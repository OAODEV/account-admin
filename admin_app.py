import os
from datetime import datetime
from urllib.parse import urlencode

from authlib.flask.client import OAuth
from flask import Flask, redirect, session, url_for
from flask_admin import Admin
from flask_admin.base import MenuLink
from flask_admin.contrib.sqla import ModelView
from flask_admin.contrib.sqla.filters import BaseSQLAFilter
from flask_admin.model.widgets import XEditableWidget
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql.functions import func
from werkzeug.exceptions import BadRequestKeyError

from models import Client, Employee, Product


def make_secret_key():
    key = os.urandom(24).hex()
    return (key)


app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', make_secret_key())
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL', ('postgres://account_admin_user@localhost:5454'
                     '/account_admin'))
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


""" Auth0 setup and methods
"""
AUTH0_CALLBACK_URL = os.getenv('AUTH0_CALLBACK_URL')
AUTH0_CLIENT_ID = os.getenv('AUTH0_CLIENT_ID')
AUTH0_CLIENT_SECRET = os.getenv('AUTH0_CLIENT_SECRET')
AUTH0_DOMAIN = os.getenv('AUTH0_DOMAIN')
AUTH0_BASE_URL = 'https://' + AUTH0_DOMAIN
AUTH0_AUDIENCE = os.getenv('AUTH0_AUDIENCE', AUTH0_BASE_URL + '/userinfo')

oauth = OAuth(app)

auth0 = oauth.register(
    'auth0',
    client_id=AUTH0_CLIENT_ID,
    client_secret=AUTH0_CLIENT_SECRET,
    api_base_url=AUTH0_BASE_URL,
    access_token_url=AUTH0_BASE_URL + '/oauth/token',
    authorize_url=AUTH0_BASE_URL + '/authorize',
    client_kwargs={
        'scope': 'openid email profile',
    },
)


@app.route('/')
def index():
    if 'profile' in session:
        return redirect('/admin/client/?flt0_0=1')
    else:
        return redirect('/login')


@app.route('/callback')
def callback_handling():
    try:
        auth0.authorize_access_token()
    except BadRequestKeyError:
        return ('<h1>Access denied</h1>'
                '<p>Please <a href="/login">login</a> '
                'with a valid adops.com account</p>'), 400
    resp = auth0.get('userinfo')
    userinfo = resp.json()

    session['jwt_payload'] = userinfo
    session['profile'] = {
        'user_id': userinfo['sub'],
        'name': userinfo['name'],
        'email': userinfo['email']
    }
    return redirect('/admin/client/?flt0_0=1')


@app.route('/login')
def login():
    return auth0.authorize_redirect(
        redirect_uri=AUTH0_CALLBACK_URL, audience=AUTH0_AUDIENCE)


@app.route('/logout')
def logout():
    session.clear()
    params = {
        'returnTo': url_for('index', _external=True, _scheme='https'),
        'client_id': AUTH0_CLIENT_ID
    }
    return redirect(auth0.api_base_url + '/v2/logout?' + urlencode(params))


class AuthMixin():
    def is_accessible(self):
        if 'profile' in session:
            return True
        return False

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('index'))


""" Helper functions for form choices
    TODO: Pull out to own file (or add to __init__?)
"""


def client_managers():
    return db.session.query(Employee).filter(
        Employee.account_manager_flag.is_(True))


def employee_managers():
    managers = db.session.query(Employee.manager_person_id).distinct()
    managers = managers.filter(Employee.manager_person_id.isnot(None))
    return db.session.query(Employee).filter(Employee.person_id.in_(managers))


def get_products():
    products = db.session.query(Product).all()
    return [(str(product), product) for product in products]


def generate_code(client):
    """ Generate OAO Standard Client code value from
        - First 2 letters of assigned account name
        - Start year
        - sum of unicode values of org name, modulo 999, zero-padded
    """
    if client.client_organization_code:
        # no-op if client already has a code
        return client.client_organization_code
    norm_name = client.assigned_account_name.upper().strip().replace(
        'THE ', '')
    abbrev_name = norm_name[:2]
    try:
        start_year = client.contract_start_date.year
    except AttributeError:
        start_year = datetime.now().year
    suffix = str(
        sum(bytearray(client.client_organization_name, 'utf-8')) %
        999).zfill(3)
    client_code = '{0}{1}-{2}'.format(abbrev_name, start_year, suffix)
    return client_code


""" Custom filter classes for ClientAdmin view
"""


class ProductFilter(BaseSQLAFilter):
    def apply(self, query, value, alias=None):
        return query.filter(Client.products.any(product_type_name=value))

    def operation(self):
        return 'includes'


class AccountLeadFilter(BaseSQLAFilter):
    def apply(self, query, value, alias=None):
        return query.filter((Client.account_manager.has(person_id=value))
                            | (Client.secondary_manager.has(person_id=value)))

    def operation(self):
        return 'equals'


""" Model views
"""


class ClientAdmin(AuthMixin, ModelView):
    # Hide from menu, so we can replace with filtered view link
    def is_visible(self):
        return False

    can_export = True
    edit_modal = True

    column_list = [
        'client_organization_name', 'client_organization_code',
        'dfp_network_code', 'account_manager', 'secondary_manager',
        'dfp_display_name'
    ]
    column_exclude_list = [
        'created_datetime',
        'modified_datetime',
        'created_by',
        'modified_by',
    ]

    column_searchable_list = ('client_organization_name', 'dfp_network_code',
                              'dfp_display_name', 'products.product_type_name',
                              'account_manager.email')
    column_default_sort = ('client_organization_name')
    column_sortable_list = (('account_manager', 'account_manager.email'),
                            ('secondary_manager', 'secondary_manager.email'),
                            'client_organization_name', 'dfp_network_code',
                            'dfp_display_name')
    # yapf: disable
    column_filters = [
        'active_client_flag',
        'dfp_network_code',
        AccountLeadFilter(
            column='account_manager',
            name='Account Lead',
            options=[(mgr.person_id, str(mgr))
                     for mgr in client_managers()]),
        ProductFilter(
            column='products',
            name='Product',
            options=get_products())
    ]
    # yapf: enable

    # override WTForms query_factory with filtered manager results
    # for account_manager
    form_args = dict(
        account_manager=dict(
            label='Account Lead', query_factory=client_managers),
        client_organization_code=dict(
            description=(
                'OAO Standard Client Code: 1st two letters, start year, '
                'three digits')))
    form_columns = [
        'client_organization_name', 'client_organization_code',
        'account_manager', 'secondary_manager', 'assigned_account_name',
        'dfp_network_code', 'dfp_display_name', 'products', 'oao_inbox_name',
        'oao_escalation_group_name', 'oao_shared_folder', 'oao_wiki_page',
        'contract_start_date', 'contract_end_date', 'active_client_flag',
        'notes'
    ]
    form_excluded_columns = [
        'created_datetime',
        'modified_datetime',
        'created_by',
        'modified_by',
    ]
    column_labels = dict(
        client_organization_name='Client',
        client_organization_code='Client Code',
        active_client_flag='Active Client',
        account_manager='Account Lead',
        secondary_manager='Secondary Lead',
        dfp_network_code='DFP Network',
        dfp_display_name='DFP Display Name',
        oao_inbox_name='Inbox',
        oao_escalation_group_name='Escalation Group',
        oao_shared_folder='Google Drive Share',
        oao_wiki_page='OAO Wiki URL')
    # Disable manual code entry/editing
    # TODO: Allow this to be edited manually by certain users
    form_widget_args = {
        'client_organization_code': {
            'readonly': True
        },
    }

    def on_model_change(self, form, Client, is_created=False):
        """ Include user email in client created_by or modified_by field
            and calculate the client code
        """
        if is_created:
            Client.created_by = session['profile']['email']
        else:
            Client.modified_by = session['profile']['email']
        Client.client_organization_code = generate_code(Client)


class ManagerEditableWidget(XEditableWidget):
    """
    Custom widget for editable Manager field in list view
    """

    def get_kwargs(self, subfield, kwargs):
        kwargs = super().get_kwargs(subfield, kwargs)
        kwargs['data-source'] = [
            dict(value=e.person_id, text=str(e))
            for e in list(employee_managers())
        ]

        return kwargs


class EmployeeAdmin(AuthMixin, ModelView):
    # override base view query to filter out former employees
    def get_query(self):
        return self.session.query(self.model).filter(
            self.model.current_employee_flag.is_(True))

    def get_count_query(self):
        return self.session.query(func.count('*')).filter(
            self.model.current_employee_flag.is_(True))

    def get_list_form(self):
        return self.scaffold_list_form(widget=ManagerEditableWidget())

    can_export = True
    can_delete = False
    can_create = False
    edit_modal = True

    column_list = ['first_name', 'last_name', 'email', 'manager', 'office']
    column_exclude_list = [
        'created_datetime',
        'modified_datetime',
        'created_by',
        'modified_by',
    ]
    column_default_sort = ('email')
    column_sortable_list = ('manager', 'first_name', 'last_name', 'email',
                            ('office', 'office.office_name'))
    column_searchable_list = ('first_name', 'last_name', 'email',
                              'office.office_name')

    form_args = dict(manager=dict(query_factory=employee_managers))
    form_excluded_columns = [
        'created_datetime', 'modified_datetime', 'created_by', 'modified_by',
        'gsuite_id'
    ]
    form_columns = [
        'first_name', 'last_name', 'email', 'manager', 'account_manager_flag',
        'office'
    ]
    column_editable_list = ['manager']
    column_labels = dict(account_manager_flag='Account Lead')

    def on_model_change(self, form, Employee, is_created):
        if is_created:
            Employee.created_by = session['profile']['email']
        else:
            Employee.modified_by = session['profile']['email']


class ProductAdmin(AuthMixin, ModelView):
    edit_modal = True

    column_exclude_list = [
        'created_datetime', 'modified_datetime', 'created_by', 'modified_by'
    ]
    form_excluded_columns = [
        'created_datetime', 'modified_datetime', 'created_by', 'modified_by',
        'clients'
    ]
    column_labels = dict(
        product_type_code='Code',
        product_type_name='Name',
        product_type_description='Description')

    def on_model_change(self, form, Product, is_created):
        if is_created:
            Product.created_by = session['profile']['email']
        else:
            Product.modified_by = session['profile']['email']


""" Admin app provisioning.
    - Instantiates Admin globally, for wsgi container
    - Order in which views and links are added corresponds to main nav menu
"""
admin = Admin(
    app, name='OAO Account Administration', template_mode='bootstrap3')

admin.add_view(ClientAdmin(Client, db.session))
# custom links for clients, to include active_client_flag filter
admin.add_link(
    MenuLink(name='Active', category='Client', url='/admin/client/?flt0_0=1'))
admin.add_link(MenuLink(name='All', category='Client', url='/admin/client'))
admin.add_view(EmployeeAdmin(Employee, db.session))
admin.add_view(ProductAdmin(Product, db.session))
admin.add_link(MenuLink(name='Logout', url='/logout'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

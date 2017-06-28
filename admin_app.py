import os

from flask import Flask
from flask_admin import Admin
from flask_admin.base import MenuLink
from flask_admin.contrib.sqla import ModelView
from flask_admin.contrib.sqla.filters import BaseSQLAFilter
from flask_admin.model.widgets import XEditableWidget
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql.functions import func

from models import Client, Employee, Product


def make_secret_key():
    key = os.urandom(24).hex()
    return (key)


app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', make_secret_key())
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DBURL', (
    'postgres://account_admin_user@localhost:5433'
    '/account_admin'))
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


@app.route('/')
def index():
    return '<a href="/admin/client/?flt0_0=1">Admin Ahoy!</a>'


'''
Helper functions for form choices
TODO: Pull out to own file (or add to __init__?)
'''


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


'''
Custom filter classes for ClientAdmin view
'''


class ProductFilter(BaseSQLAFilter):
    def apply(self, query, value, alias=None):
        return query.filter(Client.products.any(product_type_name=value))

    def operation(self):
        return 'includes'


class AccountLeadFilter(BaseSQLAFilter):
    def apply(self, query, value, alias=None):
        return query.filter((Client.account_manager.has(person_id=value)) | (
            Client.secondary_manager.has(person_id=value)))

    def operation(self):
        return 'equals'


'''
Model views
'''


class ClientAdmin(ModelView):
    # Hide from menu, so we can replace with filtered view link
    def is_visible(self):
        return False

    can_export = True
    edit_modal = True

    column_list = [
        'client_organization_name', 'dfp_network_code', 'account_manager',
        'secondary_manager', 'dfp_display_name'
    ]
    column_exclude_list = ['created_datetime', 'modified_datetime']

    column_searchable_list = ('client_organization_name', 'dfp_network_code',
                              'dfp_display_name', 'products.product_type_name',
                              'account_manager.email')
    column_default_sort = ('client_organization_name')
    column_sortable_list = (('account_manager', 'account_manager.email'), (
        'secondary_manager', 'secondary_manager.email'),
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
    form_args = dict(account_manager=dict(
        label='Account Lead', query_factory=client_managers))
    form_columns = [
        'client_organization_name', 'account_manager', 'secondary_manager',
        'assigned_account_name', 'dfp_network_code', 'dfp_display_name',
        'products', 'active_client_flag', 'notes'
    ]
    form_excluded_columns = ['created_datetime', 'modified_datetime']
    column_labels = dict(
        client_organization_name='Client',
        active_client_flag='Active Client',
        account_manager='Account Lead',
        secondary_manager='Secondary Lead',
        dfp_network_code='DFP Network',
        dfp_display_name='DFP Display Name')


class ManagerEditableWidget(XEditableWidget):
    '''
    Custom widget for editable Manager field in list view
    '''

    def get_kwargs(self, subfield, kwargs):
        kwargs = super().get_kwargs(subfield, kwargs)
        kwargs['data-source'] = [
            dict(value=e.person_id, text=str(e))
            for e in list(employee_managers())
        ]

        return kwargs


class EmployeeAdmin(ModelView):
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
    ]
    column_default_sort = ('email')
    column_sortable_list = ('manager', 'first_name', 'last_name', 'email',
                            ('office', 'office.office_name'))
    column_searchable_list = ('first_name', 'last_name', 'email',
                              'office.office_name')

    form_args = dict(manager=dict(query_factory=employee_managers))
    form_excluded_columns = [
        'created_datetime', 'modified_datetime', 'gsuite_id'
    ]
    form_columns = [
        'first_name', 'last_name', 'email', 'manager', 'account_manager_flag',
        'office'
    ]
    column_editable_list = ['manager']
    column_labels = dict(account_manager_flag='Account Lead')


class ProductAdmin(ModelView):
    edit_modal = True

    column_exclude_list = ['created_datetime', 'modified_datetime']
    form_excluded_columns = [
        'created_datetime', 'modified_datetime', 'clients'
    ]
    column_labels = dict(
        product_type_code='Code',
        product_type_name='Name',
        product_type_description='Description')


'''
Admin app provisioning. Instantiates Admin globally, for wsgi container
Order in which views and links are added corresponds to main nav menu
'''
admin = Admin(
    app, name='OAO Account Administration', template_mode='bootstrap3')

admin.add_view(ClientAdmin(Client, db.session))
# custom links for clients, to include active_client_flag filter
admin.add_link(
    MenuLink(name='Active', category='Client', url='/admin/client/?flt0_0=1'))
admin.add_link(MenuLink(name='All', category='Client', url='/admin/client'))
admin.add_view(EmployeeAdmin(Employee, db.session))
admin.add_view(ProductAdmin(Product, db.session))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView

from models import ClientOrganization, Employee, Product

app = Flask(__name__)
app.config['SECRET_KEY'] = (
    'ddc9ac8881219c29b4d87f2f046efc1170c5f80a10d9a2ecc81fc366c108719f')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DBURL', (
    'postgres://account_admin_user@localhost:5433'
    '/account_admin?sslmode=verify-ca'))
db = SQLAlchemy(app)


@app.route('/')
def index():
    return '<a href="/admin/employee/">Admin Ahoy!</a>'


class ClientAdmin(ModelView):
    can_export = True

    column_exclude_list = ['created_datetime', 'modified_datetime']
    column_list = [
        'client_organization_name', 'dfp_network_code', 'account_manager',
        'dfp_display_name'
    ]
    form_columns = [
        'client_organization_name', 'account_manager', 'assigned_account_name',
        'dfp_network_code', 'dfp_display_name', 'products',
        'active_client_flag'
    ]
    column_searchable_list = ('client_organization_name', )
    column_default_sort = ('client_organization_name')
    column_sortable_list = (('account_manager', 'account_manager.last_name'),
                            'client_organization_name', 'dfp_network_code')
    column_filters = [Employee.email, ClientOrganization.dfp_network_code]
    column_auto_select_related = True
    form_excluded_columns = ['created_datetime', 'modified_datetime']
    column_labels = dict(
        client_organization_name='Client', active_client_flag='Active Client')


class EmployeeAdmin(ModelView):
    can_export = True
    can_delete = False
    can_create = False
    edit_modal = True
    column_exclude_list = [
        'created_datetime',
        'modified_datetime',
    ]
    column_list = ['first_name', 'last_name', 'email', 'manager', 'office']
    column_default_sort = ('email')
    column_sortable_list = ('manager', 'first_name', 'last_name', 'email',
                            ('office', 'office.office_name'))
    form_excluded_columns = [
        'created_datetime', 'modified_datetime', 'gsuite_id'
    ]
    form_columns = [
        'first_name', 'last_name', 'email', 'manager', 'account_manager_flag',
        'office'
    ]
    column_editable_list = ['manager', ]
    column_select_related_list = ['manager', ]
    column_labels = dict(account_manager_flag='Acct Mgr')


class ProductAdmin(ModelView):
    column_exclude_list = ['created_datetime', 'modified_datetime']
    form_excluded_columns = [
        'created_datetime', 'modified_datetime', 'clients'
    ]
    column_labels = dict(
        product_type_code='Code',
        product_type_name='Name',
        product_type_description='Description')


if __name__ == '__main__':
    admin = Admin(
        app, name='OAO Account Administration', template_mode='bootstrap3')

    admin.add_view(EmployeeAdmin(Employee, db.session))
    admin.add_view(ClientAdmin(ClientOrganization, db.session, name='Client'))
    admin.add_view(ProductAdmin(Product, db.session))

    app.run(debug=True, host='0.0.0.0', port=5000)

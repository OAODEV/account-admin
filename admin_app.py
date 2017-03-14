from flask import Flask
from flask_admin import Admin
from flask_admin.contrib.peewee import ModelView

from models import Person, ClientOrganization, ClientProduct, Product

app = Flask(__name__)
app.config['SECRET_KEY'] = (
    'ddc9ac8881219c29b4d87f2f046efc1170c5f80a10d9a2ecc81fc366c108719f')


@app.route('/')
def index():
    return '<a href="/admin/">Admin Ahoy!</a>'


class ClientAdmin(ModelView):
    column_exclude_list = ['created_datetime', 'modified_datetime']
    column_list = [
        'client_organization_name', 'dfp_network_code', 'account_manager',
        'dfp_display_name'
    ]
    column_searchable_list = ('client_organization_name', )

    # column_auto_select_related = True
    # inline_models = (ClientProduct)


class PersonAdmin(ModelView):
    column_exclude_list = [
        'created_datetime',
        'modified_datetime',
    ]
    column_list = ['first_name', 'last_name', 'email', 'person_code']


class ProductAdmin(ModelView):
    column_exclude_list = ['created_datetime', 'modified_datetime']


class ClientProductAdmin(ModelView):
    column_exclude_list = ['created_datetime', 'modified_datetime']


if __name__ == '__main__':
    admin = Admin(
        app, name='OAO Account Administration', template_mode='bootstrap3')

    admin.add_view(PersonAdmin(Person))
    admin.add_view(ClientAdmin(ClientOrganization))
    admin.add_view(ProductAdmin(Product))
    admin.add_view(ClientProductAdmin(ClientProduct))

    app.run(debug=True, host='0.0.0.0', port=5000)

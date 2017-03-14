import os
from peewee import *
from playhouse.db_url import connect
# from playhouse.reflection import Introspector

DBURL = os.getenv('DBURL', ('postgres://account_admin_user@localhost:5433'
                            '/account_admin?sslmode=verify-ca'))

database = connect(DBURL)


class UnknownField(object):
    def __init__(self, *_, **__):
        pass


class BaseModel(Model):
    class Meta:
        database = database


class Person(BaseModel):
    created_datetime = DateTimeField(null=True)
    email = TextField()
    first_name = TextField()
    last_name = TextField()
    manager_person = ForeignKeyField(
        db_column='manager_person_id',
        null=True,
        rel_model='self',
        to_field='person')
    modified_datetime = DateTimeField(null=True)
    office = TextField(null=True)
    person_code = TextField()
    person = PrimaryKeyField(db_column='person_id')

    def __str__(self):
        return '{0} {1}'.format(self.first_name, self.last_name)

    class Meta:
        db_table = 'person'


class ClientOrganization(BaseModel):
    account_manager = ForeignKeyField(
        db_column='account_manager_id',
        null=True,
        rel_model=Person,
        to_field='person')
    active_client_flag = BooleanField(null=True)
    assigned_account_name = TextField()
    client_organization_code = TextField()
    client_organization = PrimaryKeyField(db_column='client_organization_id')
    client_organization_name = TextField()
    created_datetime = DateTimeField(null=True)
    dfp_display_name = TextField(null=True)
    dfp_network_code = IntegerField(null=True)
    modified_datetime = DateTimeField(null=True)

    def __str__(self):
        return '{0} ({1})'.format(self.client_organization_name,
                                  self.dfp_network_code)

    class Meta:
        db_table = 'client_organization'


class Product(BaseModel):
    created_datetime = DateTimeField(null=True)
    modified_datetime = DateTimeField(null=True)
    product_type_code = TextField()
    product_type_description = TextField(null=True)
    product_type = PrimaryKeyField(db_column='product_type_id')
    product_type_name = TextField()

    def __str__(self):
        return self.product_type_name

    class Meta:
        db_table = 'product_type'


class ClientProduct(BaseModel):
    client_organization = ForeignKeyField(
        db_column='client_organization_id',
        rel_model=ClientOrganization,
        to_field='client_organization')
    client_product = PrimaryKeyField(db_column='client_product_association_id')
    created_datetime = DateTimeField(null=True)
    modified_datetime = DateTimeField(null=True)
    product_type = ForeignKeyField(
        db_column='product_type_id',
        rel_model=Product,
        to_field='product_type')

    class Meta:
        db_table = 'client_product_association'

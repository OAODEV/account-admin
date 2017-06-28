# coding: utf-8
import os

from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, Integer, Table,
                        Text, create_engine, text)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

engine = create_engine(
    os.getenv('DBURL', ('postgres://account_admin_user@localhost:5433'
                        '/account_admin')))

Base = declarative_base(engine)
metadata = Base.metadata

t_client_product_association = Table(
    'client_product_association', metadata,
    Column(
        'product_type_id',
        ForeignKey('product_type.product_type_id'),
        primary_key=True,
        nullable=False),
    Column(
        'client_organization_id',
        ForeignKey('client_organization.client_organization_id'),
        primary_key=True,
        nullable=False))


class Client(Base):
    __tablename__ = 'client_organization'

    client_organization_id = Column(
        Integer,
        primary_key=True,
        server_default=text("nextval("
                            "'client_organization_client_organization_id_seq'"
                            "::regclass)"))
    client_organization_code = Column(Text)
    client_organization_name = Column(Text, nullable=False)
    assigned_account_name = Column(Text, nullable=False)
    account_manager_id = Column(ForeignKey('person.person_id'))
    secondary_manager_id = Column(ForeignKey('person.person_id'))
    dfp_network_code = Column(Integer)
    dfp_display_name = Column(Text)
    notes = Column(Text)
    active_client_flag = Column(Boolean, server_default=text("true"))
    created_datetime = Column(DateTime, server_default=text("now()"))
    modified_datetime = Column(DateTime)

    account_manager = relationship('Employee', foreign_keys=account_manager_id)
    secondary_manager = relationship(
        'Employee', foreign_keys=secondary_manager_id)
    products = relationship(
        'Product',
        secondary=t_client_product_association,
        backref='client_organization',
        passive_deletes=True)

    def __str__(self):
        return '{0} ({1})'.format(self.client_organization_name,
                                  self.dfp_network_code)


class Product(Base):
    __tablename__ = 'product_type'

    product_type_id = Column(
        Integer,
        primary_key=True,
        server_default=text(
            "nextval('product_type_product_type_id_seq'::regclass)"))
    product_type_code = Column(Text, nullable=False)
    product_type_name = Column(Text, nullable=False)
    product_type_description = Column(Text)
    created_datetime = Column(DateTime, server_default=text("now()"))
    modified_datetime = Column(DateTime)

    clients = relationship(
        'Client',
        secondary=t_client_product_association,
        backref='product_type')

    def __str__(self):
        return self.product_type_name


class Employee(Base):
    __tablename__ = 'person'

    gsuite_id = Column('person_code', Text, nullable=False)
    first_name = Column(Text, nullable=False)
    last_name = Column(Text, nullable=False)
    office_id = Column(ForeignKey('office.office_id'))
    email = Column(Text, nullable=False)
    created_datetime = Column(DateTime, server_default=text("now()"))
    modified_datetime = Column(DateTime)
    person_id = Column(
        Integer,
        primary_key=True,
        server_default=text("nextval('person_person_id_seq'::regclass)"))
    manager_person_id = Column(ForeignKey('person.person_id'))
    account_manager_flag = Column(Boolean)
    current_employee_flag = Column(Boolean, server_default=text("true"))
    office = relationship('Office', backref='employee')
    manager = relationship(
        'Employee', remote_side=[person_id], order_by='Employee.email')

    def __str__(self):
        return '{0} {1} ({2})'.format(self.first_name, self.last_name,
                                      self.email)

    __mapper_args__ = {"order_by": email}


class Office(Base):
    __tablename__ = 'office'

    office_id = Column(
        Integer,
        primary_key=True,
        server_default=text("nextval('oao_office_office_id_seq'::regclass)"))
    office_name = Column(Text, nullable=False)
    created_datetime = Column(DateTime, server_default=text("now()"))
    modified_datetime = Column(DateTime)

    def __str__(self):
        return self.office_name

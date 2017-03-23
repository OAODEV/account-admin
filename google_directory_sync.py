from __future__ import print_function

# import json
import os

import httplib2
from apiclient import discovery
from oauth2client import client, tools
from oauth2client.file import Storage

from sqlalchemy import create_engine
from sqlalchemy.orm.session import sessionmaker
from models import Employee

engine = create_engine(
    os.getenv('DBURL', ('postgres://account_admin_user@localhost:5433'
                        '/account_admin?sslmode=verify-ca')))
Session = sessionmaker(bind=engine)


SCOPES = 'https://www.googleapis.com/auth/admin.directory.user'
CLIENT_SECRET_FILE = '/secret/client_secret.json'
APPLICATION_NAME = 'Directory API Python Sync'


def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'admin-directory_v1-python-quickstart.json')

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials


def main():
    """
    Simple script to fetch all OAO internal users from Google Directory API
    and sync to the 'person' table in our 'account_admin' database.

    Users are matched based on Google user id. Any id values appearing in the
    API pull that aren't already added get a row inserted with name, gsuite_id,
    and email. Manager is left to be filled in by the administrative user.

    After that, and similiarly, any id values in the database table that are
    not in the pull from Google have their current_employee_flag set to False
    """
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('admin', 'directory_v1', http=http)

    # Get all Google Users from Directory API
    results = service.users().list(
        customer='my_customer',
        # projection='full',
        query="orgUnitPath='/Google Users'",
        orderBy='email').execute()
    users = results.get('users', [])
    user_ids = [user['id'] for user in users]

    # Get list of Employee codes (== user['id'] from google) from database
    session = Session()
    person_query = session.query(Employee).all()
    person_codes = [person.gsuite_id for person in person_query]

    # Add any Google users to 'person' table if user['id'] not already
    # in person_code
    for user in users:
        if user['id'] not in person_codes:
            print(user['primaryEmail'], user['id'])
            q = Employee(first_name=user['name']['givenName'],
                         last_name=user['name']['familyName'],
                         gsuite_id=user['id'],
                         email=user['primaryEmail'])
            session.add(q)
            session.commit()

    # Set current_employee_flag to False if person's gsuite_id not found in
    # list of ids from Google, as a way to "soft delete" these users

    # TODO: This will keep updating users that have already been soft-deleted.
    #       Not a _terrible_ issue, but we should do better.
    for person in person_codes:
        if person not in user_ids:
            q = session.query(Employee).filter_by(gsuite_id=person).first()
            q.current_employee_flag = False
            session.commit()

if __name__ == '__main__':
    main()

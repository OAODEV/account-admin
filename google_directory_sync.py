from __future__ import print_function

# import json
import os

import httplib2
from apiclient import discovery
from oauth2client import client, tools
from oauth2client.file import Storage

from playhouse.db_url import connect
from models import Person

DBURL = os.getenv('DBURL', ('postgres://account_admin_user@localhost'
                            '/account_admin?sslmode=verify-ca'))

database = connect(DBURL)


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

    """
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('admin', 'directory_v1', http=http)

    # Get all Google Users from Directory API
    results = service.users().list(
        customer='my_customer',
        projection='full',
        query="orgUnitPath='/Google Users'",
        orderBy='email').execute()
    users = results.get('users', [])

    # Get list of person codes (== user['id'] from google) from database
    person_query = Person.select()
    person_codes = []
    for person in person_query:
        person_codes.append(person.person_code)

    # Add any Google users to 'person' table if user['id'] not already
    # in person_code
    for user in users:
        if user['id'] not in person_codes:
            print(user['primaryEmail'], user['id'])
            q = Person.insert(first_name=user['name']['givenName'],
                              last_name=user['name']['familyName'],
                              person_code=user['id'],
                              email=user['primaryEmail'])
            q.execute()

if __name__ == '__main__':
    main()

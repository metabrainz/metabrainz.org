from intuitlib.client import AuthClient
from quickbooks import QuickBooks
from flask import request, current_app

auth_client = None

def init(app):
    '''
    Create global auth client that manages QuickBooks sessions.
    '''

    global auth_client
    auth_client = AuthClient(
        client_id=app.config["QUICKBOOKS_CLIENT_ID"],
        client_secret=app.config["QUICKBOOKS_CLIENT_SECRET"],
        environment=app.config["QUICKBOOKS_SANDBOX"],
        redirect_uri=app.config["QUICKBOOKS_CALLBACK_URL"]
    )


def get_client(realm, refresh_token):
    '''
    Create the QuickBooks client object from the auth client.
    '''

    global auth_client
    QuickBooks.enable_global()
    qb = QuickBooks(
        auth_client=auth_client,
        refresh_token=refresh_token,
        company_id=realm
    )

    return qb

from intuitlib.client import AuthClient
from quickbooks import QuickBooks
from flask import request, current_app

def init(app):
    '''
    Create global auth client that manages QuickBooks sessions.
    '''

    if not app.config["QUICKBOOKS_CLIENT_ID"]:
        app.logger.warn("No QUICKBOOKS_CLIENT_ID specified, not setting up QB invoice feature.")
        return

    app.quickbooks_auth_client = AuthClient(
        client_id=app.config["QUICKBOOKS_CLIENT_ID"],
        client_secret=app.config["QUICKBOOKS_CLIENT_SECRET"],
        environment=app.config["QUICKBOOKS_SANDBOX"],
        redirect_uri=app.config["QUICKBOOKS_CALLBACK_URL"]
    )


def get_client(realm, refresh_token):
    '''
    Create the QuickBooks client object from the auth client.
    '''

    QuickBooks.enable_global()
    qb = QuickBooks(
        auth_client=current_app.quickbooks_auth_client,
        refresh_token=refresh_token,
        company_id=realm
    )

    return qb

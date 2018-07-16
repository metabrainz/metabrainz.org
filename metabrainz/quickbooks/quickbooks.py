from quickbooks import Oauth2SessionManager, QuickBooks
from flask import request, current_app
from quickbooks import Oauth2SessionManager

session_manager = None

def init(app):
    '''
    Create global session manager that manages QuickBooks sessions.
    '''

    global session_manager
    session_manager = Oauth2SessionManager(
            sandbox=app.config["QUICKBOOKS_SANDBOX"],
            client_id=app.config["QUICKBOOKS_CLIENT_ID"],
            client_secret=app.config["QUICKBOOKS_CLIENT_SECRET"],
            base_url=app.config["QUICKBOOKS_CALLBACK_URL"],
    )


def get_client(realm):
    '''
    Create the QuickBooks client object from the session manager.
    '''

    global session_manager

    return QuickBooks(
        sandbox=True,
        session_manager=session_manager,
        company_id=realm
    )

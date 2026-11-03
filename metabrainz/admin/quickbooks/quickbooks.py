from intuitlib.client import AuthClient
from quickbooks import QuickBooks
from flask import current_app

def init(app):
    '''
    Check that QuickBooks is configured.
    '''

    if not app.config["QUICKBOOKS_CLIENT_ID"]:
        app.logger.warn("No QUICKBOOKS_CLIENT_ID specified, not setting up QB invoice feature.")


def create_auth_client(access_token=None, refresh_token=None):
    '''
    Create a new auth client. Auth clients hold token state, so never share one across requests.
    '''

    return AuthClient(
        client_id=current_app.config["QUICKBOOKS_CLIENT_ID"],
        client_secret=current_app.config["QUICKBOOKS_CLIENT_SECRET"],
        environment=current_app.config["QUICKBOOKS_SANDBOX"],
        redirect_uri=current_app.config["QUICKBOOKS_CALLBACK_URL"],
        access_token=access_token,
        refresh_token=refresh_token
    )


def get_client(realm, access_token, refresh_token):
    '''
    Create the QuickBooks client object. If access_token is None, the refresh token is used to
    obtain new tokens, which are then available on client.auth_client.
    '''

    qb = QuickBooks(
        auth_client=create_auth_client(access_token, refresh_token),
        refresh_token=refresh_token,
        company_id=realm
    )

    return qb


# QuickBooks returns at most 1000 rows per query, and only 100 if MAXRESULTS is not given
QUERY_PAGE_SIZE = 1000

def query_all(cls, where_clause, order_by, qb):
    '''
    Fetch every object of the given QuickBooks class matching the where clause, page by page.
    '''

    results = []
    start_position = 1
    while True:
        page = cls.where(where_clause, order_by=order_by, start_position=start_position,
                         max_results=QUERY_PAGE_SIZE, qb=qb)
        results.extend(page)
        if len(page) < QUERY_PAGE_SIZE:
            return results
        start_position += QUERY_PAGE_SIZE

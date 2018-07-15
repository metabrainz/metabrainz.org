import logging
import quickbooks

from werkzeug.exceptions import BadRequest, InternalServerError
from flask import Blueprint, request, current_app, render_template, redirect, url_for, session
from metabrainz.quickbooks.quickbooks import session_manager, get_client
from quickbooks import Oauth2SessionManager, QuickBooks
from quickbooks.objects.customer import Customer

quickbooks_bp = Blueprint('quickbooks', __name__)

@quickbooks_bp.route('/')
def index():

    access_token = session.get('access_token', None)
    realm = session.get('realm', None)

    if not session['access_token']:
        logging.error("no access token!")
        return render_template("quickbooks/login.html")

    # I shouldn't have to do this, but it doesn't persist otherwise
    session_manager.access_token = access_token

    logging.error("have access token! '%s' '%s'" % (access_token, realm))
    try:
        client = get_client(realm)
        customers = Customer.filter(Active=True, qb=client)

    except quickbooks.exceptions.AuthorizationException as err:
        session['access_token'] = None
        session['realm'] = None
        return redirect(url_for("quickbooks.index"))
        
    except quickbooks.exceptions.QuickbooksException as err:
        logging.error(err)
        raise InternalServerError

    customer_list = []
    for customer in customers:
        customer_list.append(customer.DisplayName or customer.CompanyName)

    return render_template("quickbooks/index.html", customers=customer_list)


@quickbooks_bp.route('/login')
def login():
    return redirect(session_manager.get_authorize_url(current_app.config["QUICKBOOKS_CALLBACK_URL"]))


@quickbooks_bp.route('/callback')
def callback():
    code = request.args.get('code')
    realm = request.args.get('realmId')

    session_manager.get_access_tokens(code)
    access_token = session_manager.access_token
    session['access_token'] = access_token
    session['realm'] = realm

    logging.error("fetched access token '%s'" % access_token)
    return redirect(url_for("quickbooks.index"))

import logging
import quickbooks
from datetime import datetime
from dateutil.parser import parse

from werkzeug.exceptions import BadRequest, InternalServerError
from flask import Blueprint, request, current_app, render_template, redirect, url_for, session
from metabrainz.quickbooks.quickbooks import session_manager, get_client
from quickbooks import Oauth2SessionManager, QuickBooks
from quickbooks.objects.customer import Customer
from quickbooks.objects.invoice import Invoice

quickbooks_bp = Blueprint('quickbooks', __name__)

@quickbooks_bp.route('/')
def index():

    access_token = session.get('access_token', None)
    realm = session.get('realm', None)

    if not session['access_token']:
        logging.error("flubbed access token")
        return render_template("quickbooks/login.html")

    # I shouldn't have to do this, but it doesn't persist otherwise
    session_manager.access_token = access_token

    try:
        client = get_client(realm)
        customers = Customer.filter(Active=True, qb=client)
        invoices = Invoice.query("select * from invoice order by metadata.createtime desc", qb=client)

    except quickbooks.exceptions.AuthorizationException as err:
        session['access_token'] = None
        session['realm'] = None
        return redirect(url_for("quickbooks.index"))
        
    except quickbooks.exceptions.QuickbooksException as err:
        logging.error(err)
        raise InternalServerError

    invoice_dict = {}
    for invoice in invoices:
        customer_id = invoice.CustomerRef.value
        if customer_id not in invoice_dict:
            invoice_dict[customer_id] = []

        create_time = parse(invoice.TxnDate).strftime("%m-%d-%Y")
        try:
            begin_date = parse(invoice.CustomField[1].StringValue).strftime("%m-%d-%Y")
        except ValueError:
            begin_date = ""

        try:
            end_date = parse(invoice.CustomField[2].StringValue).strftime("%m-%d-%Y")
        except ValueError:
            end_date = ""

        try:
            tier = invoice.Line[0].SalesItemLineDetail.ItemRef.name
        except AttributeError:
            tier = ""

        invoice_dict[customer_id].append({ 
            'customer' : customer_id, 
            'date' : create_time,
            'sortdate' : invoice.TxnDate,
            'amount' : invoice.TotalAmt ,
            'begin' : begin_date,
            'end' : end_date,
            'service' : tier,
            'number' : invoice.DocNumber,
            'currency' : invoice.CurrencyRef.value
        })
        


    customer_list = []
    for customer in customers:
        invoices = invoice_dict.get(customer.Id, [])
        invoices = sorted(invoices, key=lambda invoice: invoice['sortdate'], reverse=True)
        customer_list.append({ 'name' : customer.DisplayName or customer.CompanyName, 'invoices' : invoices })


    return render_template("quickbooks/index.html", customers=customer_list)


@quickbooks_bp.route('/login')
def login():
    return redirect(session_manager.get_authorize_url(current_app.config["QUICKBOOKS_CALLBACK_URL"]))


@quickbooks_bp.route('/logout')
def logout():

    session['access_token'] = None
    session['realm'] = None

    return redirect(url_for("quickbooks.index"))


@quickbooks_bp.route('/callback')
def callback():
    code = request.args.get('code')
    realm = request.args.get('realmId')

    session_manager.get_access_tokens(code)
    access_token = session_manager.access_token
    session['access_token'] = access_token
    session['realm'] = realm

    return redirect(url_for("quickbooks.index"))

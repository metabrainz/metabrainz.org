import logging
import quickbooks
import datetime 
from dateutil.parser import parse
from calendar import monthrange
from copy import deepcopy

from werkzeug.exceptions import BadRequest, InternalServerError
from flask import Blueprint, request, current_app, render_template, redirect, url_for, session, flash
from metabrainz.quickbooks.quickbooks import session_manager, get_client
from quickbooks import Oauth2SessionManager, QuickBooks
from quickbooks.objects.customer import Customer
from quickbooks.objects.invoice import Invoice

quickbooks_bp = Blueprint('quickbooks', __name__)


def calculate_quarter_dates(year, quarter):
    quarter += 1
    first_month_of_quarter = 3 * quarter - 2
    last_month_of_quarter = 3 * quarter
    date_of_first_day_of_quarter = datetime.date(year, first_month_of_quarter, 1).strftime("%m-%d-%Y")
    date_of_last_day_of_quarter = datetime.date(year, last_month_of_quarter, monthrange(year, last_month_of_quarter)[1]).strftime("%m-%d-%Y")

    return (date_of_first_day_of_quarter, date_of_last_day_of_quarter)

def add_new_invoice(invoice, cust, start, end, today):
    new_invoice = deepcopy(invoice)
    new_invoice['begin'] = start
    new_invoice['end'] = end
    new_invoice['date'] = today
    new_invoice['sortdate'] = today
    new_invoice['number'] = 'NEW'
    cust['invoices'].insert(0, new_invoice)

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
        logging.error("query success")

    except quickbooks.exceptions.AuthorizationException as err:
        flash("Authorization failed, please try again: %s" % err)
        logging.error(err)
        session['access_token'] = None
        session['realm'] = None
        return redirect(url_for("quickbooks.index"))
        
    except quickbooks.exceptions.QuickbooksException as err:
        flash("Query failed: %s" % err)
        logging.error(err)
        raise InternalServerError

    dt = datetime.datetime.now()
    today = dt.strftime("%m-%d-%Y")
    q = (dt.month-1) // 3 
    pq = (q + 3) % 4
    ppq = (pq + 3) % 4

    year = dt.year
    (q_start, q_end) = calculate_quarter_dates(year, q)
    if pq > q:
        year -= 1
    (pq_start, pq_end) = calculate_quarter_dates(year, pq)
    if ppq > pq:
        year -= 1
    (ppq_start, ppq_end) = calculate_quarter_dates(year ,ppq)

    logging.error("q: %d %s %s" % (q, q_start, q_end))
    logging.error("pq: %d %s %s" % (pq, pq_start, pq_end))
    logging.error("ppq: %d %s %s" % (ppq, ppq_start, ppq_end))

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

    ready_to_invoice = []
    wtf = []
    current = []
    for customer in customers:
        invoices = invoice_dict.get(customer.Id, [])
        invoices = sorted(invoices, key=lambda invoice: invoice['sortdate'], reverse=True)

        name = customer.DisplayName or customer.CompanyName;
        desc = customer.Notes.lower()
        if desc.find("arrears") >= 0:
            name += " (arrears)"
            is_arrears = True
        else:
            is_arrears = False

        if desc.find("donotinvoice") >= 0:
            do_not_invoice = True
            name += " (do not invoice)"
        else:
            do_not_invoice = False

#        if invoices:
#            logging.error("q '%s' - '%s' == '%s' - '%s'" % (invoices[0]['begin'], q_start, invoices[0]['end'], q_end))
#            logging.error("pq '%s' - '%s' == '%s' - '%s'" % (invoices[0]['begin'], pq_start, invoices[0]['end'], pq_end))
        
        cust = { 'name' : name, 'invoices' : invoices }
        if do_not_invoice:
            current.append(cust)
            continue

        if not invoices:
            wtf.append(cust)
            continue

        if do_not_invoice or (invoices[0]['begin'] == q_start and invoices[0]['end'] == q_end):
            current.append(cust)
            continue

        if invoices[0]['begin'] == pq_start and invoices[0]['end'] == pq_end:
            add_new_invoice(invoices[0], cust, q_start, q_end, today)
            ready_to_invoice.append(cust)
            continue

        if is_arrears and invoices[0]['begin'] == ppq_start and invoices[0]['end'] == ppq_end:
            add_new_invoice(invoices[0], cust, pq_start, pq_end, today)
            ready_to_invoice.append(cust)
            continue

        wtf.append(cust)

    return render_template("quickbooks/index.html", ready=ready_to_invoice, wtf=wtf, current=current)


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

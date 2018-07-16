from calendar import monthrange
from copy import deepcopy
import datetime 
from dateutil.parser import parse
import logging
import quickbooks

from flask import Blueprint, request, current_app, render_template, redirect, url_for, session, flash
from flask_login import login_required
from metabrainz.quickbooks.quickbooks import session_manager, get_client
from quickbooks import Oauth2SessionManager, QuickBooks
from quickbooks.objects.customer import Customer
from quickbooks.objects.invoice import Invoice
from werkzeug.exceptions import BadRequest, InternalServerError


quickbooks_bp = Blueprint('quickbooks', __name__)


def calculate_quarter_dates(year, quarter):
    '''
    Given a year and zero based quarter, return a tuple of quarter start/end dates as a US formatted date string.
    '''
    quarter += 1
    first_month_of_quarter = 3 * quarter - 2
    last_month_of_quarter = 3 * quarter
    date_of_first_day_of_quarter = datetime.date(year, first_month_of_quarter, 1).strftime("%m-%d-%Y")
    date_of_last_day_of_quarter = datetime.date(year, last_month_of_quarter, monthrange(year, last_month_of_quarter)[1]).strftime("%m-%d-%Y")

    return (date_of_first_day_of_quarter, date_of_last_day_of_quarter)


def add_new_invoice(invoice, cust, start, end, today):
    '''
    Copy an invoice object and update some fields in the object
    '''
    new_invoice = deepcopy(invoice)
    new_invoice['begin'] = start
    new_invoice['end'] = end
    new_invoice['date'] = today
    new_invoice['sortdate'] = today
    new_invoice['number'] = 'NEW'
    cust['invoices'].insert(0, new_invoice)


def create_invoices(client, invoices):
    '''
    Given a set of exiting invoices, fetch the invoice from QuickBooks, make a copy, updated it
    with new values and then have QuickBooks save the new invoice. Invoices are not sent,
    and must be sent via the QuickBooks web interface.
    '''

    for invoice in invoices:
        invoice_list = Invoice.query("select * from invoice where Id = '%s'" % invoice['base_invoice'], qb=client)
        if not invoice_list:
            flash("Cannot fetch old invoice!")
            break

        new_invoice = invoice_list[0]
        new_invoice.Id = None
        new_invoice.DocNumber = None
        new_invoice.DueDate = None
        new_invoice.TxnDate = None
        new_invoice.ShipDate = None
        new_invoice.EInvoiceStatus = None
        new_invoice.MetaData = None
        new_invoice.EmailStatus = "NeedToSend"
        new_invoice.CustomField[1].StringValue = invoice['begin']
        new_invoice.CustomField[2].StringValue = invoice['end']
        new_invoice.save(qb=client)


@quickbooks_bp.route('/', methods=['GET'])
@login_required
def index():
    '''
    Load all customers and 100 invoices and the correlate them.
    Customers get put into three bins: Ready to invoice, current (no need for an invoice) and WTF (we couldn't sort what should happen).
    Send all this to the caller to render.
    '''

    # Look up access tokens from sessions, or make the user login
    access_token = session.get('access_token', None)
    realm = session.get('realm', None)

    if not access_token:
        logging.error("flubbed access token")
        session['realm'] = None
        return render_template("quickbooks/login.html")

    # I shouldn't have to do this, but it doesn't persist otherwise
    session_manager.access_token = access_token

    # Now fetch customers and invoices
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

    # Calculate a pile of dates, based on today date. Figure out
    # which quarter we're in, and the dates of this and 2 prior quarters
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

    # Iterate over all the invoices, parse their dates and arrange them into the invoice dict, by customer
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
            'id' : invoice.Id,
            'amount' : invoice.TotalAmt ,
            'begin' : begin_date,
            'end' : end_date,
            'service' : tier,
            'number' : invoice.DocNumber,
            'currency' : invoice.CurrencyRef.value
        })

    # Finally, classify customers into the three bins
    ready_to_invoice = []
    wtf = []
    current = []
    for customer in customers:
        invoices = invoice_dict.get(customer.Id, [])
        invoices = sorted(invoices, key=lambda invoice: invoice['sortdate'], reverse=True)

        # If there are comments in the customer notes field that indicates # arrears or # donotinvoice,
        # we use those as hints to properly create new invoices or to ignore customers
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

        # create the customer object, ready for saving
        cust = { 'name' : name, 'invoices' : invoices, 'id' : customer.Id }
        if do_not_invoice:
            current.append(cust)
            continue

        # If there are no previous invoices, go WTF!
        if not invoices:
            wtf.append(cust)
            continue

        # If this customer should not be invoiced or if the last invoice corresponds to this quarter,
        # place them into the current bin
        if do_not_invoice or (invoices[0]['begin'] == q_start and invoices[0]['end'] == q_end):
            current.append(cust)
            continue

        # If the customer is not invoiced in arrears and the last invoice looks to be from last quarter -> ready to invoice
        if not is_arrears and invoices[0]['begin'] == pq_start and invoices[0]['end'] == pq_end:
            add_new_invoice(invoices[0], cust, q_start, q_end, today)
            ready_to_invoice.append(cust)
            continue

        # If the customer is invoiced in arrears and the last invoice looks to be from last last quarter -> ready to invoice
        if is_arrears and invoices[0]['begin'] == ppq_start and invoices[0]['end'] == ppq_end:
            add_new_invoice(invoices[0], cust, pq_start, pq_end, today)
            ready_to_invoice.append(cust)
            continue

        # If the customer is invoiced in arrers and the last invoice was from the prior quarter -> current
        if is_arrears and invoices[0]['begin'] == pq_start and invoices[0]['end'] == pq_end:
            current.append(cust)
            continue

        # Everyone else, WTF?
        wtf.append(cust)


    return render_template("quickbooks/index.html", ready=ready_to_invoice, wtf=wtf, current=current)


@quickbooks_bp.route('/', methods=['POST'])
@login_required
def submit():
    '''
    Parse the form submission, load invoices, copy the invoices, update the pertinent details and then save new invoice.
    '''

    customer = 0
    invoices = []
    while True:
        customer_id = request.form.get("customer_%d" % customer)
        if not customer_id:
            break

        if not request.form.get("create_%d" % customer):
            customer += 1 
            continue

        begin_date = request.form.get("begin_%d" % customer)
        end_date = request.form.get("end_%d" % customer)
        base_invoice = request.form.get("base_invoice_%d" % customer)

        invoices.append( { 'customer' : customer_id, 'begin' : begin_date, 'end' : end_date, 'base_invoice' : base_invoice })
        customer += 1 

    # setup the access nonsense again
    access_token = session.get('access_token', None)
    realm = session.get('realm', None)

    if not session['access_token']:
        flash("access token lost. log in again.")
        return render_template("quickbooks/login.html")

    # I shouldn't have to do this, but it doesn't persist otherwise
    session_manager.access_token = access_token

    # Now call create invoices and deal with possible errors
    try:
        client = get_client(realm)
        create_invoices(client, invoices)

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

    flash("Invoices created -- make sure to send them!")
    return redirect(url_for("quickbooks.index"))


@quickbooks_bp.route('/login')
@login_required
def login():
    '''
    Login to quickbooks, oauth2 callback
    '''
    return redirect(session_manager.get_authorize_url(current_app.config["QUICKBOOKS_CALLBACK_URL"]))


@quickbooks_bp.route('/logout')
@login_required
def logout():
    '''
    Logout from QuickBooks
    '''

    session['access_token'] = None
    session['realm'] = None

    return redirect(url_for("quickbooks.index"))


@quickbooks_bp.route('/callback')
def callback():
    '''
    OAuth2 login callback function. the URL of this must match exactly what is in the QB App profile
    '''
    code = request.args.get('code')
    realm = request.args.get('realmId')

    session_manager.get_access_tokens(code)
    access_token = session_manager.access_token
    session['access_token'] = access_token
    session['realm'] = realm

    return redirect(url_for("quickbooks.index"))

from calendar import monthrange
from copy import deepcopy
import datetime 
import time
from dateutil.parser import parse
import quickbooks
from intuitlib.enums import Scopes
from flask import request, current_app, render_template, redirect, url_for, session, flash
from flask_login import login_required
from flask_admin import expose, BaseView
from metabrainz.admin.quickbooks.quickbooks import get_client
from quickbooks import QuickBooks
from quickbooks.objects.customer import Customer
from quickbooks.objects.invoice import Invoice
from quickbooks.objects.detailline import SalesItemLineDetail
from intuitlib.exceptions import AuthClientError
from werkzeug.exceptions import BadRequest, InternalServerError


class QuickBooksView(BaseView):

    @staticmethod
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


    @staticmethod
    def add_new_invoice(invoice, cust, start, end, today, qty, price):
        '''
        Copy an invoice object and update date fields in the object
        '''
        new_invoice = deepcopy(invoice)
        new_invoice['begin'] = start
        new_invoice['end'] = end
        new_invoice['date'] = today
        new_invoice['sortdate'] = today
        new_invoice['number'] = 'NEW'
        new_invoice['qty'] = qty
        new_invoice['price'] = price
        cust['invoices'].insert(0, new_invoice)


    @staticmethod
    def create_invoices(client, invoices):
        '''
        Given a set of existing invoices, fetch the invoice from QuickBooks, make a copy, update it
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
            new_invoice.TotalAmt = None
            new_invoice.EmailStatus = "NeedToSend"
            new_invoice.Line[0].SalesItemLineDetail.Qty = invoice['qty']
            new_invoice.Line[0].SalesItemLineDetail.UnitPrice = invoice['price']
            new_invoice.Line[0].Amount = "%d" % round(float(invoice['price']) * float(invoice['qty']))
            new_invoice.CustomField[1].StringValue = invoice['begin']
            new_invoice.CustomField[2].StringValue = invoice['end']
            try:
                new_invoice.save(qb=client)
            except quickbooks.exceptions.QuickbooksException as err:
                flash("failed to create invoice for %s (%s)" % (new_invoice.CustomerRef.name, str(err)))


    @expose('/', methods=['GET'])
    def index(self):
        '''
        Load all customers and 100 invoices and the correlate them.
        Customers get put into three bins: Ready to invoice, current (no need for an invoice) and WTF (we couldn't sort what should happen).
        Send all this to the caller to render.
        '''

        # Look up access tokens from sessions, or make the user login
        access_token = session.get('access_token', None)
        refresh_token = session.get('refresh_token', "")
        realm = session.get('realm', None)

        if not access_token or not refresh_token:
            session['realm'] = realm
            session['access_token'] = access_token
            session['refresh_token'] = refresh_token
            return render_template("quickbooks/login.html")

        refreshed = False
        while True:
            # Now fetch customers and invoices
            try:
                client = get_client(realm, refresh_token)
                customers = Customer.filter(Active=True, qb=client)
                invoices = Invoice.query("select * from invoice order by metadata.createtime desc maxresults 300", qb=client)
                break

            except AuthClientError as err:
                session['realm'] = None
                session['access_token'] = None
                session['refresh_token'] = None
                flash("Authorization failed, please try again: %s" % str(err))
                current_app.logger.debug("Auth failed, logging out, starting over.")
                session['access_token'] = None
                return redirect(url_for("quickbooks/.index"))

            except quickbooks.exceptions.AuthorizationException as err:
                if not refreshed:
                    current_app.logger.debug("Auth failed, trying refresh")
                    refreshed = True
                    current_app.quickbooks_auth_client.refresh()
                    continue

                flash("Authorization failed, please try again: %s" % err)
                current_app.logger.debug("Auth failed, logging out, starting over.")
                session['access_token'] = None
                return redirect(url_for("quickbooks/.index"))

            except quickbooks.exceptions.QuickbooksException as err:
                flash("Query failed loading all customers: %s" % err)
                raise InternalServerError

        # Calculate a pile of dates, based on today date. Figure out
        # which quarter we're in, and the dates of this and 2 prior quarters
        dt = datetime.datetime.now()
        today = dt.strftime("%m-%d-%Y")
        q = (dt.month-1) // 3
        pq = (q + 3) % 4
        ppq = (pq + 3) % 4

        year = dt.year
        (q_start, q_end) = self.calculate_quarter_dates(year, q)
        if pq > q:
            year -= 1
        (pq_start, pq_end) = self.calculate_quarter_dates(year, pq)
        if ppq > pq:
            year -= 1
        (ppq_start, ppq_end) = self.calculate_quarter_dates(year ,ppq)

        # Iterate over all the invoices, parse their dates and arrange them into the invoice dict, by customer
        invoice_dict = {}
        for invoice in invoices:
            customer_id = invoice.CustomerRef.value
            if customer_id not in invoice_dict:
                invoice_dict[customer_id] = []

            create_time = parse(invoice.TxnDate).strftime("%m-%d-%Y")
            try:
                begin_dt = parse(invoice.CustomField[1].StringValue)
                begin_date = begin_dt.strftime("%m-%d-%Y")
            except ValueError:
                begin_date = ""
                begin_dt = None

            try:
                end_dt = parse(invoice.CustomField[2].StringValue)
                end_date = end_dt.strftime("%m-%d-%Y")
            except ValueError:
                end_date = ""
                end_dt = None

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
                'begin_dt' : begin_dt,
                'end' : end_date,
                'end_dt' : end_dt,
                'service' : tier,
                'number' : invoice.DocNumber,
                'currency' : invoice.CurrencyRef.value,
                'qty' : invoice.Line[0].SalesItemLineDetail.Qty,
                'price' : invoice.Line[0].SalesItemLineDetail.UnitPrice
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
            try:
                price = invoices[0]['price']
            except IndexError:
                price = 0

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
                self.add_new_invoice(invoices[0], cust, q_start, q_end, today, 3, price)
                ready_to_invoice.append(cust)
                continue

            # If the customer is not invoiced in arrears and the last invoice is a partial invoice last quarter -> ready to invoice new customer
            if not is_arrears and invoices[0]['end'] == pq_end:
                cust['name'] += " (new customer)"
                self.add_new_invoice(invoices[0], cust, q_start, q_end, today, 3, price)
                ready_to_invoice.append(cust)
                continue

            # If the customer is invoiced in arrears and the last invoice looks to be from last last quarter -> ready to invoice
            if is_arrears and invoices[0]['begin'] == ppq_start and invoices[0]['end'] == ppq_end:
                self.add_new_invoice(invoices[0], cust, pq_start, pq_end, today, 3, price)
                ready_to_invoice.append(cust)
                continue

            # If the customer is invoiced in arrears and the last invoice was from the prior quarter -> current
            if is_arrears and invoices[0]['begin'] == pq_start and invoices[0]['end'] == pq_end:
                current.append(cust)
                continue

            # Check to see if this is an annual invoice
            try:
                end_dt = invoices[0]['end_dt']
                begin_dt = invoices[0]['begin_dt']
                delta = end_dt - begin_dt
                if delta.days > 359 and delta.days < 366:
                    cust['name'] += " (annual)"
                    if time.mktime(end_dt.timetuple()) <= time.time():
                        end_date = datetime.date(end_dt.year + 1, end_dt.month, end_dt.day).strftime("%m-%d-%Y")
                        begin_date = datetime.date(begin_dt.year + 1, begin_dt.month, begin_dt.day).strftime("%m-%d-%Y")
                        self.add_new_invoice(invoices[0], cust, begin_date, end_date, today, 12, price)
                        ready_to_invoice.append(cust)
                    else:
                        current.append(cust)

                    continue
            except TypeError:
                wtf.append(cust)
                continue

            # If the end date is after the curent date, then consider it current
            if time.mktime(end_dt.timetuple()) > time.time():
                current.append(cust)
                continue

            # Everyone else, WTF?
            wtf.append(cust)

        return render_template("quickbooks/index.html", ready=ready_to_invoice, wtf=wtf, current=current)


    @expose('/', methods=['POST'])
    def submit(self):
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
            qty = request.form.get("qty_%d" % customer)
            price = request.form.get("price_%d" % customer)

            invoices.append( { 'customer' : customer_id, 'begin' : begin_date, 'end' : end_date, 'base_invoice' : base_invoice, 'qty' : qty, 'price' : price })
            customer += 1 

        # setup the access nonsense again
        access_token = session.get('access_token', None)
        refresh_token = session.get('refresh_token', None)
        realm = session.get('realm', None)

        if not access_token:
            flash("access token lost. log in again.")
            return render_template("quickbooks/login.html")

        # Now call create invoices and deal with possible errors
        try:
            client = get_client(realm, refresh_token)
            self.create_invoices(client, invoices)

        except AuthClientError as err:
            flash("Authorization failed, please try again: %s" % err)
            session['access_token'] = None
            session['realm'] = None
            return redirect(url_for("quickbooks/.index"))
        except quickbooks.exceptions.AuthorizationException as err:
            flash("Authorization failed, please try again: %s" % err)
            session['access_token'] = None
            session['realm'] = None
            return redirect(url_for("quickbooks/.index"))

        except quickbooks.exceptions.QuickbooksException as err:
            flash("Failed to submit some invoices!" % err)
            raise InternalServerError

        flash("Invoices created -- make sure to send them!")
        return redirect(url_for("quickbooks/.index"))


    @expose('/login/')
    def login(self):
        '''
        Login to quickbooks, oauth2 callback
        '''
        return redirect(current_app.quickbooks_auth_client.get_authorization_url([Scopes.ACCOUNTING]))


    @expose('/logout/')
    def logout(self):
        '''
        Logout from QuickBooks
        '''

        session['access_token'] = None
        session['realm'] = None

        return redirect(url_for("quickbooks/.index"))


    @expose('/callback/')
    def callback(self):
        '''
        OAuth2 login callback function. the URL of this must match exactly what is in the QB App profile
        '''
        code = request.args.get('code')
        realm = request.args.get('realmId')
        refresh_token = request.args.get('realmId')

        current_app.quickbooks_auth_client.get_bearer_token(code, realm_id=realm)
        session['access_token'] = current_app.quickbooks_auth_client.access_token
        session['refresh_token'] = current_app.quickbooks_auth_client.refresh_token
        session['realm'] = realm

        return redirect(url_for("quickbooks/.index"))

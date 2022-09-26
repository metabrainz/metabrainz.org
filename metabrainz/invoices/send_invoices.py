import datetime
import io
import time
from decimal import Decimal

from flask import current_app
from intuitlib.enums import Scopes
from intuitlib.client import AuthClient
from quickbooks import QuickBooks
from quickbooks.objects.customer import Customer
from quickbooks.objects.invoice import Invoice, DeliveryInfo
from quickbooks.objects.detailline import SalesItemLineDetail
from quickbooks import exceptions
from intuitlib.exceptions import AuthClientError

from brainzutils import cache
from metabrainz.mail import send_mail

SEND_DELAY = 5
MAIL_BODY = """To: %s %s (%s)

Here is your next invoice! For information on how to pay us, please see https://metabrainz.org/payment

Thanks!

The MetaBrainz Foundation ( accounting@metabrainz.org ) 


================================
Invoice Summary:

Invoice number: %s
Invoice date: %s
Due date: %s
Invoice amount: %s%s
================================

Please see the attached PDF file for full details."""


class QuickBooksInvoiceSender():
    """ This class uses the QuickBooks API to sent invoices from our own mail ifrastructure. """

    def __init__(self):
        QuickBooks.enable_global()
        self.auth_client = AuthClient(
            client_id=current_app.config["QUICKBOOKS_CLIENT_ID"],
            client_secret=current_app.config["QUICKBOOKS_CLIENT_SECRET"],
            environment=current_app.config["QUICKBOOKS_SANDBOX"],
            redirect_uri=current_app.config["QUICKBOOKS_CALLBACK_URL"]
        )

    def get_client(self):
        """ Create the client object from the cached credientials and return it. """

        refresh_token = cache.get("qb_refresh_token")
        realm = cache.get("qb_realm")

        if not refresh_token or not realm:
            current_app.logger.info("Could not fetch OAuth credentials from redis.")
            current_app.logger.info("Load https://metabrainz.org/admin/quickbooks/ to push the credentials to redis.")
            return None

        return QuickBooks(
            auth_client=self.auth_client,
            refresh_token=refresh_token,
            company_id=realm
        )

    def mark_invoice_sent(self, client, invoice):
        """ Given the client and invoice, mark this invoice as sent """

        invoice.EmailStatus = "EmailSent"
        if invoice.DeliveryInfo is None:
            invoice.DeliveryInfo = DeliveryInfo()
            invoice.DeliveryInfo.DeliveryType = "Email"

        invoice.DeliveryInfo.DeliveryTime = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%dT%H:%M:%S")
        try:
            invoice.save(qb=client)
            return True
        except exceptions.ValidationException as err:
            current_app.logger.info(err.detail)
            return False

    def send_invoice(self, client, invoice, customer):
        """ Given a client, invoice and its customer object, send the invoice to the customer. """

        current_app.logger.info("  sending invoice")
        emails = [e.strip() for e in str(invoice.BillEmail).split(",")]
        emails.append("accounting@metabrainz.org")
        text = MAIL_BODY % (customer.GivenName,
                            customer.FamilyName,
                            customer.DisplayName,
                            invoice.DocNumber,
                            invoice.TxnDate,
                            invoice.DueDate,
                            "%.2f" % float(invoice.TotalAmt),
                            invoice.CurrencyRef.value)
        pdf = invoice.download_pdf(qb=client)
        pdf = io.BytesIO(pdf)
        send_mail(
            subject="Invoice %s from The MetaBrainz Foundation" % invoice.DocNumber,
            text=text,
            attachments=[(pdf, 'pdf', '%s.pdf' % invoice.DocNumber)],
            recipients=emails,
            from_addr="accounting@metabrainz.org",
            from_name="MetaBrainz Accounting Department"
        )
        self.mark_invoice_sent(client, invoice)
        current_app.logger.info("  wait")
        time.sleep(SEND_DELAY)

    def send_invoices(self):
        """ Main entry point that inspects the last 300 invoices, marks voided ones as sent (as to 
            ignore them in future runs, asks for feedback about invoices that are unclear and sends
            the rest. """

        client = self.get_client()
        if not client:
            return

        invoices = Invoice.query("select * from invoice order by metadata.createtime desc maxresults 300", qb=client)
        if not invoices:
            current_app.logger.info("Cannot fetch list of invoices")
            return

        for invoice in invoices:
            if invoice.EmailStatus == "EmailSent":
                continue

            current_app.logger.info("Invoice %s with status %s" % (invoice.DocNumber, invoice.EmailStatus))
            if float(invoice.TotalAmt) == 0.0:
                current_app.logger.info("  marking zero amount invoice %s as sent." % invoice.DocNumber)
                self.mark_invoice_sent(client, invoice)
                continue

            customer = Customer.get(int(invoice.CustomerRef.value), qb=client)
            if customer.Notes.find("donotsend") >= 0:
                current_app.logger.info("  marking donotsend invoice %s as sent, without sending." % invoice.DocNumber)
                self.mark_invoice_sent(client, invoice)

            if invoice.EmailStatus == "NotSet":
                current_app.logger.info("  To '%s' marked as NotSet." % customer.DisplayName)
                while True:
                    resp = input("  Send [s], Mark sent [m], Ignore [i]:").strip().lower()
                    if resp is None or len(resp) == 0 or resp[0] not in "smi":
                        current_app.logger.info("  select one of the given options!")
                        continue

                    if resp[0] == "s":
                        self.send_invoice(client, invoice, customer)
                        current_app.logger.info("  invoice sent!")
                    elif resp[0] == "m":
                        self.mark_invoice_sent(client, invoice)
                        current_app.logger.info("  invoice marked as sent, without being sent!")

                    break

                continue

            self.send_invoice(client, invoice, customer)
            current_app.logger.info("  invoice sent!")

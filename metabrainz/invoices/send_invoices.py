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

    def __init__(self):
        QuickBooks.enable_global()
        self.auth_client = AuthClient(
            client_id=current_app.config["QUICKBOOKS_CLIENT_ID"],
            client_secret=current_app.config["QUICKBOOKS_CLIENT_SECRET"],
            environment=current_app.config["QUICKBOOKS_SANDBOX"],
            redirect_uri=current_app.config["QUICKBOOKS_CALLBACK_URL"]
        )


    def get_client(self):
        refresh_token = cache.get("qb_refresh_token")
        realm = cache.get("qb_realm")

        if not refresh_token or not realm:
            print("Could not fetch OAuth credentials from redis.")
            print("Load https://test.metabrainz.org/admin/quickbooks/ to push the credentials to redis.")
            return None

        return QuickBooks(
            auth_client=self.auth_client,
            refresh_token=refresh_token,
            company_id=realm
        )

    def mark_invoice_sent(self, client, invoice):
        invoice.EmailStatus = "EmailSent"
        if invoice.DeliveryInfo is None:
            invoice.DeliveryInfo = DeliveryInfo()
            invoice.DeliveryInfo.DeliveryType = "Email"
            
        invoice.DeliveryInfo.DeliveryTime = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%dT%H:%M:%S")
        try:
            invoice.save(qb=client)
            return True
        except exceptions.ValidationException as err:
            print(err.detail)
            return False

    def send_invoice(self, client, invoice, customer):
        emails = [ e.strip() for e in str(invoice.BillEmail).split(",") ]
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

    def send_invoices(self):

        client = self.get_client()
        if not client:
            return

        invoices = Invoice.query("select * from invoice order by metadata.createtime desc maxresults 300", qb=client)
        if not invoices:
            print("Cannot fetch list of invoices")
            return

        for invoice in invoices:
            if invoice.EmailStatus == "EmailSent":
                continue

            print("Invoice %s with status %s" % (invoice.DocNumber, invoice.EmailStatus))
            if float(invoice.TotalAmt) == 0.0:
                print("  marking zero amount invoice %s as sent." % invoice.DocNumber)
                self.mark_invoice_sent(self, client, invoice)
                continue

            customer = Customer.get(int(invoice.CustomerRef.value), qb=client)
            if customer.Notes.find("donotsend") >= 0:
                print("  marking donotsend invoice %s as sent, without sending." % invoice.DocNumber)
                self.mark_invoice_sent(client, invoice)

            if invoice.EmailStatus == "NotSet":
                print("  To '%s' marked as NotSet." % customer.DisplayName)
                while True:
                    print("  Send [s], Mark sent [m], Ignore [i]:", end="")
                    resp = input().strip().lower()
                    if resp is None or len(resp) == 0 or resp[0] not in "smi":
                        print("  select one of the given options!")  

                    if resp[0] == "s":
                        self.send_invoice(client, invoice)
                        print("  invoice sent!")
                        break
                    elif resp[0] == "m":
                        self.mark_invoice_sent(client, invoice)
                        print("  invoice marked as sent, without being sent!")
                        break
                    else:
                        break

                continue

            self.send_invoice(client, invoice, customer)
            print("  invoice sent!")

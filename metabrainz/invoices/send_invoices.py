import datetime
import io
import time

from flask import current_app
from intuitlib.enums import Scopes
from intuitlib.client import AuthClient
import intuitlib.exceptions
from quickbooks import QuickBooks
from quickbooks.objects.customer import Customer
from quickbooks.objects.invoice import Invoice, DeliveryInfo
from quickbooks.objects.detailline import SalesItemLineDetail
from quickbooks import exceptions

from brainzutils import cache
from brainzutils.mail import send_mail

SEND_DELAY = 5
MAIL_SUBJECT = "Invoice {invoice_number} and a note from the MetaBrainz Board"
INVOICE_SUMMARY = """================================
Invoice Summary:

Invoice number: {invoice_number}
Invoice date: {invoice_date}
Due date: {due_date}
Invoice amount: {invoice_amount} {currency}
================================"""
MAIL_BODY = """Dear {supporter_name},

{invoice_summary}

A note from the MetaBrainz Board

It is with great sadness that we write to share that our dear friend Robert Kaye — founder and Executive Director of MetaBrainz Foundation — died suddenly on February 20th. Many of you will have heard this terrible news already; for those learning about it now, we are sorry to be the ones breaking this news.

Rob built his life’s work on a simple but radical idea: that the world's music data should be open, owned by the community that builds it, and be reliable and free for anyone to build on. Over two decades, he turned that idea into MusicBrainz, ListenBrainz, Picard, and the infrastructure that quietly underpins many of the world's most-used music products and services. Your support made that possible. In March, the team, the community, and Rob's family gathered in Barcelona to celebrate his life — a fitting send-off for someone whose work brought so many people together.

The work continues. Nicolás Tamargo, who has been with the Foundation a very long time,  has stepped in as Interim Executive Director to keep things steady. Many of you will know Nicolás already — he has been Secretary to our Board for several years and a long-time contributor to the project, and we're lucky to have him at the helm right now. Alongside his work, we've opened a formal search for a permanent ED to lead the MetaBrainz Foundation through a time of real change in music, data, and AI. If someone in your world comes  to mind — with roots in open source or the music community — we'd love an introduction. Full details here: https://blog.metabrainz.org/2026/04/14/seeking-a-new-executive-director/

The mission matters more than ever. As AI, rights, and data systems become ever more consolidated and opaque, the case for an independent, community-maintained source of truth only grows stronger. Meanwhile, if anything is on your mind, just reply to this email and one of us will come back to you.

Our invoice for the coming period is attached. Your continued support keeps the team working, the volunteers supported, and the data flowing — and it is, honestly, the most meaningful way we know to honour what Rob spent his life building.

With gratitude,
The MetaBrainz Board
Nick Ashton-Hart, Paul Bennun, Cory Doctorow, Matthew Hawn, Rassami Hök Ljungberg, Hazel Savage"""


REMINDER_MAIL_BODY = """To: %s %s (%s)

Hello!

Our records show that the attached invoices remains outstanding or not marked as paid. We frequently
do not get invoice numbers attached to the payments we receive, which makes reconciling invoices
difficult, so please bear with us if you've made payment already. If you think we've sent you this
reminder in error, we apologize -- please send us a note on which date you made payment on this invoice and
which service you used to pay the invoice and we will get it credited.

For information on how to pay us, please see https://metabrainz.org/payment

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
            current_app.logger.warn("Could not fetch OAuth credentials from redis.")
            current_app.logger.warn("Load https://metabrainz.org/admin/quickbooks/ to push the credentials to redis.")
            return None

        try:
            return QuickBooks(
                auth_client=self.auth_client,
                refresh_token=refresh_token,
                company_id=realm
            )
        except intuitlib.exceptions.AuthClientError as err:
            current_app.logger.warn("Could not log into quickbooks. Re-log in on the web to fix.")
            return None


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
            current_app.logger.warn(err.detail)
            return False

    @staticmethod
    def get_supporter_name(customer):
        for field in ("DisplayName", "GivenName", "CompanyName"):
            value = getattr(customer, field, None)
            if value:
                return value

        full_name = " ".join(
            part for part in (getattr(customer, "GivenName", None), getattr(customer, "FamilyName", None))
            if part
        )
        if full_name:
            return full_name

        return "Supporter"

    @staticmethod
    def format_invoice_summary(invoice):
        return INVOICE_SUMMARY.format(
            invoice_number=invoice.DocNumber,
            invoice_date=invoice.TxnDate,
            due_date=invoice.DueDate,
            invoice_amount="%.2f" % float(invoice.TotalAmt),
            currency=invoice.CurrencyRef.value,
        )

    @classmethod
    def format_invoice_mail_body(cls, invoice, customer):
        return MAIL_BODY.format(
            supporter_name=cls.get_supporter_name(customer),
            invoice_summary=cls.format_invoice_summary(invoice),
        )

    @staticmethod
    def format_invoice_mail_subject(invoice, subject_template=MAIL_SUBJECT):
        return subject_template.format(invoice_number=invoice.DocNumber)

    def send_invoice(self, client, invoice, customer):
        """ Given a client, invoice and its customer object, send the invoice to the customer. """

        current_app.logger.warn("  sending invoice")
        emails = [e.strip() for e in str(invoice.BillEmail).split(",")]
        emails.append("accounting@metabrainz.org")
        text = self.format_invoice_mail_body(invoice, customer)
        pdf = invoice.download_pdf(qb=client)
        pdf = io.BytesIO(pdf)
        send_mail(
            subject=self.format_invoice_mail_subject(invoice),
            text=text,
            attachments=[(pdf, 'pdf', '%s.pdf' % invoice.DocNumber)],
            recipients=emails,
            from_addr="accounting@metabrainz.org",
            from_name="MetaBrainz Accounting Department"
        )
        self.mark_invoice_sent(client, invoice)

        current_app.logger.warn("  wait")
        time.sleep(SEND_DELAY)

    def send_invoices(self):
        """ Main entry point that inspects the last 300 invoices, marks voided ones as sent (as to 
            ignore them in future runs, asks for feedback about invoices that are unclear and sends
            the rest. """

        current_app.logger.warn("Find invoices to send...")
        client = self.get_client()
        if not client:
            current_app.logger.warn("Cannot get client -- have you logged into QuickBooks web within the last hour?")
            return

        invoices = Invoice.query("select * from invoice order by metadata.createtime desc maxresults 300", qb=client)
        if not invoices:
            current_app.logger.warn("Cannot fetch list of invoices")
            return

        for invoice in invoices:
            if invoice.EmailStatus == "EmailSent":
                current_app.logger.warn("Skip invoice %s with status %s" % (invoice.DocNumber, invoice.EmailStatus))
                continue

            if invoice.DocNumber is None:
                current_app.logger.warn("Skip invoice %s. Bad invoice number." % invoice.DocNumber)
                continue

            current_app.logger.warn("Invoice %s with status %s" % (invoice.DocNumber, invoice.EmailStatus))
            if float(invoice.TotalAmt) == 0.0:
                current_app.logger.warn("  marking zero amount invoice %s as sent." % invoice.DocNumber)
                self.mark_invoice_sent(client, invoice)
                continue

            customer = Customer.get(int(invoice.CustomerRef.value), qb=client)
            if customer.Notes.find("donotsend") >= 0:
                current_app.logger.warn("  marking donotsend invoice %s as sent, without sending." % invoice.DocNumber)
                self.mark_invoice_sent(client, invoice)
                continue

            if invoice.EmailStatus == "NotSet":
                current_app.logger.warn("  To '%s' marked as NotSet." % customer.DisplayName)
                while True:
                    resp = input("  Send [s], Mark sent [m], Ignore [i]:").strip().lower()
                    if resp is None or len(resp) == 0 or resp[0] not in "smi":
                        current_app.logger.warn("  select one of the given options!")
                        continue

                    if resp[0] == "s":
                        self.send_invoice(client, invoice, customer)
                        current_app.logger.warn("  invoice sent!")
                    elif resp[0] == "m":
                        self.mark_invoice_sent(client, invoice)
                        current_app.logger.warn("  invoice marked as sent, without being sent!")

                    break

                continue

            self.send_invoice(client, invoice, customer)
            current_app.logger.warn("  invoice sent!")

    def send_invoice_reminder(self, client, invoice, customer):
        """ Given a client, invoice and its customer object, send the invoice to the customer. """

        current_app.logger.warn("  sending invoice")
        emails = [e.strip() for e in str(invoice.BillEmail).split(",")]
        emails.append("accounting@metabrainz.org")
        text = REMINDER_MAIL_BODY % (customer.GivenName,
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
            subject="Invoice %s reminder from The MetaBrainz Foundation" % invoice.DocNumber,
            text=text,
            attachments=[(pdf, 'pdf', '%s.pdf' % invoice.DocNumber)],
            recipients=emails,
            from_addr="accounting@metabrainz.org",
            from_name="MetaBrainz Accounting Department"
        )

        current_app.logger.warn("  wait")
        time.sleep(SEND_DELAY)

    def send_invoice_reminders(self):
        client = self.get_client()
        if not client:
            current_app.logger.warn("Cannot get client -- have you logged into QuickBooks web within the last hour?")
            return

        due_date = datetime.datetime.now() - datetime.timedelta(days=182)
        due_date = "%d-%02d-%02d" % (due_date.year, due_date.month, due_date.day)
        invoices = Invoice.query(f"select * from invoice where balance > '0.0' and duedate < '{due_date}' order by metadata.createtime desc maxresults 300", qb=client)
        if not invoices:
            current_app.logger.warn("Cannot fetch list of invoices")
            return

        current_app.logger.warn(f"fetched %d invoices" % len(invoices))
        for invoice in invoices:
            customer = Customer.get(int(invoice.CustomerRef.value), qb=client)
            if customer.Notes.find("donotsend") >= 0:
                current_app.logger.warn("skipping donotsend invoice %s." % invoice.DocNumber)
                continue

            current_app.logger.warn("Invoice %s with balance %s due on %s" % (invoice.DocNumber, invoice.Balance, invoice.DueDate))
            self.send_invoice_reminder(client, invoice, customer)

#!/usr/bin/env python3

import datetime 
import time
import redis
from intuitlib.enums import Scopes
from intuitlib.client import AuthClient
from quickbooks import QuickBooks
from quickbooks.objects.customer import Customer
from quickbooks.objects.invoice import Invoice
from quickbooks.objects.detailline import SalesItemLineDetail
from intuitlib.exceptions import AuthClientError

import config


class QuickBooksInvoiceSender():

    def __init__(self):
        QuickBooks.enable_global()
        self.auth_client = AuthClient(
            client_id=config.QUICKBOOKS_CLIENT_ID,
            client_secret=config.QUICKBOOKS_CLIENT_SECRET,
            environment=config.QUICKBOOKS_SANDBOX,
            redirect_uri=config.REDIRECT_URL
        )
        self.redis = redis.Redis(host=config.REDIS_HOST, port=config.REDIS_PORT, db=0, namespace=config.REDIS_NAMESPACE)


    def get_client(self):
        refresh_token = redis.get("qb_refresh_token")
        realm = redis.get("qb_realm")

        if not refresh_token or not realm:
            print("Could not fetch OAuth credentials from redis.")

        return QuickBooks(
            auth_client=self.auth_client,
            refresh_token=refresh_token,
            company_id=realm
        )

    def send_invoices(invoices):

        client = get_client()

        invoices = Invoice.query("select * from invoice order by metadata.createtime desc maxresults 300", qb=self.client)
        if not invoices:
            print("Cannot fetch list of invoices")
            return

        for invoice in invoice_list:
            print("Fetched %d with status %s" % (invoice.DocNumber, invoice.EmailStatus))


qb = QuickBooksInvoiceSender()
qb.send_invoices()

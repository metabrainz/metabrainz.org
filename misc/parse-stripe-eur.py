#!/usr/bin/env python3

from dateutil import parser

# Parse the stripe balance report:  https://dashboard.stripe.com/reports/balance

import sys, os
from decimal import Decimal
import csv

def parse_payouts(payouts_file):
    pay = None
    try:
        pay = open(payouts_file, "r")
        reader = csv.DictReader(pay)
    except IOError:
        print("Cannot open payouts file %s" % payouts_file)
        exit(0)

    payouts = []
    for row in reader:
        for i, (k, v) in enumerate(row.items()):
            print("%d %-40s %s" % (i, k, v))
        print()

        amount = -Decimal(row["gross"].replace(",", "."))
        date = parser.parse(row["effective_at_utc"] + " UTC")
        payouts.append({ "date": date, "amount": amount, "sender": "PAYOUT", "fee": Decimal(0.0) })

    return payouts


if len(sys.argv) < 4:
    print("Usage parse-stripe.py <stripe csv file> <payout csv> <starting balance> <qbo csv file>")
    sys.exit(-1)

fp = None
try:
    fp = open(sys.argv[1], "r")
except IOError:
    print("Cannot open input file %s" % sys.argv[1])
    sys.exit(0)

payouts = parse_payouts(sys.argv[2])
balance = Decimal(sys.argv[3].replace(",", ""))

_out = None
try:
    _out = open(sys.argv[4], "w")
except IOError:
    print("Cannot open output file %s" % sys.argv[4])
    exit(0)


out = csv.writer(_out, quoting=csv.QUOTE_MINIMAL)
out.writerow(["Date","Description","Amount"])

reader = csv.DictReader(fp)
rows = list(reader)
rows.reverse()
fp.close()

data = []
for row in rows:
    for i, (k, v) in enumerate(row.items()):
        print("%d %-40s %s" % (i, k, v))
    print()

    date = parser.parse(row["created_utc"] + " UTC")
    amount = Decimal(row["gross"].replace(",", "."))
    fee = Decimal(row["fee"].replace(",", "."))
    description = row["description"].lower()
    editor = row.get("payment_metadata[editor]", "")
    customer_name = row.get("customer_name", "")

    if amount < Decimal(0.0):
        sender = "Stripe Additional Fee"
    elif "subscription" in description:
        sender = "Subscription from %s" % customer_name if customer_name else "Subscription"
        if editor:
            sender += ", editor %s" % editor
    elif "donation" in description:
        sender = "Donation from %s" % customer_name if customer_name else "Donation"
        if editor:
            sender += ", editor %s" % editor
    else:
        sender = row["description"]

    invoice_number = row.get("payment_metadata[invoice_number]", "")
    if invoice_number != "":
        sender += " (inv #%s)" % invoice_number

    data.append({ "date": date, "amount": amount, "fee": fee, "sender": sender })

data.extend(payouts)
data = sorted(data, key=lambda a: a["date"])

for row in data:
    print(row)

for entry in data:
    date = "%s/%s/%s" % (entry["date"].month, entry["date"].day, entry["date"].year)

    if entry["fee"] != Decimal(0.0):
        out.writerow([date, "Stripe fee", str(-entry["fee"])])
    out.writerow([date, entry["sender"], str(entry["amount"])])

    balance = balance + entry["amount"]
    print("%s,%-60s,%.2f,%.2f" % (date, entry["sender"], entry["amount"], balance))
    if entry["fee"] != Decimal(0.0):
        balance = balance - entry["fee"]
        print("%s,%-60s,%.2f,%.2f" % (date, "Stripe fee", -entry["fee"], balance))

_out.close()

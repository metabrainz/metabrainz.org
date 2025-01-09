#!/usr/bin/env python3

from datetime import datetime
from dateutil import parser

# Parse the stripe balance report:  https://dashboard.stripe.com/reports/balance

import sys, os
from decimal import Decimal
import csv

def parse_payouts(payouts_file):
    pay = None
    try:
        pay = open(payouts_file, "r")
        reader = csv.reader(pay)
    except IOError:
        print("Cannot open payouts file %s" % payouts_file)
        exit(0)

    payouts = []
    head = None
    for i, row in enumerate(reader):
        if i == 0:
            head = row
            continue

        for i, d in enumerate(zip(head, row)):
            print("%d %-40s %s" % (i, d[0], d[1]))
        print()

        amount = -Decimal(row[1].replace(",", "."))
        date = parser.parse(row[5] + " UTC")
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

trans = []
head = None
reader = csv.reader(fp)

rows = []
for i, row in enumerate(reader):
    if not i:
        head = row
        continue

    rows.append(row)

rows.reverse()
fp.close()

data = []
for row in rows:
    for i, d in enumerate(zip(head, row)):
        print("%d %-40s %s" % (i, d[0], d[1]))
    print()

    date = parser.parse(row[2] + " UTC")
    amount = Decimal(row[6].replace(",", "."))
    fee = Decimal(row[7].replace(",", "."))
    sender = row[19]

    if not sender:
        sender = "Subscription from %s" % row[41]
        if row[61]:
            sender += ", editor %s" % row[61]
        if row[62]:
            sender += ", email %s" % row[62]

    if amount < Decimal(0.0):
        sender = "Stripe Additional Fee"

    if row[62] != "":
        sender += " (inv #%s)" % row[62]

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

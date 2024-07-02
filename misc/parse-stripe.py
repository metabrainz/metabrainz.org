#!/usr/bin/env python3

from datetime import datetime
from dateutil import parser

# Parse the report downloaded from https://dashboard.stripe.com/reports/balance

import sys, os
from decimal import Decimal
import csv

if len(sys.argv) < 4:
    print("Usage parse-stripe.py <stripe csv file> <qbo csv file> [beginning balance]")
    sys.exit(-1)

fp = None
try:
    fp = open(sys.argv[1], "r")
except IOError:
    print("Cannot open input file %s" % sys.argv[1])
    sys.exit(0)

_out = None
try:
    _out = open(sys.argv[2], "w")
except IOError:
    print("Cannot open output file %s" % sys.argv[2])
    exit(0)

try:
    balance = Decimal(sys.argv[3])
except IndexError:
    balance = None

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

for row in rows:

#    for i, d in enumerate(zip(head, row)):
#        print("%d %-40s %s" % (i, d[0], d[1]))
#    print()

    # TODO: Convert to PST/PDT
    date = parser.parse(row[1] + " UTC")
    date = "%s/%s/%s" % (date.month, date.day, date.year)
    gross = Decimal(row[2])
    fee = Decimal(row[11])
    sender = row[22]
    memo = row[10]

    if row[84] != "":
        sender += " (inv #%s)" % row[84]

    out.writerow([date, "Stripe fee", "-" + str(fee)])
    out.writerow([date, sender, str(gross)])
    if balance is not None:
        balance = balance + gross
        print("%s %-40s %10s %10s" % (date, sender, str(gross), str(balance)))
        balance = balance - fee
        print("%s %-40s %10s %10s" % (date, "Stripe fee", str(fee), str(balance)))

fp.close()
_out.close()

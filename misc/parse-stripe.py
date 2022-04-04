#!/usr/bin/env python3

# Parse the report downloaded from https://dashboard.stripe.com/reports/balance

import sys, os
from decimal import Decimal
import csv

def toFloat(svalue):
    return float(svalue.replace(",", ""))

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
for i, row in enumerate(reader):
    if not i:
        head = row
        continue

    if row[1] == 'payout':
        continue

#    for i, d in enumerate(zip(head, row)):
#        print("%d %-40s %s" % (i, d[0], d[1]))
#    print()

    date = row[3].split(' ')[0]
    date = date.split('-')
    date = "%s/%s/%s" % (date[1], date[2], date[0])
    gross = Decimal(row[4])
    fee = Decimal(row[9])

    if row[1] == "contribution":
        sender = "Climate contribution"
        if balance is not None:
            balance = balance + gross
            print("%s %-40s %10s %10s" % (date, sender, str(gross), str(balance)))
        out.writerow([date, sender, gross])
        continue

    sender = row[25]
    if not sender or sender.strip() == "":
        sender = row[17]
    memo = row[1]

    if row[1].find("Invoice") >= 0:
        inv = row[1][row[1].find("Invoice") + 8:]
        sender += " (inv #%s)" % inv

    out.writerow([date, "Stripe fee", "-" + str(fee)])
    out.writerow([date, sender, str(gross)])
    if balance is not None:
        balance = balance + gross
        print("%s %-40s %10s %10s" % (date, sender, str(gross), str(balance)))
        balance = balance - fee
        print("%s %-40s %10s %10s" % (date, "Stripe fee", str(-fee), str(balance)))

fp.close()
_out.close()

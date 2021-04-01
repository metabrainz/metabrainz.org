#!/usr/bin/env python

import sys, os
import decimal
import csv

def toFloat(svalue):
    return float(svalue.replace(",", ""))

if len(sys.argv) != 3:
    print("Usage parse-stripe.py <stripe csv file> <qbo csv file>")
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

out = csv.writer(_out, quoting=csv.QUOTE_MINIMAL)
out.writerow(["Date","Description","Amount"])

trans = []
reader = csv.reader(fp)
for i, row in enumerate(reader):
    if not i:
        continue

    if row[1] == 'transfer':
        continue

    if row[12].lower() == 'failed':
        continue

    date = row[3].split(' ')[0]
    date = date.split('-')
    date = "%s/%s/%s" % (date[1], date[2], date[0])
    sender = row[25]
    amount = toFloat(row[7])
    fee = -toFloat(row[9])
    net = amount - fee
    memo = row[1]
    inv = row[54]

    text = sender
    if inv:
        text += " (inv #%s)" % inv

    out.writerow([date, "Stripe fee", "%.2f" % fee])
    out.writerow([date, text, amount])

fp.close()
_out.close()

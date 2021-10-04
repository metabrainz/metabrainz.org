#!/usr/bin/env python3

# Parse the report downloaded from https://dashboard.stripe.com/reports/balance

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


    date = row[1].split(' ')[0]
    date = date.split('-')
    date = "%s/%s/%s" % (date[1], date[2], date[0])
    sender = row[41]
    gross = row[6]
    fee = row[7]
    memo = row[1]
    inv = row[43]

    if inv:
        sender += " (inv #%s)" % inv

    if row[9] == "contribution":
        out.writerow([date, "Climate contribution", gross])
    elif row[9] == "fee":
        out.writerow([date, "Stripe Friends & Family $20K (or local equiv.) Credit", gross])
    else:
        out.writerow([date, "Stripe fee", "-" + fee])
        out.writerow([date, sender, gross])

fp.close()
_out.close()

#!/usr/bin/env python

import sys, os
import decimal
import csv

def toFloat(svalue):
    return float(svalue.replace(",", ""))

fp = None
try:
    fp = open(sys.argv[1], "r")
except IOError:
    print "Cannot open input file %s" % sys.argv[1]
    exit(0)

out = None
try:
    out = open(sys.argv[2], "w")
    out.write("Date,Description,Amount\n")
except IOError:
    print "Cannot open output file %s" % sys.argv[2]
    exit(0)

trans = []
reader = csv.reader(fp)
for i, row in enumerate(reader):
    if not i:
        continue

    if row[1] == 'transfer':
        continue

    print row
    date = row[2].split(' ')[0]
    date = date.split('-')
    date = "%s/%s/%s" % (date[1], date[2], date[0])
    sender = row[24].decode('iso-8859-1') #.encode('utf8')
    amount = toFloat(row[6])
    fee = -toFloat(row[8])
    net = amount - fee
    memo = row[1]

    out.write("%s,%s,%.2f\n" % (date, "Stripe", fee))
    out.write("%s,%s,%.2f\n" % (date, sender.encode('utf-8'), amount))

fp.close()
out.close()

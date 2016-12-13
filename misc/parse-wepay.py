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

    if row[9] == 'withdrawal':
        continue

    print row
    date = row[1].split(' ')[0]
    sender = row[2]
    amount = toFloat(row[11])
    fee = -toFloat(row[12])
    net = amount - fee

    out.write("%s,%s,%.2f\n" % (date, "WePay", fee))
    out.write("%s,%s,%.2f\n" % (date, sender, amount))

fp.close()
out.close()

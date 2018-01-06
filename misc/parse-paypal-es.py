#!/usr/bin/env python

import sys
import re
import csv

def unicode_csv_reader(utf8_data, dialect=csv.excel, **kwargs):
    csv_reader = csv.reader(utf8_data, dialect=dialect, **kwargs)
    for row in csv_reader:
        yield [unicode(cell, 'utf-8') for cell in row]

if len(sys.argv) != 3:
    print "Usage parse-paypal-es.py <paypal csv file> <qbo csv file>"
    sys.exit(-1)

fp = None
try:
    fp = open(sys.argv[1], "r")
except IOError:
    print "Cannot open input file %s" % sys.argv[1]
    sys.exit(0)

out = None
try:
    out = open(sys.argv[2], "w")
except IOError:
    print "Cannot open output file %s" % sys.argv[2]
    sys.exit(0)


out.write("Date,Description,Amount\n")

reader = unicode_csv_reader(fp)
index = 0
for fields in reader:
    if not index:
        index = 1
        continue

    desc = fields[3].encode('utf8')
    dat = fields[0].encode('utf8')
    amount = fields[7].encode('utf8')
    status = fields[5].encode('utf8')
    if status != 'Completed':
        continue

    out.write("%s,%s,%s\n" % (dat, desc, amount))

    desc = "PayPal"
    dat = fields[0].encode('utf8')
    fee = fields[8].encode('utf8')
    if fee and float(fee) != 0.0:
        out.write("%s,%s,%s\n" % (dat, desc, fee))

fp.close()
out.close()

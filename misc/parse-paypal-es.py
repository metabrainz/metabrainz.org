#!/usr/bin/env python

import sys
import re
import csv

def unicode_csv_reader(utf8_data, dialect=csv.excel, **kwargs):
    csv_reader = csv.reader(utf8_data, dialect=dialect, **kwargs)
    for row in csv_reader:
        yield [unicode(cell, 'utf-8') for cell in row]

print "Date,Description,Amount"

reader = unicode_csv_reader(sys.stdin)
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

    print("%s,%s,%s" % (dat, desc, amount))

    desc = "PayPal"
    dat = fields[0].encode('utf8')
    fee = fields[8].encode('utf8')
    if fee and float(fee) != 0.0:
        print("%s,%s,%s" % (dat, desc, fee))

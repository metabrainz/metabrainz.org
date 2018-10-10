#!/usr/bin/env python

import sys
import re
import csv
import datetime
from dateutil.parser import parse
from decimal import *

# header
#"TransferWise ID",Date,Amount,Currency,Description,"Payment Reference","Running Balance","Exchange From","Exchange To","Exchange Rate","Payer Name","Payee Name",
#    "Payee Account Number",Merchant,"Total fees"

def unicode_csv_reader(utf8_data, dialect=csv.excel, **kwargs):
    csv_reader = csv.reader(utf8_data, dialect=dialect, **kwargs)
    for row in csv_reader:
        yield [unicode(cell, 'utf-8') for cell in row]

if len(sys.argv) != 2:
    print "Usage parse-transferwise.py <transferwise csv file>"
    sys.exit(-1)

fp = None
try:
    fp = open(sys.argv[1], "r")
except IOError:
    print "Cannot open input file %s" % sys.argv[1]
    sys.exit(0)


lines = []
reader = unicode_csv_reader(fp)
for line in reader:
    lines.append(line)

lines = lines[1:]
lines.reverse()

output_data = {}

for fields in lines:
    status = fields[3].encode('utf8')
    if status == 'cancelled':
        continue


    desc = fields[14].encode('utf8')
    dat = fields[1].encode('utf8')
    amount = Decimal(fields[7].encode('utf8'))
    fee = Decimal(fields[6].encode('utf8'))
    refs = fields[16].encode('utf8').split(" ")
    currency = fields[4].encode('utf8').lower()

    dt =  parse(dat, dayfirst=True)
    dat = "%02d-%02d-%04d" % (dt.month, dt.day, dt.year)

    if not currency in output_data:
        output_data[currency] = []

    if status == 'refunded':
        desc = "Refund from %s" % desc
        amount = -Decimal(fields[10].encode('utf8'))
        fee = -fee
        
    new_refs = []
    for r in refs:
        if r.startswith("SVWZ+"):
            new_refs.append(r[5:])
            continue

        if r.startswith("EREF+"):
            continue

        new_refs.append(r)

    ref = " ".join(new_refs)

    if desc == "MetaBrainz Foundation Inc.":
        desc = "Funds received (%s)" % ref
        output_data[currency].append([dat, desc, amount])
    else:
        amount = -amount
        desc = desc.replace(",", " ")
        if ref:
            output_data[currency].append([dat, "%s (%s)" % (desc, ref), amount])
        else:
            output_data[currency].append([dat, "%s" % desc, amount])

    if fee and float(fee) != 0.0:
        output_data[currency].append([dat,"TW Fee for payment to %s" % desc, -fee])

fp.close()

now = datetime.datetime.now()
for currency in output_data:
    try:
        filename = "transferwise-%s-%d-%d-%d.csv" % (currency, now.year, now.month, now.day)
        out = open(filename, "w")
    except IOError:
        print "Cannot open output file %s" % filename
        sys.exit(0)

    _out = csv.writer(out, quoting=csv.QUOTE_MINIMAL)
    _out.writerow(["Date","Description","Amount"])
    for line in output_data[currency]:
        _out.writerow(line)
        
    out.close()

#!/usr/bin/env python

import sys
import re
import csv
from dateutil.parser import parse
from decimal import *

# header
#"TransferWise ID",Date,Amount,Currency,Description,"Payment Reference","Running Balance","Exchange From","Exchange To","Exchange Rate","Payer Name","Payee Name",
#    "Payee Account Number",Merchant,"Total fees"

def unicode_csv_reader(utf8_data, dialect=csv.excel, **kwargs):
    csv_reader = csv.reader(utf8_data, dialect=dialect, **kwargs)
    for row in csv_reader:
        yield [cell for cell in row]

if len(sys.argv) != 3:
    print("Usage parse-transferwise.py <transferwise csv file> <qbo csv file>")
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
    sys.exit(0)

out = csv.writer(_out, quoting=csv.QUOTE_MINIMAL)
out.writerow(["Date","Description","Amount"])

lines = []
reader = unicode_csv_reader(fp)
for line in reader:
    lines.append(line)

lines = lines[1:]
lines.reverse()

for fields in lines:
    desc = fields[10]
    if not desc:
        desc = fields[11]
    if not desc:
        desc = fields[4]
    dat = fields[1]
    amount = Decimal(fields[2])
    fee = Decimal(fields[14])
    refs = fields[5].split(" ")

    amount += fee

    dt =  parse(dat, dayfirst=True)
    dat = "%02d-%02d-%04d" % (dt.month, dt.day, dt.year)

    new_refs = []
    for r in refs:
        if r.startswith("SVWZ+"):
            new_refs.append(r[5:])
            continue

        if r.startswith("EREF+"):
            continue

        new_refs.append(r)

    ref = " ".join(new_refs)

    desc = desc.replace(",", " ")
    if ref:
        out.writerow([dat, "%s (%s)" % (desc, ref), amount])
    else:
        out.writerow([dat, desc, amount])

    if fee and float(fee) != 0.0:
        out.writerow([dat,"TW Fee (%s)" % desc, -fee])

fp.close()
_out.close()

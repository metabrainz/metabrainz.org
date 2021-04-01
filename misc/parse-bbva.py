#!/usr/bin/env python

import sys
import re

if len(sys.argv) != 3:
    print("Usage parse-bbva.py <bbva csv file> <qbo csv file>")
    sys.exit(-1)

fp = None
try:
    fp = open(sys.argv[1], "r")
except IOError:
    print("Cannot open input file %s" % sys.argv[1])
    sys.exit(0)

out = None
try:
    out = open(sys.argv[2], "w")
except IOError:
    print("Cannot open output file %s" % sys.argv[2])
    sys.exit(0)

out.write("Date,Description,Amount\n")

lines = fp.readlines()
for line in lines:
    stripped = line.strip()
    if len(stripped) == 0 or not stripped[0].isdigit():
        continue

    fields = stripped.split(',')
    print(fields)

    desc = fields[4]
    if desc.startswith("'"):
        desc = desc [1:]
    if desc.endswith("'"):
        desc = desc [:-1]
    desc = desc.replace(",", " ")
    desc = re.sub("^\d\d\d\d\d\d\d\-", "", desc)
    desc = re.sub("^\d\d\d\d\d\d\d\d\d\d ", "", desc)
    desc = re.sub("^\d\d\d\d\d\d\d\d\d\d\d\d\d\d\d\d ", "", desc)
    desc = re.sub("  ", " ", desc)
    desc = re.sub("  ", " ", desc)
    desc = re.sub("  ", " ", desc)
    desc = re.sub("  ", " ", desc)
    dat = fields[0].split('/')
    dat = "%s/%s/%s" % (dat[1], dat[0], dat[2])
    amount = fields[6]
    out.write("%s,%s,%s\n" % (dat, desc, amount))

#!/usr/bin/env python

import sys
import re

print "Date,Description,Amount"

lines = sys.stdin.readlines()
for line in lines:
    line = line.decode('iso-8859-1').encode('utf8')
    stripped = line.strip()
    if len(stripped) == 0 or not stripped[0].isdigit():
        continue

    fields = stripped.split('\t')

    desc = fields[4]
    if desc.startswith("'"):
        desc = desc [1:]
    if desc.endswith("'"):
        desc = desc [:-1]
    desc = re.sub("^\d\d\d\d\d\d\d\-", "", desc)
    desc = re.sub("^\d\d\d\d\d\d\d\d\d\d ", "", desc)
    desc = re.sub("^\d\d\d\d\d\d\d\d\d\d\d\d\d\d\d\d ", "", desc)
    desc = re.sub("  ", " ", desc)
    desc = re.sub("  ", " ", desc)
    desc = re.sub("  ", " ", desc)
    desc = re.sub("  ", " ", desc)
    dat = fields[0].split('/')
    dat = "%s/%s/%s" % (dat[1], dat[0], dat[2])
    amount = fields[6].replace(".", "")
    amount = amount.replace(",", ".")
    amount = float(amount)
    print("%s,%s,%.2f" % (dat, desc, amount))

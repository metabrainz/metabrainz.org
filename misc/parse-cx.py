#!/usr/bin/env python

import sys
import re

print "Date,Description,Amount"

lines = sys.stdin.readlines()
for line in lines:
    stripped = line.strip()
    if len(stripped) == 0:
        continue

    fields = stripped.split('\t')

    desc = fields[0]
    desc = re.sub("^\d\d\d\d\d\d\d\-", "", desc)
    dat = fields[1].split('-')
    dat = "%s/%s/%s" % (dat[1], dat[0], "2016")
    amount = fields[3].replace(".", "")
    amount = amount.replace(",", ".")
    amount = float(amount)
    print("%s,%s,%.2f" % (dat, desc, amount))

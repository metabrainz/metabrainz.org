#!/usr/bin/env python3

import sys
import re
import csv
from decimal import Decimal, InvalidOperation

def unicode_csv_reader(utf8_data, dialect=csv.excel, **kwargs):
    csv_reader = csv.reader(utf8_data, dialect=dialect, **kwargs)
    for row in csv_reader:
        yield [cell for cell in row]

if len(sys.argv) not in [3,4]:
    print("Usage parse-paypal-es.py <paypal csv file> <qbo csv file> [start balance]")
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

balance = None
try:
    balance = Decimal(sys.argv[3])
except (InvalidOperation, IndexError):
    print("Cannot balance value, ignoring.")


out = csv.writer(_out, quoting=csv.QUOTE_MINIMAL)
out.writerow(["Date","Description","Amount"])

lines = []
reader = unicode_csv_reader(fp)
for line in reader:

    # Filter out lines that complicate everything
    if line[4] in ("General Card Deposit", "Account Hold for Open Authorization", "Reversal of General Account Hold"):
        continue

    if line[5] != 'Completed':
        continue

    lines.append(line)

index = 1
register = []
while True:
    if index >= len(lines):
        break

    fields = lines[index]

    desc = fields[3]
    dat = fields[0]
    gross = fields[7]
    fee = fields[8]
    net = fields[9]
    status = fields[5]
    typ = fields[4]

    currency = fields[6]
    if currency == 'USD' and typ != "General Currency Conversion":
        # Normal native currency transactions
        amount = gross

    elif currency != 'USD':
        print("transaction foreign")
        # Received money in foreign currency
        print(lines[index + 1])
        print(lines[index + 2])
        foreign = Decimal(lines[index + 2][7].replace(",", "")).copy_abs()
        native = Decimal(lines[index + 1][7].replace(",", "")).copy_abs()


        print("native %f, foreign %f" % (native, foreign))

        ratio = native / foreign
        print("conversion rate: %f" % ratio)

        fee = Decimal(fee) / ratio
        fee = Decimal(int(fee * 100)) / 100
        net = native - fee

        amount = native
        if typ == "Express Checkout Payment":
            amount = -amount
        print("amount %f fee: %f\n" % (amount, fee))

        index += 2
        
    desc = desc.replace(",", " ")
    out.writerow([dat, desc, amount])

    if balance is not None:
        balance = balance + Decimal(str(net).replace(",", ""))
        register.append("%s %-40s %10s %10s %10s" % (dat, desc, str(amount), str(fee), str(balance)))

    desc = "PayPal Fee"
    dat = fields[0]
    if fee and Decimal(fee) != 0.0:
        out.writerow([dat, desc, fee])

    index += 1

fp.close()
_out.close()

if register:
    register.reverse()
    for line in register:
        print(line)

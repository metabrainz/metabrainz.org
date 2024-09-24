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
    print("Usage parse-paypal-es.py <paypal csv file> <qbo csv file>")
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

    # Filter out lines that complicate everything
    if line[4] in ("General Card Deposit", "Account Hold for Open Authorization", "Reversal of General Account Hold"):
        continue

    if line[5] != 'Completed':
        continue

    lines.append(line)

index = 0
register = []
balance = None
while True:
    if index >= len(lines):
        break

    fields = lines[index]

    desc = fields[3]
    dat = fields[0]
    gross = Decimal(fields[7].replace(",", ""))
    fee = Decimal(fields[8].replace(",", ""))
    net = Decimal(fields[9].replace(",", ""))
    pp_balance = Decimal(fields[29].replace(",", ""))
    status = fields[5]
    typ = fields[4]

    currency = fields[6]
    if currency == 'USD' and typ != "General Currency Conversion":
        # Normal native currency transactions
        amount = gross

    elif currency != 'USD':
        # Received money in foreign currency
        foreign = Decimal(lines[index + 2][7].replace(",", "")).copy_abs()
        native = Decimal(lines[index + 1][7].replace(",", "")).copy_abs()

        # Get the correct balance, because WTF paypal.
        pp_balance = Decimal(lines[index + 2][29].replace(",", ""))

        ratio = native / foreign
        fee = Decimal(fee) / ratio
        fee = Decimal(int(fee * 100)) / 100
        net = native - fee

        amount = native
        if typ == "Express Checkout Payment":
            amount = -amount

        index += 2

    # If this is the first row, calculate the starting balance
    if balance is None:
        balance = pp_balance - net
        print("Starting balance: ", balance)

    desc = desc.replace(",", " ")
    out.writerow([dat, desc, amount])

    balance = balance + net
    print("%s %-40s %10s %10s %10s %10s" % (dat, desc, str(amount), str(fee),
                                           str(pp_balance), str(balance)))

    desc = "PayPal Fee"
    dat = fields[0]
    if fee and Decimal(fee) != 0.0:
        out.writerow([dat, desc, fee])

    index += 1

print("    Final paypal balance: ", pp_balance)
print("Final calculated balance: ", balance)


fp.close()
_out.close()

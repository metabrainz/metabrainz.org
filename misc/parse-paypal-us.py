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
    lines.append(line)

print("DATE       NAME                                           GROSS       FEE     PP_BAL    BALANCE")

index = 1
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

#    if gross == Decimal(0.0):
#        print("*** skip non balance affecting transaction: %s", desc)
#        index += 1
#        continue

    currency = fields[6]

    try:
        lookahead_type = lines[index + 1][4]
    except IndexError:
        lookahead_type = ""

    if currency == 'USD' and typ != "General Currency Conversion":
        # Normal native currency transactions
        amount = gross

    elif currency != 'USD' and lookahead_type == "General Currency Conversion":

        if typ == "Express Checkout Payment":
            # Received money in foreign currency
            usd = Decimal(lines[index + 1][7].replace(",", "")).copy_abs()
            foreign = Decimal(lines[index + 2][7].replace(",", "")).copy_abs()
        else:
            # Received money in foreign currency
            usd = Decimal(lines[index + 2][7].replace(",", "")).copy_abs()
            foreign = Decimal(lines[index + 1][7].replace(",", "")).copy_abs()

        exchange_rate = usd / foreign
        usd_fee = Decimal(fee) * exchange_rate
        usd_fee = Decimal(int(usd_fee * 100)) / 100
        gross = usd - usd_fee
        fee = usd_fee
        net = usd

        if typ == "Express Checkout Payment":
            gross = -gross
            net = -net

        print("      foreign: ", foreign)
        print("  foreign fee: ", fee)
        print("          net: ", usd)
        print("      usd fee: ", usd_fee)
        print("        gross: ", gross)
        print("exchange rate: ", exchange_rate)


        # Get the correct balance, because WTF paypal.
        pp_balance = Decimal(lines[index + 2][29].replace(",", ""))

        # The balance for express checkout are zero. thanks paypal.
        if pp_balance == Decimal(0.0):
            print("Balance fix!")
            print("balance: %s gross: %s" % (str(balance), str(gross)))
            pp_balance = balance + gross

        print("Balance: ", balance)

        index += 2
    else:
        print(gross, fee)
        if gross + fee == Decimal(0.0):
            print("*** skip non balance affecting transaction: %s", desc)
            index += 1
            continue

        print("Unknown transaction")
        print("%s %-40s %10s %10s %10s %10s" % (dat, desc, str(gross), str(fee),
                                               str(pp_balance), str(balance)))
        assert False

    if balance is None:
        balance = pp_balance - net

    balance = balance + net
    if balance != pp_balance:
        print("     discrepancy: ", (pp_balance - balance))
        print("%s %-40s %10s %10s %10s %10s" % (dat, desc, str(gross), str(fee),
                                               str(pp_balance), str(balance)))
        sys.exit(-1)

    desc = desc.replace(",", " ")
    out.writerow([dat, desc, fee, gross])

    print("%s %-40s %10s %10s %10s %10s" % (dat, desc, str(gross), str(fee),
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

#!/usr/bin/env python3

import sys
import re
import csv
from decimal import Decimal, InvalidOperation

def unicode_csv_reader(utf8_data, dialect=csv.excel, **kwargs):
    csv_reader = csv.reader(utf8_data, dialect=dialect, **kwargs)
    for row in csv_reader:
        yield [cell for cell in row]

def process_file(in_file, out_file, verbose):
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
            elif typ == "Payment Refund":
                # A refund was made. Did we make it or someone else?
                if gross > Decimal(0.0):
                    # Someone else made it
                    usd = Decimal(lines[index + 2][7].replace(",", "")).copy_abs()
                    foreign = Decimal(lines[index + 1][7].replace(",", "")).copy_abs()
                else:
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

            if (verbose):
                print("      foreign: ", foreign)
                print("  foreign fee: ", fee)
                print("          net: ", net)
                print("      usd fee: ", usd_fee)
                print("        gross: ", gross)
                print("exchange rate: ", exchange_rate)


            fee = usd_fee
            net = usd

            gross_fix = False
            if typ == "Express Checkout Payment":
                gross = -gross
                net = -net


            # Get the correct balance, because WTF paypal.
            pp_balance = Decimal(lines[index + 2][29].replace(",", ""))

            # The balance for express checkout are zero. thanks paypal.
            if pp_balance == Decimal(0.0):
                if (verbose):
                    print("Balance fix!")
                    print("balance: %s gross: %s" % (str(balance), str(gross)))
                pp_balance = balance + gross

            index += 2
        else:
            if gross + fee == Decimal(0.0):
                print("*** skip non balance affecting transaction: %s" % desc)
                index += 1
                continue

            print("Unknown transaction")
            print("%s %-40s %10s %10s %10s %10s" % (dat, desc, str(gross), str(fee),
                                                   str(pp_balance), str(balance)))
            assert False

        if balance is None:
            balance = pp_balance - net
            starting_balance = balance

        balance = balance + net
        if balance != pp_balance:
            print("     discrepancy: ", (pp_balance - balance))
            print("%s %-40s %10s %10s %10s %10s" % (dat, desc, str(gross), str(fee),
                                                   str(pp_balance), str(balance)))
            assert False

        desc = desc.replace(",", " ")
        out.writerow([dat, desc, gross])

        print("%s %-40s %10s %10s %10s %10s" % (dat, desc, str(gross), str(fee),
                                               str(pp_balance), str(balance)))
 
        desc = "PayPal Fee"
        dat = fields[0]
        if fee and Decimal(fee) != 0.0:
            out.writerow([dat, desc, fee])

        index += 1

    print("    Start paypal balance: ", starting_balance)
    print("    Final paypal balance: ", pp_balance)
    print("Final calculated balance: ", balance)


if len(sys.argv) not in [3,4]:
    print("Usage parse-paypal-es.py <paypal csv file> <qbo csv file>")
    sys.exit(-1)

if sys.argv[1] == "-v":
    verbose = True
    index = 2
else:
    verbose = False
    index = 1

fp = None
try:
    fp = open(sys.argv[index], "r")
except IOError:
    print("Cannot open input file %s" % sys.argv[1])
    sys.exit(0)

_out = None
try:
    _out = open(sys.argv[index + 1], "w")
except IOError:
    print("Cannot open output file %s" % sys.argv[2])
    sys.exit(0)

process_file(fp, _out, verbose)

fp.close()
_out.close()

#!/usr/bin/env python3

import sys
import re
import csv

# header

# "Date","Time","TimeZone","Name","Type","Status","Currency","Gross","Fee","Net","From Email Address","To Email Address","Transaction ID","Shipping Address","Address Status","Item Title","Item ID","Shipping and Handling Amount","Insurance Amount","Sales Tax","Option 1 Name","Option 1 Value","Option 2 Name","Option 2 Value","Reference Txn ID","Invoice Number","Custom Number","Quantity","Receipt ID","Balance","Address Line 1","Address Line 2/District/Neighborhood","Town/City","State/Province/Region/County/Territory/Prefecture/Republic","Zip/Postal Code","Country","Contact Phone Number","Subject","Note","Country Code","Balance Impact"

# conversion line
# "12/31/2017","14:50:41","PST","Mathias Kunter","General Payment","Completed","EUR","200.00","-7.75","192.25","mathiaskunter@gmail.com","paypal@metabrainz.org","3LW066840A4238521","Mathias, Kunter","Non-Confirmed","","","","","","","","","","","","","","","192.25","","","","","","","","","Magic MP3 Tagger November","","Credit"

def unicode_csv_reader(utf8_data, dialect=csv.excel, **kwargs):
    csv_reader = csv.reader(utf8_data, dialect=dialect, **kwargs)
    for row in csv_reader:
        yield [cell for cell in row]

if len(sys.argv) != 3:
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

index = 1
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

    if status != 'Completed':
        index += 1
        continue

    if typ in ["Account Hold for Open Authorization", "Reversal of General Account Hold"]:
        index += 1
        continue

    currency = fields[6]
    if currency == 'USD' and typ != "General Currency Conversion":
        # Normal native currency transactions
        amount = gross

    elif currency != 'USD':
        # Received money in foreign currency
        native = float(lines[index + 2][7].replace(",", ""))
        foreign = -float(lines[index + 1][7].replace(",", ""))

        #print "native %f, foreign %f" % (native, foreign)

        ratio = native / foreign
        #print "conversion rate: %f" % ratio

        fee = float(fee) * ratio
        fee = float(int(fee * 100)) / 100

        amount = native - fee
        #print "amount %f fee: %f" % (amount, fee)

        index += 2
    elif typ == "General Currency Conversion":
        #print lines[index]
        #print lines[index + 1]
        #print lines[index + 2]

        native = float(lines[index][7].replace(",", ""))
        foreign = -float(lines[index + 1][7].replace(",", ""))
        desc = lines[index + 2][3]

        #print "native %f, foreign %f" % (native, foreign)

        ratio = native / foreign
        #print "conversion rate: %f" % ratio

        fee = float(fee) * ratio
        fee = float(int(fee * 100)) / 100

        amount = native - fee
        #print "amount %f fee: %f" % (amount, fee)

        index += 2
        

    desc = desc.replace(",", " ")
    out.writerow([dat, desc, amount])

    desc = "PayPal Fee"
    dat = fields[0]
    if fee and float(fee) != 0.0:
        out.writerow([dat, desc, fee])

    index += 1

fp.close()
_out.close()

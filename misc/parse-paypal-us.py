#!/usr/bin/env python3
import argparse
from dataclasses import dataclass
import csv
from datetime import datetime
from decimal import Decimal, ROUND_DOWN
from typing import Dict
from icecream import ic

@dataclass
class Transaction:
    description: str
    date: datetime
    gross: Decimal
    fee: Decimal
    net: Decimal
    currency: str
    type: str
    balance: Decimal
    comment: str
    is_donation: bool
    accounted_for: bool
    line: str
    balance_impact: str
    transaction_id: str
    invoice_num: str
    reference_transaction_id: str
    subtransactions: list


def create_csv_file(out_file: str, transactions: Dict[str, Transaction]):

    balance = None
    try:
        _out = open(out_file, "w")
    except IOError:
        print("Cannot open output file %s" % sys.argv[2])
        sys.exit(0)

    out = csv.writer(_out, quoting=csv.QUOTE_MINIMAL)
    out.writerow(["Date","Description","Amount"])
    for t in transactions:

        if t.type in ("General Withdrawal", "User Initiated Withdrawal"):
            t.description = "Transfer"
        elif t.type.startswith("Bank Deposit to PP Account"):
            t.description = "Bank Deposit to PP Account"
        elif t.type == "General Card Deposit":
            t.description = "General Card Deposit"

        if t.currency != "USD":
            pp_balance = None
            for sub_t in t.subtransactions:
                if sub_t.currency == "USD" and sub_t.type == "General Currency Conversion":
                    native = sub_t.gross
                    pp_balance = sub_t.balance
                if sub_t.currency != "USD":
                    foreign = -sub_t.gross

            exchange_rate = native / foreign
            usd_fee = Decimal(t.fee * exchange_rate).quantize(Decimal('.01'), rounding=ROUND_DOWN)

#            print(f" native: {native:.2f}")
#            print(f"foreign: {foreign:.2f}")
#            print(f"eur fee: {t.fee:.2f}")
#            print(f"usd fee: {usd_fee:.2f}")
#            print(f" x-rate: {exchange_rate:.10f}")

            t.gross = native - usd_fee
            t.fee = usd_fee
#            ic(t)
#            print(f" fix bal: {pp_balance:.2f}")
            t.balance = pp_balance 
#            print()
#        else:
#            print(f"  gross: {t.gross:.2f}")
#            print(f"    fee: {t.fee:.2f}")
#            print(f"balance: {t.balance:.2f}")
#            print()

        if balance is None:
            balance = t.balance
        else:
            balance += t.gross + t.fee
            if t.balance != balance:
                print(f"    balance: {balance:.2f}")
                print(f" pp balance: {t.balance:.2f}")
                print(f"Discrepancy: {t.balance - balance:.2f}")
                ic(t)
                assert False

        print(t.date, t.balance, balance)

        assert t.gross != Decimal(0.0)
        if t.description == "":
            print(t)
            assert False
        out.writerow([t.date.strftime("%m/%d/%Y"), t.description, t.gross])
        if t.fee != Decimal(0.0):
            out.writerow([t.date.strftime("%m/%d/%Y"), "PayPal Fee", t.fee])

    print(f"Final balance: {balance:.2f}")

    _out.close()


def parse(input_file) -> Dict[str, Transaction]:

    transactions = []

    with open(input_file, "r", encoding="utf-8-sig") as f:
        csv_reader = csv.DictReader(f, dialect="excel")
        for line in csv_reader:
            if line["Option 1 Name"] == "is_donation":
                is_donation = line["Option 1 Value"] == "yes"
            elif line["Option 2 Name"] == "is_donation":
                is_donation = line["Option 2 Value"] == "yes"
            elif "donation" in line["Subject"].lower():
                is_donation = True
            else:
                is_donation = False

            transaction = Transaction(
                description=line["Name"],
                date=datetime.strptime(line["Date"] + " " + line["Time"], "%m/%d/%Y %H:%M:%S"),
                gross=Decimal(line["Gross"].replace(",", "")),
                fee=Decimal(line["Fee"].replace(",", "")),
                net=Decimal(line["Net"].replace(",", "")),
                currency=line["Currency"],
                type=line["Type"],
                balance=Decimal(line["Balance"].replace(",", "")),
                is_donation=bool(is_donation),  # is_donation
                comment="",
                accounted_for=False,
                balance_impact=line["Balance Impact"],
                transaction_id=line["Transaction ID"],
                invoice_num=line["Invoice Number"],
                reference_transaction_id=line["Reference Txn ID"],
                subtransactions=[],
                line=line
            )
            transactions.append(transaction)

    subbed = []
    for i, t in enumerate(transactions):
        if i == 0:
            subbed.append(t)
            continue

        prev = subbed[-1]

        # If the balance doesn't change, ignore it
        if t.net == Decimal(0.0):
            continue

        # If they snuck a card deposit into a transaction, process it first as a separate transaction!
        if prev.date == t.date and t.description == "" and t.type == "General Card Deposit":
            subbed.insert(len(subbed) - 1, t)
            continue

        if prev.currency != "USD" and prev.date == t.date and \
            t.description == "PayPal" and t.type == "Reversal of General Account Hold":
            subbed.insert(len(subbed) - 1, t)
            continue

        if prev.date == t.date and t.description == "":
            prev.subtransactions.append(t)
            continue

        subbed.append(t)

#    for t in subbed:
#        ic(t)

    return subbed


def main():
    parser = argparse.ArgumentParser(prog='Parse PayPal Transactions')
    parser.add_argument("--input", help="Paypal transactions/activity csv file", required=True)
    parser.add_argument("--output", help="Desired simplified report file path", required=True)

    args = parser.parse_args()
    transactions = parse(args.input)
    create_csv_file(args.output, transactions)

if __name__ == "__main__":
    main()

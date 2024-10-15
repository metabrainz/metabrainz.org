#!/usr/bin/env python3
import argparse
from dataclasses import dataclass
import csv
from datetime import datetime
from decimal import Decimal
from typing import Dict

from ofxtools.models import STMTTRN, BANKTRANLIST, STMTRS, BANKMSGSRSV1, OFX, BANKACCTFROM, LEDGERBAL, STMTTRNRS, \
    STATUS, FI, SONRS, SIGNONMSGSRSV1
from ofxtools.utils import UTC
import xml.etree.ElementTree as ET


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
    reference_transaction_id: str
    subtransactions: list


def classify_transaction(transaction: Transaction):
    if transaction.is_donation and transaction.currency == 'USD':
        return {
            'trntype': 'CREDIT',
            'trnamt': transaction.gross,
            'name': 'Donation',
            'memo': '4010 Income - Donations - PayPal'
        }
    elif transaction.is_donation and transaction.currency != 'USD':
        return {
            'trntype': 'CREDIT',
            'trnamt': transaction.gross,
            'name': None,  # Not classified
            'memo': f'PayPal donation in {transaction.currency}. Reference: {transaction.reference_transaction_id}'
        }
    elif transaction.type == 'Payment':
        return {
            'trntype': 'DEBIT',
            'trnamt': -transaction.gross,
            'name': None,  # Not classified
            'memo': f'Payment in {transaction.currency}'
        }
    elif transaction.type == 'Transfer':
        return {
            'trntype': 'XFER',
            'trnamt': -transaction.gross,
            'name': '3100 Bank - PPB Checking',
            'memo': 'Transfer to Pacific Premier'
        }
    else:  # Checkout payments, refunds, etc.
        return {
            'trntype': 'OTHER',
            'trnamt': transaction.gross,
            'name': None,  # Not classified
            'memo': f'Unclassified transaction: {transaction.type}'
        }


def create_ofx(transactions: Dict[str, Transaction]):
    statement_transactions = []
    for transaction in list(transactions.values()):
        classified = classify_transaction(transaction)

        if not classified:
            continue
        tran = STMTTRN(
            trntype=classified['trntype'],
            dtposted=transaction.date.replace(tzinfo=UTC),
            trnamt=classified['trnamt'],
            fitid=transaction.transaction_id,
            name=classified['name'],
            memo=classified['memo']
        )
        statement_transactions.append(tran)

        if transaction.fee != 0:
            fee_tran = STMTTRN(
                trntype='DEBIT',
                dtposted=transaction.date.replace(tzinfo=UTC),
                trnamt=transaction.fee,
                fitid=f"{transaction.transaction_id}_fee",
                name=f'PayPal fee for {transaction.transaction_id}',
                memo='5020 Expense - Bank - PayPal'
            )
            statement_transactions.append(fee_tran)

        for subtrans in transaction.subtransactions:
            sub_tran = STMTTRN(
                trntype='OTHER',
                dtposted=transaction.date.replace(tzinfo=UTC),
                trnamt=subtrans.gross,
                fitid=f"{transaction.transaction_id}",
                name=None,
                memo=f"Subtransaction: {subtrans.description}"
            )
            statement_transactions.append(sub_tran)

    tl = BANKTRANLIST(*statement_transactions,
                      dtstart=statement_transactions[0].dtposted,
                      dtend=statement_transactions[-1].dtposted)

    t = list(transactions.values())[0]
    stmtrs = STMTRS(
        curdef='USD',
        bankacctfrom=BANKACCTFROM(bankid='Paypal', acctid='3020', accttype='CHECKING'),
        banktranlist=tl,
        ledgerbal=LEDGERBAL(balamt=t.balance, dtasof=t.date.replace(tzinfo=UTC)),
    )
    msgsrs = BANKMSGSRSV1(STMTTRNRS(
        stmtrs=stmtrs,
        trnuid="0",
        status=STATUS(code="0", severity="INFO"))
    )
    fi = FI(org='Illuminati', fid='666')
    sonrs = SONRS(status=STATUS(code="0", severity="INFO"), dtserver = datetime(2015, 1, 2, 17, tzinfo=UTC),
                  language = 'ENG', fi = fi)
    signonmsgs = SIGNONMSGSRSV1(sonrs=sonrs)
    return OFX(signonmsgsrsv1=signonmsgs, bankmsgsrsv1=msgsrs)


def parse(input_file) -> Dict[str, Transaction]:

    transactions = {}

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
                date=datetime.strptime(line["Date"], "%m/%d/%Y"),
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
                reference_transaction_id=line["Reference Txn ID"],
                subtransactions=[],
                line=line
            )
            transactions[transaction.transaction_id] = transaction

    subtransaction_keys = []
    for transaction in transactions.values():
        if transaction.reference_transaction_id is not None and transaction.reference_transaction_id != "" \
                and transaction.reference_transaction_id in transactions:
            main_transaction = transactions[transaction.reference_transaction_id]
            main_transaction.subtransactions.append(transaction)
            subtransaction_keys.append(transaction.transaction_id)

    for subtransaction_key in subtransaction_keys:
        subtransaction = transactions[subtransaction_key]

        if subtransaction.subtransactions:
            print(subtransaction)
            for t in subtransaction.subtransactions:
                print("\t", t)
            transactions.pop(subtransaction_key)

    return transactions

    # usd_donations = []
    # usd_payments = []
    # withdrawals = []
    # usd_expenses = []
    #
    # non_usd_donations = {}
    # non_usd_expenses = {}
    # non_usd_payments = {}
    #
    # index = 0
    # while index < len(transactions):
    #     transaction = transactions[index]
    #     if transaction.type == "General Currency Conversion":
    #         if non_usd_expenses.get(transaction.reference_transaction_id):
    #             main_transaction = non_usd_expenses[transaction.reference_transaction_id]
    #         elif non_usd_payments.get(transaction.reference_transaction_id):
    #             main_transaction = non_usd_payments[transaction.reference_transaction_id]
    #         elif non_usd_donations.get(transaction.reference_transaction_id):
    #             main_transaction = non_usd_donations[transaction.reference_transaction_id]
    #         else:
    #             main_transaction = None
    #
    #         if main_transaction is not None:
    #             main_transaction.subtransactions.append(transaction)
    #             transaction.accounted_for = True
    #         else:
    #             print(transaction.line)
    #
    #         index += 1
    #     elif transaction.currency == "USD":
    #         if transaction.is_donation:
    #             usd_donations.append(transaction)
    #             transaction.accounted_for = True
    #         elif transaction.type == "General Withdrawal":
    #             withdrawals.append(transaction)
    #             transaction.accounted_for = True
    #         elif transaction.type in ["General Payment", "Subscription Payment", "Website Payment", "Reversal of General Account Hold"] and transaction.balance_impact == "Credit":
    #             usd_payments.append(transaction)
    #             transaction.accounted_for = True
    #         elif transaction.balance_impact == "Debit":
    #             usd_expenses.append(transaction)
    #             transaction.accounted_for = True
    #         else:
    #             print(transaction.line)
    #         index += 1
    #     else:
    #         if transaction.is_donation:
    #             non_usd_donations[transaction.transaction_id] = transaction
    #             transaction.accounted_for = True
    #         elif transaction.type in ["Express Checkout Payment", "General Payment"] and transaction.balance_impact == "Credit":
    #             non_usd_payments[transaction.transaction_id] = transaction
    #             transaction.accounted_for = True
    #         elif transaction.balance_impact == "Debit":
    #             non_usd_expenses[transaction.transaction_id] = transaction
    #             transaction.accounted_for = True
    #         else:
    #             print(transaction.line)
    #         index += 1
    #
    # print("all transactions", len(transactions))
    #
    # count = 0
    # for transaction in transactions:
    #     if transaction.accounted_for:
    #         count += 1
    #
    # print("accounted for", count)


def main():
    parser = argparse.ArgumentParser(prog='Parse PayPal Transactions')
    parser.add_argument("--input", help="Paypal transactions/activity csv file", required=True)
    parser.add_argument("--output", help="Desired simplified report file path", required=True)

    args = parser.parse_args()
    transactions = parse(args.input)

    ofx = create_ofx(transactions)

    root = ofx.to_etree()
    message = ET.tostring(root).decode()
    with open(args.output, 'w') as ofxfile:
        ofxfile.write('<?xml version="1.0" encoding="UTF-8" standalone="no"?><?OFX OFXHEADER="200" VERSION="220" SECURITY="NONE" OLDFILEUID="NONE" NEWFILEUID="NONE"?>')
        ofxfile.write(message)

if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""
This module contains functions for donation receipt generation and receipt
sending via email.
"""
from reportlab.platypus import SimpleDocTemplate, Spacer
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from metabrainz.mail import send_mail
from flask import current_app
import tempfile

_PRIMARY_FONT = 'Helvetica'
_PRIMARY_FONT_BOLD = 'Helvetica-Bold'


def send_receipt(email, date, amount, name, is_donation, editor_name=None):
    if is_donation:
        subject = "Receipt for your donation to the MetaBrainz Foundation"
        text = (
            "Dear %s:\n\n"
            "Thank you very much for your donation to the MetaBrainz Foundation!\n\n"
            "Your donation will allow the MetaBrainz Foundation to continue operating "
            "and improving the MusicBrainz project and its related projects. The "
            "foundation depends on donations from the community and therefore deeply "
            "appreciates your support.\n\n"
            "The MetaBrainz Foundation is a United States 501(c)(3) tax-exempt public "
            "charity. This allows US taxpayers to deduct this donation from their "
            "taxes under section 170 of the Internal Revenue Service code.\n\n"
            "Please save a printed copy of the attached PDF receipt for your records."
        ) % name
        from_addr = 'donations@' + current_app.config['MAIL_FROM_DOMAIN'],
        from_name = 'Donation Manager'
        attachment_file_name = 'metabrainz_donation'
    else:
        subject = "Receipt for your donation to the MetaBrainz Foundation"
        text = (
            "Dear %s:\n\n"
            "Thank you very much for your payment to the MetaBrainz Foundation!\n\n"
            "Your payment will allow the MetaBrainz Foundation to continue operating "
            "and improving the MusicBrainz project and its related projects. The "
            "foundation depends on these payments and therefore deeply appreciates "
            "your support.\n\n"
            "Please save a printed copy of the attached PDF receipt for your records."
        ) % name
        from_addr = 'payments@' + current_app.config['MAIL_FROM_DOMAIN'],
        from_name = 'Payment Manager'
        attachment_file_name = 'metabrainz_payment'

    send_mail(
        subject=subject,
        text=text,
        attachments=[(generate_recript(email, date, amount, name, is_donation, editor_name),
                      'pdf', '%s.pdf' % attachment_file_name)],
        recipients=[email],
        from_addr=from_addr,
        from_name=from_name,
    )


def _create_header_donation(canvas, document):
    # Adding metadata here just because that's the only place we have access to canvas :/
    canvas.setAuthor("MetaBrainz Foundation Inc.")
    canvas.setTitle("Donation Receipt")
    canvas.setKeywords("metabrainz musicbrainz donation receipt")

    canvas.setFont(_PRIMARY_FONT_BOLD, 16)
    canvas.drawRightString(550, 700, "MetaBrainz Foundation Inc.")

    canvas.setFont(_PRIMARY_FONT, 14)
    canvas.drawString(55, 700, "Donation Receipt")

    canvas.line(52, 695, 550, 695)


def _create_header_payment(canvas, document):
    # Adding metadata here just because that's the only place we have access to canvas :/
    canvas.setAuthor("MetaBrainz Foundation Inc.")
    canvas.setTitle("Payment Receipt")
    canvas.setKeywords("metabrainz musicbrainz payment receipt")

    canvas.setFont(_PRIMARY_FONT_BOLD, 16)
    canvas.drawRightString(550, 700, "MetaBrainz Foundation Inc.")

    canvas.setFont(_PRIMARY_FONT, 14)
    canvas.drawString(55, 700, "Payment Receipt")

    canvas.line(52, 695, 550, 695)


def generate_recript(email, date, amount, name, is_donation, editor_name):
    """This function generates PDF file with a receipt.

    Returns:
        Temporary file that needs to be closed after all operations on it are complete.
    """
    story = [Spacer(0, 20)]

    address_style = ParagraphStyle("address")
    address_style.fontName = _PRIMARY_FONT
    address_style.fontSize = 12
    address_style.alignment = TA_RIGHT
    if is_donation:
        email = "donations@metabrainz.org"
    else:
        email = "payments@metabrainz.org"
    address_par = Paragraph(
        "3565 South Higuera St., Suite B<br/>"
        "San Luis Obispo, CA 93401<br/><br/>"
        "%s<br/>"
        "https://metabrainz.org"
        % email,
        address_style)
    story.append(address_par)

    story.append(Spacer(0, 30))

    note_style = ParagraphStyle("note")
    note_style.fontName = _PRIMARY_FONT
    note_style.fontSize = 12
    note_style.alignment = TA_LEFT
    if is_donation:
        note_par = Paragraph(
            "%s<br/><br/><br/>"
            "Dear %s:<br/><br/>"
            "Thank you very much for your donation to the MetaBrainz Foundation!<br/><br/>"
            "Your donation will allow the MetaBrainz Foundation to continue operating "
            "and improving the MusicBrainz project and its related projects. The "
            "foundation depends on donations from the community and therefore deeply "
            "appreciates your support.<br/><br/>"
            "The MetaBrainz Foundation is a United States 501(c)(3) tax-exempt public charity. This "
            "allows US taxpayers to deduct this donation from their taxes under section 170 of the "
            "Internal Revenue Service code.<br/><br/>"
            "<b>Please save a printed copy of this receipt for your records.</b>"
            % (email, name),
            note_style)
    else:
        note_par = Paragraph(
            "%s<br/><br/><br/>"
            "Dear %s:<br/><br/>"
            "Thank you very much for your payment to the MetaBrainz Foundation!<br/><br/>"
            "Your payment will allow the MetaBrainz Foundation to continue operating "
            "and improving the MusicBrainz project and its related projects. The "
            "foundation depends on these payments and therefore deeply appreciates your "
            "support.<br/><br/>"
            "<b>Please save a printed copy of this receipt for your records.</b>"
            % (email, name),
            note_style)
    story.append(note_par)

    details_style = ParagraphStyle("details")
    details_style.fontName = _PRIMARY_FONT
    details_style.fontSize = 12
    details_style.alignment = TA_CENTER
    if is_donation:
        details_par = Paragraph(
            "<br/><br/><br/><b>"
            "Donation date: %s<br/>"
            "Donation amount: %s<br/>"
            "Donation editor: %s"
            "</b>" % (date, amount, editor_name),
            details_style)
    else:
        details_par = Paragraph(
            "<br/><br/><br/><b>"
            "Payment date: %s<br/>"
            "Amount: %s"
            "</b>" % (date, amount),
            details_style)
    story.append(details_par)

    story.append(Spacer(0, 40))

    thanks_style = ParagraphStyle("thanks")
    thanks_style.fontName = _PRIMARY_FONT_BOLD
    thanks_style.fontSize = 20
    thanks_style.alignment = TA_CENTER
    thanks_par = Paragraph("Thank you for your support!", thanks_style)
    story.append(thanks_par)

    file = tempfile.NamedTemporaryFile()
    doc = SimpleDocTemplate(file.name, pagesize=(595, 792),
                            leftMargin=52, rightMargin=44)
    if is_donation:
        doc.build(story, onFirstPage=_create_header_donation)
    else:
        doc.build(story, onFirstPage=_create_header_payment)
    return file

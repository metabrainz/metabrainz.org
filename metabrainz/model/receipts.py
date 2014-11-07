# -*- coding: utf-8 -*-
"""Receipt generation stuff."""
# TODO: Maybe move this out of models package?
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, BaseDocTemplate
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import portrait
from reportlab.platypus import Paragraph, Frame
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER


def send_receipt():
    # TODO: Implement sending
    pass


PRIMARY_FONT = 'Helvetica'
PRIMARY_FONT_BOLD = 'Helvetica-Bold'


def create_header(canvas, document):
    # Adding metadata here just because that's the only place we have access to canvas
    canvas.setAuthor("MetaBrainz Foundation Inc.")
    canvas.setTitle("Donation Receipt")
    canvas.setKeywords("metabrainz musicbrainz donation receipt")
    # TODO: Write more metadata (creation date, etc.)

    canvas.setFont(PRIMARY_FONT_BOLD, 16)
    canvas.drawRightString(550, 700, "MetaBrainz Foundation Inc.")

    canvas.setFont(PRIMARY_FONT, 14)
    canvas.drawString(55, 700, "Donation Receipt")

    canvas.line(52, 695, 550, 695)


def generate_recript(date, amount, name, editor_name, email):
    story = [Spacer(0, 70)]
    # TODO: Fix content margins

    address_style = ParagraphStyle("address")
    address_style.fontName = PRIMARY_FONT
    address_style.fontSize = 12
    address_style.alignment = TA_RIGHT
    address_par = Paragraph(
        "3565 South Higuera St., Suite B<br/>"
        "San Luis Obispo, CA 93401<br/><br/>"
        "donations@metabrainz.org<br/>"
        "http://metabrainz.org",
        address_style)
    story.append(address_par)

    note_style = ParagraphStyle("note")
    note_style.fontName = PRIMARY_FONT
    note_style.fontSize = 12
    note_style.alignment = TA_LEFT
    note_par = Paragraph(
        "%s<br/><br/><br/>"
        "Dear %s:<br/><br/>"
        "Thank you very much for your donation to the MetaBrainz Foundation!<br/><br/>"
        "Your donation will allow the MetaBrainz Foundation to continue operating and "
        "improving the MusicBrainz project (http://musicbrainz.org). MusicBrainz depends "
        "on donations from the community and therefore deeply appreciates your support.<br/><br/>"
        "The MetaBrainz Foundation is a United States 501(c)(3) tax-exempt public charity. This "
        "allows US taxpayers to deduct this donation from their taxes under section 170 of the "
        "Internal Revenue Service code.<br/><br/>"
        "<b>Please save a printed copy of this receipt for your records.</b>"
        % (email, name),
        note_style)
    story.append(note_par)

    details_style = ParagraphStyle("details")
    details_style.fontName = PRIMARY_FONT
    details_style.fontSize = 12
    details_style.alignment = TA_CENTER
    details_par = Paragraph(
        "<br/><br/><br/><b>"
        "Donation date: %s<br/>"
        "Donation amount: %s<br/>"
        "Donation editor: %s"
        "</b>" % (date, amount, editor_name),
        details_style)
    story.append(details_par)

    story.append(Spacer(0, 40))

    thanks_style = ParagraphStyle("thanks")
    thanks_style.fontName = PRIMARY_FONT_BOLD
    thanks_style.fontSize = 20
    thanks_style.alignment = TA_CENTER
    thanks_par = Paragraph("Thank you for your support!", thanks_style)
    story.append(thanks_par)

    doc = SimpleDocTemplate('test.pdf', pagesize=(595, 792))
    doc.build(story, onFirstPage=create_header)


if __name__ == "__main__":
    # TODO: Replace example with proper implementation
    generate_recript("2014/11/07", "1.00 USD", "Tester Testing", "tester", "tester@example.com")

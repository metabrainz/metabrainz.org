# -*- coding: utf-8 -*-
"""Receipt generation stuff."""
# TODO: Maybe move this out of models package?
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER


def send_receipt():
    # TODO: Implement sending
    pass


styles = getSampleStyleSheet()

PRIMARY_FONT = 'Helvetica'
PRIMARY_FONT_BOLD = 'Helvetica-Bold'


def create_header(canvas, document):
    #canvas.setPageSize((595, 842))  # A4 Size
    #canvas.setPageSize((612, 792))  # Letter size
    canvas.setPageSize((595, 792))  # Common size between Letter and A4

    # HEADER
    canvas.setFont(PRIMARY_FONT_BOLD, 16)
    canvas.drawRightString(550, 700, "MetaBrainz Foundation Inc.")

    canvas.setFont(PRIMARY_FONT, 14)
    canvas.drawString(55, 700, "Donation Receipt")

    # TODO: Make this line thinner
    canvas.line(52, 695, 550, 695)


def generate_recript(date, amount, name, editor_name, email):
    doc = SimpleDocTemplate("test.pdf")  # TODO: Fix
    # TODO: Write metadata (author, creation date, title, etc.)

    story = [Spacer(0, 70)]
    style = styles["Normal"]
    # TODO: Fix content margins
    style.fontName = PRIMARY_FONT
    style.fontSize = 12

    style.alignment = TA_RIGHT  # TODO: Fix (text below is not printed on the right side)
    address_par = Paragraph(
        "3565 South Higuera St., Suite B<br/>"
        "San Luis Obispo, CA 93401<br/><br/>"
        "donations@metabrainz.org<br/>"
        "http://metabrainz.org",
        style)
    story.append(address_par)

    style.alignment = TA_LEFT
    note_par = Paragraph(
        "%s<br/><br/><br/>"
        "Dear %s:<br/><br/>"
        "Thank you very much for your donation to the MetaBrainz Foundation!<br/><br/>"
        "Your donation will allow the MetaBrainz Foundation to continue operating and"
        "improving the MusicBrainz project (http://musicbrainz.org). MusicBrainz depends"
        "on donations from the community and therefore deeply appreciates your support.<br/><br/>"
        "The MetaBrainz Foundation is a United States 501(c)(3) tax-exempt public charity. This"
        "allows US taxpayers to deduct this donation from their taxes under section 170 of the"
        "Internal Revenue Service code.<br/><br/>"
        "<b>Please save a printed copy of this receipt for your records.</b>"
        % (email, name),
        style)
    story.append(note_par)

    style.alignment = TA_CENTER
    details_par = Paragraph(
        "<br/><br/><br/><b>"
        "Donation date: %s<br/>"
        "Donation amount: %s<br/>"
        "Donation editor: %s"
        "</b>" % (date, amount, editor_name),
        style)
    story.append(details_par)

    story.append(Spacer(0, 40))

    address_par = Paragraph("<b>Thank you for your support!</b>", style)
    story.append(address_par)

    doc.build(story, onFirstPage=create_header)

if __name__ == "__main__":
    # TODO: Replace example with proper implementation
    generate_recript("2014/09/11", "1 USD", "Tester Testing", "tester", "tester@example.com")

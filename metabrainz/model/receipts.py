"""Receipt generation stuff."""
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_RIGHT


def send_receipt():
    # TODO: Implement sending
    pass


styles = getSampleStyleSheet()

PRIMARY_FONT = 'Helvetica'
PRIMARY_FONT_BOLD = 'Helvetica-Bold'


def first_page(canvas, doc):
    canvas.saveState()

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

    # TODO: FIX
    textobject = canvas.beginText(55, 700 - 140)
    textobject.textLines("Hello!!! Thanks for donation!")
    canvas.drawText(textobject)

    # TODO: Draw the donor name and address

    # TODO: Draw the text

    # TODO: Draw donation details (date, amount, editor)

    canvas.restoreState()


def generate_recript():
    doc = SimpleDocTemplate("test.pdf")  # TODO: Fix
    story = [Spacer(1, 2 * inch)]

    # ADDRESS
    address_style = styles["Normal"]
    address_style.alignment = TA_RIGHT
    address_style.fontName = PRIMARY_FONT
    address_style.fontSize = 12
    address_style.rightIndent = 550
    #550, 700
    address_par = Paragraph(
        "3565 South Higuera St., Suite B<br/>"
        "San Luis Obispo, CA 93401<br/><br/>"
        "donations@metabrainz.org<br/>"
        "http://metabrainz.org",
        address_style)
    story.append(address_par)

    style = styles["Normal"]  # ????
    style.alignment = TA_RIGHT

    # TODO: Write metadata (author, creation date, title, etc.)
    p = Paragraph(
        "Thank you very<br/> much for your donation to the MetaBrainz Foundation!<br/><br/>"
        "Your donation will allow the MetaBrainz Foundation to continue operating and"
        "improving the MusicBrainz project (http://musicbrainz.org). MusicBrainz depends"
        "on donations from the community and therefore deeply appreciates your support.<br/><br/>"
        "The MetaBrainz Foundation is a United States 501(c)(3) tax-exempt public charity. This"
        "allows US taxpayers to deduct this donation from their taxes under section 170 of the"
        "Internal Revenue Service code.",
        style)

    story.append(p)
    story.append(Spacer(1, 0.2 * inch))

    doc.build(story, first_page)


if __name__ == "__main__":
    generate_recript()

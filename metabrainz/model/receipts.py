"""Receipt generation stuff."""
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.rl_config import defaultPageSize
from reportlab.lib.units import inch


def send_receipt():
    # TODO: Implement sending
    pass


PAGE_HEIGHT = defaultPageSize[1]
PAGE_WIDTH = defaultPageSize[0]

styles = getSampleStyleSheet()


def first_page(canvas, doc):
    canvas.saveState()
    canvas.setFont('Times-Bold', 16)
    canvas.drawCentredString(PAGE_WIDTH / 2.0, PAGE_HEIGHT - 108, "Donation Receipt")
    canvas.setFont('Times-Roman', 9)
    canvas.restoreState()


def later_pages(canvas, doc):
    canvas.saveState()
    canvas.setFont('Times-Roman', 9)
    canvas.drawString(inch, 0.75 * inch, "Page %d" % doc.page)
    canvas.restoreState()


def create():
    doc = SimpleDocTemplate("test.pdf")  # TODO: Fix
    story = [Spacer(1, 2 * inch)]
    style = styles["Normal"]  # ????

    # TODO: Write metadata (author, creation date, title, etc.)
    # TODO: Set fonts
    # TODO: Set page size

    # TODO: Draw the header

    # TODO: Draw the donor name and address

    # TODO: Draw the text

    # TODO: Draw donation details (date, amount, editor)

    p = Paragraph("Hello.", style)
    story.append(p)
    story.append(Spacer(1, 0.2 * inch))

    doc.build(story, onFirstPage=first_page, onLaterPages=later_pages)


if __name__ == "__main__":
    create()

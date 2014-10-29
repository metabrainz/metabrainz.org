from flask import Blueprint, render_template
from werkzeug.exceptions import NotFound
from jinja2.exceptions import TemplateNotFound

reports_bp = Blueprint('reports', __name__)


@reports_bp.route('/<year>')
def index(year):
    """This endpoint handles requests for pages with annual reports.
    
    If you want to create a new report just add a new HTML file into
    /metabrainz/templates/reports directory.
    """
    try:
        return render_template('reports/%s.html' % year)
    except TemplateNotFound:
        return NotFound("Requested annual report was not found.")

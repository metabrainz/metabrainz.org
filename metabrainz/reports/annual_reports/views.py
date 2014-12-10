from flask import Blueprint, render_template, redirect, url_for
from werkzeug.exceptions import NotFound
import os
import codecs

annual_reports_bp = Blueprint('annual_reports', __name__, static_folder='files')


@annual_reports_bp.route("/")
def index():
    years = list_years()
    if years:
        # Redirecting to the latest report
        return redirect(url_for('.view', year=years[-1]))
    else:
        raise NotFound('No reports created.')


@annual_reports_bp.route('/<int:year>')
def view(year):
    """This endpoint handles requests for pages with annual reports."""
    report = load_report(year)
    if report is None:
        raise NotFound('Requested annual report was not found.')
    return render_template('reports/annual_reports/view.html', year=year,
                           all_years=list_years(), report=report)


def list_years():
    # Getting list of directories with reports for each year
    dirs = os.walk(annual_reports_bp.static_folder).next()[1]
    years = map(int, dirs)
    return years


def load_report(year):
    report_location = os.path.abspath(
        os.path.join(annual_reports_bp.static_folder, str(year), 'content.html'))
    if os.path.exists(report_location):
        with codecs.open(report_location, encoding='utf8') as f:
            report = f.read()
        return report
    else:
        return None

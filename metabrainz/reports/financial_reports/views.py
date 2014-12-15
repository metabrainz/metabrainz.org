from flask import Blueprint, render_template

financial_reports_bp = Blueprint('financial_reports', __name__, static_folder='files')


@financial_reports_bp.route('/')
def index():
    return render_template('reports/financial_reports/index.html')

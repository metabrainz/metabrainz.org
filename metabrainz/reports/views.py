from flask import Blueprint, render_template

reports_bp = Blueprint('reports', __name__)


@reports_bp.route('/')
def index():
    # TODO: Create this page.
    return "Page is missing."

from flask import Blueprint, render_template

api_index_bp = Blueprint('api_index', __name__)


@api_index_bp.route('/')
def info():
    """This view provides information about using the API."""
    return render_template('api/info.html')

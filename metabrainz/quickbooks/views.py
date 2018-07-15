from flask import Blueprint, request, current_app, render_template, redirect, url_for
from metabrainz.quickbooks.quickbooks import session_manager, callback_url

quickbooks_bp = Blueprint('quickbooks', __name__)

@quickbooks_bp.route('/')
def index():
    return render_template("quickbooks/login.html")
    return render_template("quickbooks/index.html")


@quickbooks_bp.route('/login')
def login():
    return redirect(session_manager.get_authorize_url(callback_url))


@quickbooks_bp.route('/callback')
def callback():
    session_manager.get_access_tokens(request.args.get('code'))
    access_token = session_manager.access_token

    print("access token for future user: ", access_token)
    return redirect(url_for("quickbooks.index"))

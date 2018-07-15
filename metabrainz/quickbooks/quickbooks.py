from flask import request, current_app
from quickbooks import Oauth2SessionManager

session_manager = None

def init(app):
    global session_manager
        
    session_manager = Oauth2SessionManager(
        sandbox=True,
        client_id=app.config["QUICKBOOKS_CLIENT_ID"],
        client_secret=app.config["QUICKBOOKS_CLIENT_SECRET"],
        base_url=app.config["QUICKBOOKS_BASE_URL"],
    )

callback_url = 'http://localhost/quickbooks/callback'  # Quickbooks will send the response to this url

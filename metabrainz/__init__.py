from flask import Flask


def create_app():
    app = Flask(__name__)

    # Configuration
    app.config.from_object('metabrainz.config')

    if app.debug:
        # Debug toolbar
        from flask_debugtoolbar import DebugToolbarExtension
        DebugToolbarExtension(app)
        app.config['DEBUG_TB_TEMPLATE_EDITOR_ENABLED'] = True

    # Database
    from metabrainz.model import db
    db.init_app(app)

    from utils import reformat_datetime
    app.jinja_env.filters['datetime'] = reformat_datetime

    # Blueprints
    from metabrainz.views import index_bp
    from metabrainz.reports.financial_reports.views import financial_reports_bp
    from metabrainz.reports.annual_reports.views import annual_reports_bp
    from metabrainz.customers.views import customers_bp
    from metabrainz.donations.views import donations_bp
    from metabrainz.donations.paypal.views import donations_paypal_bp
    from metabrainz.donations.wepay.views import donations_wepay_bp

    app.register_blueprint(index_bp)
    app.register_blueprint(financial_reports_bp, url_prefix='/finances')
    app.register_blueprint(annual_reports_bp, url_prefix='/reports')
    app.register_blueprint(customers_bp, url_prefix='/customers')
    app.register_blueprint(donations_bp, url_prefix='/donations')
    app.register_blueprint(donations_paypal_bp, url_prefix='/donations/paypal')
    app.register_blueprint(donations_wepay_bp, url_prefix='/donations/wepay')

    # Admin section
    from flask_admin import Admin
    admin = Admin(app, name='BDFLs only!')

    from metabrainz.model.tier import TierAdminView
    from metabrainz.model.organization import OrganizationAdminView
    from metabrainz.model.donation import DonationAdminView

    admin.add_view(TierAdminView(db.session))
    admin.add_view(OrganizationAdminView(db.session))
    admin.add_view(DonationAdminView(db.session))

    return app

from flask import Flask


def create_app():
    app = Flask(__name__)

    # Configuration
    app.config.from_object('metabrainz.config')

    # Logging
    from metabrainz import loggers
    loggers.init_loggers(app)

    if app.debug:
        # Debug toolbar
        from flask_debugtoolbar import DebugToolbarExtension
        DebugToolbarExtension(app)
        app.config['DEBUG_TB_TEMPLATE_EDITOR_ENABLED'] = True

    # Database
    from metabrainz.model import db
    db.init_app(app)

    # Memcached
    if 'MEMCACHED_SERVERS' in app.config:
        from metabrainz import cache
        cache.init(app.config['MEMCACHED_SERVERS'],
                   app.config['MEMCACHED_NAMESPACE'],
                   debug=1 if app.debug else 0)

    # MusicBrainz OAuth
    from metabrainz.users import login_manager, musicbrainz_login
    login_manager.init_app(app)
    musicbrainz_login.init(app.config['MUSICBRAINZ_CLIENT_ID'],
                           app.config['MUSICBRAINZ_CLIENT_SECRET'])

    from metabrainz.utils import reformat_datetime
    app.jinja_env.filters['datetime'] = reformat_datetime

    # Error handling
    from errors import init_error_handlers
    init_error_handlers(app)

    # Blueprints
    from metabrainz.views import index_bp
    from metabrainz.reports.financial_reports.views import financial_reports_bp
    from metabrainz.reports.annual_reports.views import annual_reports_bp
    from metabrainz.users.views import users_bp
    from metabrainz.donations.views import donations_bp
    from metabrainz.donations.paypal.views import donations_paypal_bp
    from metabrainz.donations.wepay.views import donations_wepay_bp
    from metabrainz.donations.stripe.views import donations_stripe_bp
    from metabrainz.api.views import api_bp

    app.register_blueprint(index_bp)
    app.register_blueprint(financial_reports_bp, url_prefix='/finances')
    app.register_blueprint(annual_reports_bp, url_prefix='/reports')
    app.register_blueprint(users_bp, url_prefix='/users')
    app.register_blueprint(donations_bp, url_prefix='/donate')
    app.register_blueprint(donations_paypal_bp, url_prefix='/donations/paypal')
    app.register_blueprint(donations_wepay_bp, url_prefix='/donations/wepay')
    app.register_blueprint(donations_stripe_bp, url_prefix='/donations/stripe')
    app.register_blueprint(api_bp, url_prefix='/api')

    # ADMIN SECTION

    from flask_admin import Admin
    admin = Admin(app, name='BDFLs only!')

    # Models
    from metabrainz.model.tier import TierAdminView
    from metabrainz.model.user import UserAdminView
    from metabrainz.model.donation import DonationAdminView
    admin.add_view(TierAdminView(db.session, category='Database'))
    admin.add_view(UserAdminView(db.session, category='Database'))
    admin.add_view(DonationAdminView(db.session, category='Database'))

    # Custom stuff
    from metabrainz.admin.views import UsersView
    from metabrainz.admin.views import TokensView
    admin.add_view(UsersView(name='Users'))
    admin.add_view(TokensView(name='Access tokens'))

    return app

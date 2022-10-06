import os
import pprint
import sys

import stripe
from brainzutils.flask import CustomFlask
from brainzutils import sentry
from flask import send_from_directory, request
from flask_bcrypt import Bcrypt
from metabrainz.admin.quickbooks.views import QuickBooksView
from time import sleep

from metabrainz.utils import get_global_props

from metabrainz.new_oauth.authorization_grant import AuthorizationCodeGrant
from metabrainz.new_oauth.provider import authorization_server, revoke_token

from authlib.oauth2.rfc6749 import ImplicitGrant
from authlib.oauth2.rfc7636 import CodeChallenge

from metabrainz.new_oauth.authorization_grant import AuthorizationCodeGrant
from metabrainz.new_oauth.refresh_grant import RefreshTokenGrant


# Check to see if we're running under a docker deployment. If so, don't second guess
# the config file setup and just wait for the correct configuration to be generated.
deploy_env = os.environ.get('DEPLOY_ENV', '')

CONSUL_CONFIG_FILE_RETRY_COUNT = 10


bcrypt = Bcrypt()


def create_app(debug=None, config_path = None):

    app = CustomFlask(
        import_name=__name__,
        use_flask_uuid=True,
    )

    # Static files
    from metabrainz import static_manager
    static_manager.read_manifest()
    app.static_folder = '/static'
    app.context_processor(lambda: dict(
        get_static_path=static_manager.get_static_path,
        global_props=get_global_props()
    ))

    # get rid of some really pesky warning. Remove this in April 2020, when it shouldn't be needed anymore.
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True

    print("Starting metabrainz service with %s environment." % deploy_env)

    # This is used to run tests, but not for dev or deployment
    if config_path:
        print("loading %s" % config_path)
        app.config.from_pyfile(config_path)
    else:
        if not deploy_env:
            print("loading %s" % os.path.join( os.path.dirname(os.path.realpath(__file__)), '..', 'config.py'))
            app.config.from_pyfile(os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                '..', 'config.py'
            ))

    # Load configuration files: If we're running under a docker deployment, wait until 
    # the consul configuration is available.
    if deploy_env:
        consul_config = os.path.join( os.path.dirname(os.path.realpath(__file__)), 
            '..', 'consul_config.py')

        print("loading consul %s" % consul_config)
        for i in range(CONSUL_CONFIG_FILE_RETRY_COUNT):
            if not os.path.exists(consul_config):
                sleep(1)
                    
        if not os.path.exists(consul_config):
            print("No configuration file generated yet. Retried %d times, exiting." % CONSUL_CONFIG_FILE_RETRY_COUNT);
            sys.exit(-1)

        app.config.from_pyfile(consul_config, silent=True)

    if debug is not None:
        app.debug = debug

    if app.debug and app.config['SECRET_KEY']:
        app.init_debug_toolbar()

    # Printing out some debug values such as config and git commit
    try:
        with open(".git-version") as f:
            git_version = f.read()
        print('Running on git commit %s' % git_version.strip())
    except IOError:
        print("Unable to retrieve git commit. Use docker/push.sh to push images for production.")

    print('Configuration values are as follows: ')
    print(pprint.pformat(app.config, indent=4))

    sentry_config = app.config.get('LOG_SENTRY')
    if sentry_config:
        sentry.init_sentry(**sentry_config)

    # Database
    from metabrainz import db
    db.init_db_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    from metabrainz import model
    model.db.init_app(app)

    # Redis (cache)
    from brainzutils import cache
    cache.init(**app.config['REDIS'])

    # quickbooks module setup
    from metabrainz.admin.quickbooks import quickbooks
    quickbooks.init(app)

    # bcrypt setup
    bcrypt.init_app(app)

    # MusicBrainz OAuth
    from metabrainz.supporter import login_manager, musicbrainz_login
    login_manager.init_app(app)
    musicbrainz_login.init(
        app.config['MUSICBRAINZ_BASE_URL'],
        app.config['MUSICBRAINZ_CLIENT_ID'],
        app.config['MUSICBRAINZ_CLIENT_SECRET']
    )

    # Templates
    from metabrainz.utils import reformat_datetime
    app.jinja_env.filters['datetime'] = reformat_datetime
    app.jinja_env.filters['nl2br'] = lambda val: val.replace('\n', '<br />') if val else ''

    # Error handling
    from metabrainz.errors import init_error_handlers
    init_error_handlers(app)

    add_robots(app)

    from metabrainz import babel
    babel.init_app(app)

    from flask_uploads import configure_uploads
    from metabrainz.admin.forms import LOGO_UPLOAD_SET
    configure_uploads(app, upload_sets=[
        LOGO_UPLOAD_SET,
    ])

    from metabrainz.new_oauth.models import db as new_oauth_db

    @app.before_first_request
    def create_tables():
        new_oauth_db.create_all()

    config_oauth(app)

    # Blueprints
    _register_blueprints(app)

    # ADMIN SECTION

    from flask_admin import Admin
    from metabrainz.admin.views import HomeView
    admin = Admin(app, index_view=HomeView(name='Pending supporters'), template_mode='bootstrap3')

    # Models
    from metabrainz.model.supporter import SupporterAdminView
    from metabrainz.model.payment import PaymentAdminView
    from metabrainz.model.tier import TierAdminView
    from metabrainz.model.dataset import DatasetAdminView
    admin.add_view(SupporterAdminView(model.db.session, category='Supporters', endpoint="supporter_model"))
    admin.add_view(PaymentAdminView(model.db.session, category='Payments', endpoint="payment_model"))
    admin.add_view(TierAdminView(model.db.session, endpoint="tier_model"))
    admin.add_view(DatasetAdminView(model.db.session, endpoint="dataset_model"))

    # Custom stuff
    from metabrainz.admin.views import CommercialSupportersView
    from metabrainz.admin.views import SupportersView
    from metabrainz.admin.views import PaymentsView
    from metabrainz.admin.views import TokensView
    from metabrainz.admin.views import StatsView
    admin.add_view(CommercialSupportersView(name='Commercial supporters', category='Supporters'))
    admin.add_view(SupportersView(name='Search', category='Supporters'))
    admin.add_view(PaymentsView(name='All', category='Payments'))
    admin.add_view(TokensView(name='Access tokens', category='Supporters'))
    admin.add_view(StatsView(name='Statistics', category='Statistics'))
    admin.add_view(StatsView(name='Top IPs', endpoint="statsview/top-ips", category='Statistics'))
    admin.add_view(StatsView(name='Top Tokens', endpoint="statsview/top-tokens", category='Statistics'))
    admin.add_view(StatsView(name='Supporters', endpoint="statsview/supporters", category='Statistics'))

    if app.config["QUICKBOOKS_CLIENT_ID"]:
        admin.add_view(QuickBooksView(name='Invoices', endpoint="quickbooks/", category='Quickbooks'))

    stripe.api_key = app.config["STRIPE_KEYS"]["SECRET"]

    return app


def add_robots(app):
    @app.route('/robots.txt')
    def static_from_root():
        return send_from_directory(app.static_folder, request.path[1:])


def _register_blueprints(app):
    from metabrainz.views import index_bp
    from metabrainz.reports.financial_reports.views import financial_reports_bp
    from metabrainz.reports.annual_reports.views import annual_reports_bp
    from metabrainz.supporter.views import supporters_bp
    from metabrainz.user.views import users_bp
    from metabrainz.payments.views import payments_bp
    from metabrainz.payments.paypal.views import payments_paypal_bp
    from metabrainz.payments.stripe.views import payments_stripe_bp

    app.register_blueprint(index_bp)
    app.register_blueprint(financial_reports_bp, url_prefix='/finances')
    app.register_blueprint(annual_reports_bp, url_prefix='/reports')
    app.register_blueprint(supporters_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(payments_bp)

    # FIXME(roman): These URLs aren't named very correct since they receive payments
    # from organizations as well as regular donations:
    app.register_blueprint(payments_paypal_bp, url_prefix='/donations/paypal')
    app.register_blueprint(payments_stripe_bp, url_prefix='/donations/stripe')

    #############
    # OAuth / API
    #############

    from metabrainz.oauth.views import oauth_bp
    app.register_blueprint(oauth_bp, url_prefix='/oauth')
    from metabrainz.new_oauth.views import new_oauth_bp
    app.register_blueprint(new_oauth_bp, url_prefix='/new-oauth')
    from metabrainz.api.views.index import api_index_bp
    app.register_blueprint(api_index_bp, url_prefix='/api')
    from metabrainz.api.views.supporter import api_supporter_bp
    app.register_blueprint(api_supporter_bp, url_prefix='/api/supporter')
    from metabrainz.api.views.musicbrainz import api_musicbrainz_bp
    app.register_blueprint(api_musicbrainz_bp, url_prefix='/api/musicbrainz')


def config_oauth(app):
    authorization_server.init_app(app)

    authorization_server.register_grant(AuthorizationCodeGrant, [CodeChallenge(required=False)])
    authorization_server.register_grant(ImplicitGrant)
    authorization_server.register_grant(RefreshTokenGrant)
    authorization_server.register_endpoint(revoke_token)


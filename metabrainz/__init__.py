import os
import pprint
import subprocess
import sys

from brainzutils.flask import CustomFlask
from flask import send_from_directory, request
from metabrainz.utils import get_git_commit
from time import sleep

# Check to see if we're running under a docker deployment. If so, don't second guess
# the config file setup and just wait for the correct configuration to be generated.
deploy_env = os.environ.get('DEPLOY_ENV', '')

CONSUL_CONFIG_FILE_RETRY_COUNT = 10

def create_app(config_path=None):
    app = CustomFlask(
        import_name=__name__,
        use_flask_uuid=True,
        use_debug_toolbar=True,
    )

    # Now load other bits of configuration
    print("loading %s" % os.path.join( os.path.dirname(os.path.realpath(__file__)), '..', 'default_config.py'))
    app.config.from_pyfile(os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        '..', 'default_config.py'
    ))
    print("loading %s" % os.path.join( os.path.dirname(os.path.realpath(__file__)), '..', 'custom_config.py'))
    app.config.from_pyfile(os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        '..', 'custom_config.py'
    ), silent=True)

    if config_path:
        print("loading custom %s" % config_path)
        app.config.from_pyfile(config_path)

    # Load configuration files: If we're running under a docker deployment, wait until 
    # the consul configuration is available.
    if deploy_env:
        print("Running in production!");
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


    app.init_loggers(
        file_config=app.config.get('LOG_FILE'),
        email_config=app.config.get('LOG_EMAIL'),
        sentry_config=app.config.get('LOG_SENTRY'),
    )


    # Printing out some debug values such as config and git commit
    app.logger.info('Configuration values are as follows: ')
    app.logger.info(pprint.pformat(app.config, indent=4))
    try:
        app.logger.info('Running on git commit %s', get_git_commit())
    except subprocess.CalledProcessError as e:
        app.logger.info('Unable to retrieve git commit due to error: %s', str(e))


    # Database
    from metabrainz import db
    db.init_db_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    from metabrainz import model
    model.db.init_app(app)

    # Redis (cache)
    from brainzutils import cache
    cache.init(**app.config['REDIS'])

    # MusicBrainz OAuth
    from metabrainz.users import login_manager, musicbrainz_login
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

    # Blueprints
    _register_blueprints(app)

    # ADMIN SECTION

    from flask_admin import Admin
    from metabrainz.admin.views import HomeView
    admin = Admin(app, index_view=HomeView(name='Pending users'), template_mode='bootstrap3')

    # Models
    from metabrainz.model.user import UserAdminView
    from metabrainz.model.payment import PaymentAdminView
    from metabrainz.model.tier import TierAdminView
    admin.add_view(UserAdminView(model.db.session, category='Users', endpoint="user_model"))
    admin.add_view(PaymentAdminView(model.db.session, category='Payments', endpoint="payment_model"))
    admin.add_view(TierAdminView(model.db.session, endpoint="tier_model"))

    # Custom stuff
    from metabrainz.admin.views import CommercialUsersView
    from metabrainz.admin.views import UsersView
    from metabrainz.admin.views import PaymentsView
    from metabrainz.admin.views import TokensView
    from metabrainz.admin.views import StatsView
    admin.add_view(CommercialUsersView(name='Commercial users', category='Users'))
    admin.add_view(UsersView(name='Search', category='Users'))
    admin.add_view(PaymentsView(name='All', category='Payments'))
    admin.add_view(TokensView(name='Access tokens', category='Users'))
    admin.add_view(StatsView(name='Statistics'))

    return app


def add_robots(app):
    @app.route('/robots.txt')
    def static_from_root():
        return send_from_directory(app.static_folder, request.path[1:])


def _register_blueprints(app):
    from metabrainz.views import index_bp
    from metabrainz.reports.financial_reports.views import financial_reports_bp
    from metabrainz.reports.annual_reports.views import annual_reports_bp
    from metabrainz.users.views import users_bp
    from metabrainz.payments.views import payments_bp
    from metabrainz.payments.paypal.views import payments_paypal_bp
    from metabrainz.payments.stripe.views import payments_stripe_bp

    app.register_blueprint(index_bp)
    app.register_blueprint(financial_reports_bp, url_prefix='/finances')
    app.register_blueprint(annual_reports_bp, url_prefix='/reports')
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
    from metabrainz.api.views.index import api_index_bp
    app.register_blueprint(api_index_bp, url_prefix='/api')
    from metabrainz.api.views.user import api_user_bp
    app.register_blueprint(api_user_bp, url_prefix='/api/user')
    from metabrainz.api.views.musicbrainz import api_musicbrainz_bp
    app.register_blueprint(api_musicbrainz_bp, url_prefix='/api/musicbrainz')

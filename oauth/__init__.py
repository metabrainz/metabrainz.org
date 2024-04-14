import json
import logging
import os
import pprint
import sys
from time import sleep

from authlib.oauth2 import OAuth2Error
from brainzutils import sentry
from brainzutils.flask import CustomFlask
from flask import render_template, current_app

from oauth.provider import authorization_server
from metabrainz.utils import get_global_props

# Check to see if we're running under a docker deployment. If so, don"t second guess
# the config file setup and just wait for the correct configuration to be generated.
deploy_env = os.environ.get("DEPLOY_ENV", "")

CONSUL_CONFIG_FILE_RETRY_COUNT = 10


def create_app(debug=None, config_path=None):
    logging.getLogger("authlib").setLevel(logging.DEBUG)

    app = CustomFlask(
        import_name=__name__,
        use_flask_uuid=True,
    )

    # Static files
    from metabrainz import static_manager
    static_manager.read_manifest()
    app.static_folder = "/static"
    app.context_processor(lambda: dict(
        get_static_path=static_manager.get_static_path,
        global_props=get_global_props()
    ))

    print("Starting metabrainz service with %s environment." % deploy_env)

    # This is used to run tests, but not for dev or deployment
    if config_path:
        print("loading %s" % config_path)
        app.config.from_pyfile(config_path)
    else:
        if not deploy_env:
            print("loading %s" % os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "config.py"))
            app.config.from_pyfile(os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                "..", "config.py"
            ))

    app.config["OAUTH2_REFRESH_TOKEN_GENERATOR"] = True

    app.config["SERVER_BASE_URL"] = "http://localhost:8150"
    app.config["SERVER_NAME"] = "localhost:8150"
    app.config["DEBUG"] = False
    app.config["TESTING"] = False
    app.logger.setLevel(logging.INFO)

    # app.config["SERVER_BASE_URL"] = "http://127.0.0.1:5000"
    # app.config["SERVER_NAME"] = "127.0.0.1:5000"

    # Load configuration files: If we're running under a docker deployment, wait until
    # the consul configuration is available.
    if deploy_env:
        consul_config = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "consul_config.py")

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

    if app.debug and app.config["SECRET_KEY"]:
        app.init_debug_toolbar()

    # Printing out some debug values such as config and git commit
    try:
        with open(".git-version") as f:
            git_version = f.read()
        print("Running on git commit %s" % git_version.strip())
    except IOError:
        print("Unable to retrieve git commit. Use docker/push.sh to push images for production.")

    print("Configuration values are as follows: ")
    print(pprint.pformat(app.config, indent=4))

    sentry_config = app.config.get("LOG_SENTRY")
    if sentry_config:
        sentry.init_sentry(**sentry_config)

    from oauth.login import current_user
    app.context_processor(lambda: dict(current_user=current_user))

    from metabrainz import babel
    babel.init_app(app)

    from oauth import model
    model.db.init_app(app)

    # Templates
    from metabrainz.utils import reformat_datetime
    app.jinja_env.filters["datetime"] = reformat_datetime
    app.jinja_env.filters["nl2br"] = lambda val: val.replace("\n", "<br />") if val else ""

    # Error handling
    from metabrainz.errors import init_error_handlers
    init_error_handlers(app)

    @app.errorhandler(OAuth2Error)
    def oauth_error_handler(error: OAuth2Error):
        current_app.logger.info("Error: %s", error)
        return render_template("oauth/error.html", props=json.dumps({
            "error": {
                "name": error.error,
                "description": error.get_error_description()
            }
        }))

    authorization_server.init_app(app)

    from oauth.views import oauth2_bp
    app.register_blueprint(oauth2_bp, url_prefix="/oauth2")

    return app

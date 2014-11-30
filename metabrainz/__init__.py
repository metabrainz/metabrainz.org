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
    from model import db
    db.init_app(app)

    # Blueprints
    from views import index_bp
    from finances.views import finances_bp
    from reports.views import reports_bp
    from donations.views import donations_bp
    from admin.views import admin_bp

    app.register_blueprint(index_bp)
    app.register_blueprint(finances_bp, url_prefix='/finances')
    app.register_blueprint(reports_bp, url_prefix='/reports')
    app.register_blueprint(donations_bp, url_prefix='/donations')
    app.register_blueprint(admin_bp, url_prefix='/admin')

    return app

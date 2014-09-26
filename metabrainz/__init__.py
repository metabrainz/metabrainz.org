from flask import Flask


def create_app():
    app = Flask(__name__)

    # Configuration
    import default_config
    app.config.from_object(default_config)
    app.config.from_object('metabrainz.config')

    # Blueprints
    from views import index_bp
    from finances.views import finances_bp
    from reports.views import reports_bp
    from donation.views import donation_bp

    app.register_blueprint(index_bp)
    app.register_blueprint(finances_bp, url_prefix='/finances')
    app.register_blueprint(reports_bp, url_prefix='/reports')
    app.register_blueprint(donation_bp, url_prefix='/donation')

    return app

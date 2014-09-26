from flask import Flask, render_template


def create_app():
    app = Flask(__name__)

    # Configuration
    import default_config
    app.config.from_object(default_config)
    app.config.from_object('metabrainz.config')

    @app.route("/")
    def index():
        return render_template('index.html')

    return app

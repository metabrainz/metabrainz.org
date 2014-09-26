from flask import Flask


def create_app():
    app = Flask(__name__)

    @app.route("/")
    def index():
        return "Hello, world!"

    return app

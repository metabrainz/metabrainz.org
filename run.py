from werkzeug.serving import run_simple
from metabrainz import create_app

application = create_app()

if __name__ == '__main__':
    run_simple('0.0.0.0', 8080, application,
               use_reloader=True, use_debugger=True, use_evalex=True)

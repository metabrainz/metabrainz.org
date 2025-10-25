from metabrainz import create_app


app = create_app()
celery = app.extensions["celery"]

# Import tasks to ensure they're registered
# This must happen after celery app is created
import metabrainz.webhooks.tasks  # noqa: F401, E402

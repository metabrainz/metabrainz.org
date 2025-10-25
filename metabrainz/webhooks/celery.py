from celery import Celery, Task
from celery.schedules import crontab
from flask import Flask


def init_celery(app: Flask) -> Celery:
    """
    Create and configure a Celery instance integrated with Flask app context.

    Args:
        app: Flask application instance

    Returns:
        Configured Celery application
    """
    # Make celery work with flask app context
    class ContextTask(Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery = Celery(
        app.name,
        task_cls=ContextTask,
        broker=f'redis://{app.config["REDIS"]["host"]}:{app.config["REDIS"]["port"]}/0',
        backend=f'redis://{app.config["REDIS"]["host"]}:{app.config["REDIS"]["port"]}/1',
    )

    celery.conf.update(
        task_routes={
            "metabrainz.webhooks.tasks.deliver_webhook": {"queue": "webhooks"},
            "metabrainz.webhooks.tasks.retry_failed_webhooks": {"queue": "webhooks_maintenance"},
        },

        worker_prefetch_multiplier=4,
        worker_max_tasks_per_child=1000,

        task_acks_late=True,
        task_reject_on_worker_lost=True,
        task_time_limit=app.config.get("WEBHOOK_TASK_TIME_LIMIT", 120),
        task_soft_time_limit=app.config.get("WEBHOOK_TASK_SOFT_TIME_LIMIT", 90),

        task_autoretry_for=(Exception,),
        task_retry_backoff=True,
        task_retry_backoff_max=600,
        task_retry_jitter=True,

        task_ignore_result=True,

        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],

        timezone="UTC",
        enable_utc=True,

        worker_send_task_events=True,
        task_send_sent_event=True,

        task_default_rate_limit=app.config.get("WEBHOOK_DEFAULT_RATE_LIMIT", "100/m"),
    )

    celery.conf.beat_schedule.update({
        "webhook-retry-failed": {
            "task": "metabrainz.webhooks.tasks.retry_failed_webhooks",
            "schedule": 300.0,
            "options": {
                "queue": "webhooks_maintenance",
                "expires": 240.0,
            }
        },
        "webhook-cleanup-old-deliveries": {
            "task": "metabrainz.webhooks.tasks.cleanup_old_deliveries",
            "schedule": crontab(hour=2, minute=0),
            "args": (30,),
            "options": {
                "queue": "webhooks_maintenance",
            }
        },
    })

    celery.set_default()
    app.extensions["celery"] = celery

    return celery

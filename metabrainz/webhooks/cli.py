import click
from datetime import datetime, timedelta, timezone

from metabrainz import create_app
from metabrainz.model.webhook import Webhook
from metabrainz.model.webhook_delivery import WebhookDelivery
from metabrainz.webhooks.delivery import WebhookDeliveryEngine
from metabrainz.webhooks.tasks import retry_failed_webhooks, cleanup_old_deliveries


@click.group()
def webhooks():
    """Webhook management commands."""
    pass


@webhooks.command('retry')
def retry_failed():
    """Manually trigger retry of failed deliveries."""
    app = create_app()
    with app.app_context():
        click.echo("Retrying failed webhook deliveries...")
        result = retry_failed_webhooks()
        click.echo(f"  Found: {result['found']}")
        click.echo(f"  Queued: {result['queued']}")
        click.echo(f"  Errors: {result['errors']}")


@webhooks.command('cleanup')
@click.option('--days', default=30, help='Keep deliveries newer than N days (default: 30)')
@click.option('--dry-run', is_flag=True, help='Show what would be deleted without deleting')
def cleanup(days, dry_run):
    """Clean up old webhook delivery records."""
    app = create_app()
    with app.app_context():
        if dry_run:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            count = WebhookDelivery.query.filter(
                WebhookDelivery.status == "delivered",
                WebhookDelivery.created_at < cutoff_date
            ).count()
            click.echo(f"Would delete {count} deliveries older than {days} days")
        else:
            click.echo(f"Cleaning up deliveries older than {days} days...")
            result = cleanup_old_deliveries(days)
            if 'error' in result:
                click.echo(f"  Error: {result['error']}", err=True)
            else:
                click.echo(f"  Deleted: {result['deleted']} deliveries")


@webhooks.command('circuit-breaker')
@click.argument('webhook_id', type=int)
@click.option('--reset', is_flag=True, help='Reset the circuit breaker')
def circuit_breaker_cmd(webhook_id, reset):
    """Show or reset circuit breaker status for a webhook."""
    app = create_app()
    with app.app_context():
        webhook = Webhook.query.get(webhook_id)
        if not webhook:
            click.echo(f"Webhook {webhook_id} not found", err=True)
            return

        if reset:
            WebhookDeliveryEngine.reset_circuit_breaker(webhook_id)
            click.echo(f"Circuit breaker reset for webhook {webhook_id}")
        else:
            cb = WebhookDeliveryEngine.get_circuit_breaker(webhook_id)
            stats = cb.get_stats()
            click.echo(f"\nCircuit Breaker Status for Webhook {webhook_id}:")
            click.echo(f"  State: {stats['state']}")
            click.echo(f"  Failure count: {stats['failure_count']}")
            if stats["last_failure_time"]:
                click.echo(f"  Time until retry: {stats['time_until_retry']:.1f}s")

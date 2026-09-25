from datetime import datetime, timezone

import click
from flask import current_app
from functools import wraps

from metabrainz import create_app

from metabrainz.model import db, Supporter
from metabrainz.model.crm_sync import CrmSync
from metabrainz.crm.tasks import publish_signup_sync


def app_context(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        with create_app().app_context():
            return func(*args, **kwargs)
    return wrapped


@click.command("crm-sync")
@click.argument("supporter_id", type=int)
@click.option("--person-id", type=click.UUID, help="Explicitly link an existing CRM person.")
@click.option("--company-id", type=click.UUID, help="Explicitly link an existing CRM company.")
@app_context
def crm_sync(supporter_id, person_id, company_id):
    """Queue one supporter for synchronization or retry after resolving a match."""
    if not current_app.config.get("CRM_ENABLED", False):
        raise click.ClickException("CRM synchronization is disabled")
    if db.session.get(Supporter, supporter_id) is None:
        raise click.ClickException("Supporter does not exist")
    mapping = CrmSync.query.filter_by(supporter_id=supporter_id).with_for_update().first()
    if mapping is None:
        mapping = CrmSync(supporter_id=supporter_id)
        db.session.add(mapping)
    if person_id is not None:
        mapping.person_id = person_id
    if company_id is not None:
        mapping.company_id = company_id
    mapping.pending = True
    mapping.next_attempt_at = datetime.now(timezone.utc)
    mapping.last_error = None
    db.session.commit()
    publish_signup_sync(supporter_id)
    click.echo(f"Supporter {supporter_id} scheduled for CRM synchronization.")

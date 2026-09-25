from sqlalchemy import func

from metabrainz.model import db


class CrmSync(db.Model):
    """Durable signup work and explicit mappings to existing CRM records."""

    __tablename__ = "crm_sync"

    supporter_id = db.Column(db.Integer, db.ForeignKey("supporter.id", ondelete="CASCADE"), primary_key=True)
    pending = db.Column(db.Boolean, nullable=False, default=True)
    next_attempt_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())
    attempts = db.Column(db.Integer, nullable=False, default=0)
    last_error = db.Column(db.Text)
    synced_at = db.Column(db.DateTime(timezone=True))
    person_id = db.Column(db.Uuid)
    company_id = db.Column(db.Uuid)

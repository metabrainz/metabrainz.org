import hashlib
import hmac
from typing import Any

from flask import current_app
from sqlalchemy import Column, Integer, Text, Boolean, DateTime
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import func

from metabrainz.model import db
from metabrainz.model.webhook_delivery import WebhookDeliveryError, WebhookDelivery


EVENT_USER_CREATED = "user.created"
EVENT_USER_DELETED = "user.deleted"
EVENT_USER_UPDATED = "user.updated"
EVENT_USER_VERIFIED = "user.verified"


class Webhook(db.Model):
    """Webhook configuration model."""
    __tablename__ = "webhook"

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    url = Column(Text, nullable=False)
    secret = Column(Text, nullable=False)
    events = Column(ARRAY(Text), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    deliveries = relationship("WebhookDelivery", backref=backref("webhook", lazy=True), lazy=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "url": self.url,
            "events": self.events,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def sign_payload(self, payload: bytes) -> str:
        """Sign the payload using the webhook's secret."""
        return hmac.new(
            key=self.secret.encode("utf-8"),
            msg=payload,
            digestmod=hashlib.sha256
        ).hexdigest()

    def deliver(self, event_type: str, payload: dict[str, Any]) -> "WebhookDelivery":
        """
        Create and optionally queue a new webhook delivery.

        Args:
            event_type: Type of event triggering the webhook
            payload: Event payload to send

        Returns:
            WebhookDelivery instance

        Raises:
            WebhookDeliveryError: If webhook is inactive or event type not subscribed
        """
        if not self.is_active:
            raise WebhookDeliveryError(f"Webhook {self.id} is not active")

        if event_type not in self.events:
            raise WebhookDeliveryError(f"Event type {event_type} is not enabled for this webhook")

        delivery = WebhookDelivery(
            webhook_id=self.id,
            event_type=event_type,
            payload=payload,
            status="pending",
        )
        db.session.add(delivery)
        db.session.commit()

        from metabrainz.webhooks.tasks import deliver_webhook
        deliver_webhook.apply_async(
            args=[str(delivery.id)],
            queue="webhooks"
        )

        return delivery

    @classmethod
    def get_active_webhooks_for_event(cls, event_type: str) -> list["Webhook"]:
        """Get all active webhooks that are subscribed to the given event type."""
        return cls.query.filter(
            cls.is_active == True,
            cls.events.any(event_type)
        ).all()

    @classmethod
    def create_delivery_for_event(cls, event_type: str, payload: dict[str, Any]) -> list["WebhookDelivery"]:
        """Create deliveries for all webhooks subscribed to the given event type."""
        webhooks = cls.get_active_webhooks_for_event(event_type)
        deliveries = []
        
        for webhook in webhooks:
            try:
                delivery = webhook.deliver(event_type, payload)
                deliveries.append(delivery)
            except Exception as e:
                current_app.logger.error(
                    f"Failed to create delivery for webhook {webhook.id} for event {event_type}: {str(e)}",
                    exc_info=True
                )
        
        return deliveries

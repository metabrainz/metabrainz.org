import json
import random
from datetime import timezone, datetime, timedelta
from typing import Any
from uuid import uuid4

import requests
from flask import current_app
from sqlalchemy import Column, Integer, DateTime, Text, ForeignKey, Index, func, Enum
from sqlalchemy.dialects.postgresql import UUID, JSON

from metabrainz.model import db


class WebhookDeliveryError(Exception):
    """Exception raised when a webhook delivery fails."""
    pass


class WebhookDelivery(db.Model):
    """Webhook delivery attempt model."""
    __tablename__ = "webhook_delivery"

    id = Column(UUID, primary_key=True, default=uuid4)
    webhook_id = Column(Integer, ForeignKey("webhook.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(Text, nullable=False)
    payload = Column(JSON, nullable=False)
    status = Column(Enum("pending", "processing", "delivered", "failed", name="webhook_delivery_status_type"), nullable=False)
    response_status = Column(Integer)
    response_headers = Column(JSON)
    response_body = Column(Text)
    error_message = Column(Text)
    retry_count = Column(Integer, nullable=False, default=0)
    next_retry_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_webhook_delivery_status", "status"),
        Index("idx_webhook_delivery_retry", "next_retry_at", postgresql_where=status.in_(["pending", "failed"])),
    )

    def process(self, session: requests.Session):
        """Process the webhook delivery by making an HTTP request to the webhook URL."""
        if self.status not in ["pending", "failed"]:
            raise ValueError(f"Cannot process delivery in status {self.status}")

        self.status = "processing"
        self.updated_at = datetime.now(timezone.utc)
        db.session.commit()

        try:
            headers = {
                "User-Agent": "MetaBrainz-Webhooks/1.0",
                "Content-Type": "application/json; charset=utf-8",
                "X-MetaBrainz-Event": self.event_type,
                "X-MetaBrainz-Delivery": str(self.id),
                "X-MetaBrainz-Attempt": str(self.retry_count + 1),
            }

            payload_bytes = json.dumps(
                self.payload,
                ensure_ascii=False,
                separators=(",", ":")
            ).encode("utf-8")

            signature = self.webhook.sign_payload(payload_bytes)
            headers["X-MetaBrainz-Signature-256"] = f"sha256={signature}"

            timeout = current_app.config.get("WEBHOOK_DELIVERY_TIMEOUT", 30)

            response = session.post(
                self.webhook.url,
                data=payload_bytes,
                headers=headers,
                timeout=timeout,
                allow_redirects=False,
            )

            self.response_status = response.status_code
            self.response_headers = dict(response.headers)
            self.response_body = response.text[:10000]

            response.raise_for_status()
            self.status = "delivered"
        except Exception as e:
            self.status = "failed"
            self.error_message = str(e)[:1000]
            self.schedule_retry()
            raise WebhookDeliveryError(f"Failed to send webhook: {str(e)}") from e
        finally:
            self.updated_at = datetime.now(timezone.utc)
            db.session.commit()

    def schedule_retry(self):
        """Schedule a retry for this delivery if we haven't exceeded the maximum number of retries."""
        max_retries = current_app.config.get("WEBHOOK_MAX_RETRIES")
        if self.retry_count < max_retries:
            self.retry_count += 1
            self.next_retry_at = datetime.now(timezone.utc) + self._get_retry_delay()
        else:
            self.next_retry_at = None

    def _get_retry_delay(self) -> timedelta:
        """Calculate the delay before the next retry using exponential backoff with jitter."""
        # Exponential backoff with jitter: 30 s, 2 m, 8 m, 32 m, 2 h (approx)
        backoff_seconds = min(60 * 60 * 24, 30 * (2 ** ((self.retry_count - 1) * 2)))  # capped at 24h
        jitter = random.randint(0, backoff_seconds // 10)
        return timedelta(seconds=backoff_seconds + jitter)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "webhook_id": self.webhook_id,
            "event_type": self.event_type,
            "status": self.status,
            "response_status": self.response_status,
            "retry_count": self.retry_count,
            "next_retry_at": self.next_retry_at.isoformat() if self.next_retry_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

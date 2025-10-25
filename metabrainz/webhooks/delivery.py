import json
import time
from datetime import datetime, timezone
from typing import Any

import requests
from flask import current_app
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from metabrainz.model import db
from metabrainz.model.webhook_delivery import WebhookDelivery, WebhookDeliveryError
from metabrainz.webhooks.circuit_breaker import CircuitBreaker


class WebhookDeliveryEngine:
    """
    High-performance webhook delivery engine with reliability features.
    """

    _session = None
    _circuit_breakers: dict[int, CircuitBreaker] = {}

    @classmethod
    def get_session(cls) -> requests.Session:
        """
        Get or create a singleton HTTP session with connection pooling and retry logic.

        Returns:
            Configured requests.Session instance
        """
        if cls._session is None:
            cls._session = requests.Session()
            retry_strategy = Retry(
                total=0,
                status_forcelist=[],
                allowed_methods=["POST"],
            )
            adapter = HTTPAdapter(
                max_retries=retry_strategy,
                pool_connections=20,
                pool_maxsize=100,
                pool_block=False,
            )
            cls._session.mount("http://", adapter)
            cls._session.mount("https://", adapter)

        return cls._session

    @classmethod
    def get_circuit_breaker(cls, webhook_id: int) -> CircuitBreaker:
        """
        Get or create a circuit breaker for a webhook.

        Args:
            webhook_id: ID of the webhook

        Returns:
            CircuitBreaker instance for the webhook
        """
        if webhook_id not in cls._circuit_breakers:
            failure_threshold = current_app.config.get("WEBHOOK_CIRCUIT_BREAKER_THRESHOLD", 5)
            recovery_timeout = current_app.config.get("WEBHOOK_CIRCUIT_BREAKER_TIMEOUT", 300)
            cls._circuit_breakers[webhook_id] = CircuitBreaker(
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout
            )
        return cls._circuit_breakers[webhook_id]

    @classmethod
    def check_rate_limit(cls, webhook_id: int) -> bool:
        """
        Check if the webhook can be delivered based on rate limiting.

        Args:
            webhook_id: ID of the webhook

        Returns:
            True if delivery is allowed, False otherwise
        """
        # TODO: Implement Redis-based rate limiting using sliding window
        # For now, return True (no rate limiting)
        # Implementation would use Redis ZSET for sliding window counter
        return True

    @classmethod
    def deliver(cls, delivery_id: str) -> dict[str, Any]:
        """
        Execute webhook delivery with all reliability features.

        Args:
            delivery_id: UUID of the WebhookDelivery record

        Returns:
            dictionary with delivery results

        Raises:
            WebhookDeliveryError: If delivery fails
        """
        delivery = db.session.get(WebhookDelivery, {"id": delivery_id})
        if not delivery:
            raise WebhookDeliveryError(f"Delivery {delivery_id} not found")

        webhook = delivery.webhook
        if not webhook:
            raise WebhookDeliveryError(f"Webhook not found for delivery {delivery_id}")

        if not webhook.is_active:
            delivery.status = "failed"
            delivery.error_message = "Webhook is not active"
            delivery.updated_at = datetime.now(timezone.utc)
            db.session.commit()
            raise WebhookDeliveryError(f"Webhook {webhook.id} is not active")

        circuit_breaker = cls.get_circuit_breaker(webhook.id)
        if not circuit_breaker.can_execute():
            delivery.status = "failed"
            delivery.error_message = "Circuit breaker is open - webhook temporarily disabled"
            delivery.schedule_retry()
            delivery.updated_at = datetime.now(timezone.utc)
            db.session.commit()

            current_app.logger.warning(
                f"Circuit breaker open for webhook {webhook.id}, "
                f"will retry delivery {delivery_id} later"
            )
            return {
                "success": False,
                "delivery_id": str(delivery_id),
                "error": "Circuit breaker open",
                "will_retry": delivery.next_retry_at is not None
            }

        if not cls.check_rate_limit(webhook.id):
            current_app.logger.info(
                f"Rate limit exceeded for webhook {webhook.id}, "
                f"delivery {delivery_id} will be retried"
            )
            time.sleep(1)
            raise WebhookDeliveryError("Rate limit exceeded")

        start_time = time.time()

        try:
            delivery.process(cls.get_session())
            circuit_breaker.record_success()

            elapsed_time = time.time() - start_time
            current_app.logger.info(
                f"Webhook delivery {delivery_id} succeeded "
                f"(webhook_id={webhook.id}, status={delivery.response_status}, "
                f"duration={elapsed_time:.2f}s)"
            )

            return {
                "success": True,
                "delivery_id": str(delivery_id),
                "duration": elapsed_time,
            }
        except Exception as e:
            circuit_breaker.record_failure()

            elapsed_time = time.time() - start_time
            current_app.logger.error(
                f"Webhook delivery {delivery_id} failed "
                f"(webhook_id={webhook.id}, error={str(e)}, "
                f"duration={elapsed_time:.2f}s, "
                f"retry_count={delivery.retry_count}, "
                f"next_retry={delivery.next_retry_at})",
                exc_info=True
            )

            return {
                "success": False,
                "delivery_id": str(delivery_id),
                "error": str(e),
                "duration": elapsed_time,
                "will_retry": delivery.next_retry_at is not None,
                "retry_count": delivery.retry_count,
            }

    @classmethod
    def reset_circuit_breaker(cls, webhook_id: int) -> None:
        """
        Manually reset the circuit breaker for a webhook.

        Args:
            webhook_id: ID of the webhook
        """
        if webhook_id in cls._circuit_breakers:
            cls._circuit_breakers[webhook_id].reset()
            current_app.logger.info(f"Circuit breaker reset for webhook {webhook_id}")

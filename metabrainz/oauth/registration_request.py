from __future__ import annotations

from authlib.common.security import generate_token
from brainzutils import cache
from flask import current_app


REGISTRATION_REQUEST_NAMESPACE = "oauth-registration-request"


def create_registration_request(data: dict) -> tuple[str, int]:
    expires_in = current_app.config.get("OAUTH2_REGISTRATION_REQUEST_EXPIRES_IN", 300)
    request_id = "mebrq_" + generate_token(42)
    cache.set(
        request_id,
        data,
        expires_in,
        namespace=REGISTRATION_REQUEST_NAMESPACE,
    )
    return request_id, expires_in


def get_registration_request(request_id: str | None) -> dict | None:
    if not request_id:
        return None
    return cache.get(request_id, namespace=REGISTRATION_REQUEST_NAMESPACE)


def delete_registration_request(request_id: str | None) -> None:
    if request_id:
        cache.delete(request_id, namespace=REGISTRATION_REQUEST_NAMESPACE)

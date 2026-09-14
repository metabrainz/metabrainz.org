from datetime import datetime, timedelta, timezone

from brainzutils import cache
from flask import abort, current_app, jsonify, make_response, request

from metabrainz.model import db, OAuth2AccessToken

SIGNUP_RATE_LIMIT_KEY_PREFIX = "signup_ip:"
SECONDS_IN_DAY = 86400


def availability_rate_limit_policy():
    """Choose the shared availability allowance for this IP or OAuth client."""
    authorization = request.headers.get("Authorization")
    if authorization is None:
        return (
            f"ip:{request.remote_addr}",
            current_app.config.get("AVAILABILITY_RATE_LIMIT_PER_IP", 30),
        )

    parts = authorization.split()
    token = None
    if len(parts) == 2 and parts[0].lower() == "bearer":
        token = db.session.query(OAuth2AccessToken).filter_by(access_token=parts[1]).first()
    if token is None or token.is_expired() or token.is_revoked():
        abort(make_response(jsonify({"error": "invalid_token"}), 401, {
            "WWW-Authenticate": 'Bearer error="invalid_token"',
        }))
    return (
        f"client:{token.client_id}",
        current_app.config.get("AVAILABILITY_RATE_LIMIT_PER_CLIENT", 300),
    )


def get_signup_count(ip_address: str) -> int:
    """Get the current registration count for an IP."""
    key = f"{SIGNUP_RATE_LIMIT_KEY_PREFIX}{ip_address}"
    count = cache.get(key)
    return count if count else 0


def increment_signup_count() -> None:
    """Increment the registration count for the current remote addr IP."""
    ip_address = request.remote_addr
    key = f"{SIGNUP_RATE_LIMIT_KEY_PREFIX}{ip_address}"
    count = get_signup_count(ip_address)
    cache.set(key, count + 1, SECONDS_IN_DAY)


def is_rate_limited(ip_address: str, limit: int) -> bool:
    """Check if an IP has exceeded the signup rate limit."""
    return get_signup_count(ip_address) >= limit


def check_signup_rate_limit(form) -> bool:
    """Check if the current IP is rate limited for signups.

    Adds a form-level error if rate limited.

    Returns:
        True if rate limited, False otherwise
    """
    ip_address = request.remote_addr
    limit = current_app.config.get("SIGNUP_RATE_LIMIT_PER_IP", 5)

    if is_rate_limited(ip_address, limit):
        form.form_errors.append(
            "Too many registration attempts from this IP address. Please try again tomorrow."
        )
        return True

    return False


# A separate key format keeps these raw Redis counters apart from the old
# msgpack-encoded cache values. Each allowance resets at midnight UTC.
REGISTRATION_REQUEST_RATE_LIMIT_KEY_PREFIX = "registration_request_client_daily:"


def _registration_request_window(client_id):
    now = datetime.now(timezone.utc)
    key = f"{REGISTRATION_REQUEST_RATE_LIMIT_KEY_PREFIX}{client_id}:{now.date().isoformat()}"
    expires_at = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    return key, int(expires_at.timestamp())


def check_registration_request_rate_limit(client_id: int) -> bool:
    """Reject new requests after the client reaches its daily allowance."""
    limit = current_app.config.get("REGISTRATION_REQUEST_RATE_LIMIT_PER_CLIENT", 100)
    key, _ = _registration_request_window(client_id)
    return int(cache.get(key, decode=False) or 0) >= limit


def increment_registration_request_count(client_id: int) -> None:
    """Count a completed provisioning without losing concurrent increments.

    In-flight requests can take the client over its allowance; subsequent
    requests will be rejected by the limit check.
    """
    key, expires_at = _registration_request_window(client_id)
    cache.increment(key)
    cache.expireat(key, expires_at)

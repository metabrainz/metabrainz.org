"""Reusable fixed-window request limits backed by brainzutils' Redis cache."""
from datetime import datetime, timezone
from functools import wraps

from brainzutils import cache
from flask import jsonify


def rate_limit(bucket, policy, window_seconds=60):
    """Limit requests using a policy returning ``(identity, allowance)``.

    Views with the same bucket, identity and window share an allowance. The
    policy runs on each request and may abort if authentication fails. Windows
    align to Unix time; every admitted request counts, including failed views.
    Counters use atomic increments and expire at the end of their window.
    """
    if window_seconds <= 0:
        raise ValueError("Rate limit window must be positive.")

    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            identity, allowance = policy()
            now = int(datetime.now(timezone.utc).timestamp())
            window = now // window_seconds
            expires_at = (window + 1) * window_seconds
            key = f"rate_limit:{bucket}:{window_seconds}:{identity}:{window}"
            count = cache.increment(key)
            cache.expireat(key, expires_at)
            if count > allowance:
                return jsonify({"error": "rate_limit_exceeded"}), 429, {
                    "Retry-After": str(expires_at - now),
                }
            return view(*args, **kwargs)
        return wrapped
    return decorator

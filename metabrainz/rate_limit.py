"""Application policies and JSON errors around BrainzUtils rate limiting."""
from functools import wraps

from brainzutils.ratelimit import RateLimit
from flask import jsonify


def rate_limit(bucket, policy, window_seconds=60):
    """Limit requests using a policy returning ``(identity, allowance)``.

    Views with the same bucket, identity and window share an allowance. The
    policy runs on each request and may abort if authentication fails. Windows
    align to Unix time; every admitted request counts, including failed views.
    BrainzUtils manages atomic counters, window resets and cache expiration.
    """
    if window_seconds <= 0:
        raise ValueError("Rate limit window must be positive.")

    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            identity, allowance = policy()
            limit = RateLimit(
                f"{bucket}:{window_seconds}:{identity}:", allowance, window_seconds,
            )
            if limit.over_limit:
                return jsonify({"error": "rate_limit_exceeded"}), 429, {
                    "Retry-After": str(limit.seconds_before_reset),
                }
            return view(*args, **kwargs)
        return wrapped
    return decorator

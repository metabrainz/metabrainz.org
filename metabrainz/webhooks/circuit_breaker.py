import time
from uuid import uuid4


class RedisCircuitBreaker:
    """Block a webhook after too many failures within a rolling time window.

    Each webhook has its own Redis sorted set. Every failed request adds one
    member whose value is a unique ID and whose score is the failure timestamp.
    The circuit is open while the set contains ``failure_threshold`` or more
    timestamps from the last ``failure_window`` seconds. It closes
    automatically as those timestamps become too old to count.
    """

    def __init__(
        self,
        redis_client,
        key: str,
        failure_threshold: int = 5,
        failure_window: int = 300,
    ):
        self.redis_client = redis_client
        self.key = key
        self.failure_threshold = failure_threshold
        self.failure_window = failure_window

    def _recent_failures(self) -> list:
        now = time.time()
        # Scores are timestamps, so this returns only failures still inside the
        # rolling window. Older entries do not affect the circuit state.
        return self.redis_client.zrangebyscore(
            self.key,
            now - self.failure_window,
            "+inf",
            withscores=True,
        )

    def is_open(self) -> bool:
        return len(self._recent_failures()) >= self.failure_threshold

    def record_failure(self) -> None:
        now = time.time()
        # Remove expired timestamps before adding the new failure so old
        # entries do not accumulate if this key remains active for a long time.
        self.redis_client.zremrangebyscore(
            self.key,
            "-inf",
            now - self.failure_window,
        )

        # A UUID keeps simultaneous failures distinct even when they have the
        # same timestamp. Redis orders and filters them using the timestamp.
        self.redis_client.zadd(self.key, {str(uuid4()): now})

        # Remove the whole set after the final failure ages out.
        self.redis_client.expire(self.key, self.failure_window)

    def reset(self) -> None:
        self.redis_client.delete(self.key)

    def get_stats(self) -> dict:
        failures = self._recent_failures()
        failure_count = len(failures)
        is_open = failure_count >= self.failure_threshold
        last_failure_time = failures[-1][1] if failures else None
        time_until_retry = 0

        if is_open:
            # Find the failure that must leave the window for the count to fall
            # below the threshold. Later failures may keep the circuit open.
            retry_failure = failures[failure_count - self.failure_threshold]
            time_until_retry = max(
                0,
                self.failure_window - (time.time() - retry_failure[1]),
            )

        return {
            "state": "open" if is_open else "closed",
            "failure_count": failure_count,
            "last_failure_time": last_failure_time,
            "time_until_retry": time_until_retry,
        }

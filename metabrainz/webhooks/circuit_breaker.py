import time
from enum import Enum
from threading import Lock


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for webhook delivery.

    Tracks failures and automatically opens the circuit when threshold is exceeded.
    After a recovery timeout, allows test requests to check if service recovered.
    
    States:
        - CLOSED: Normal operation, requests are allowed.
        - OPEN: Failure threshold exceeded, requests are blocked.
        - HALF_OPEN: Testing if service has recovered.
    """

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 300):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of consecutive failures before opening circuit.
            recovery_timeout: Seconds to wait before attempting recovery (default 5 minutes).
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout

        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._last_failure_time = None
        self._lock = Lock()

    @property
    def state(self) -> CircuitBreakerState:
        """Get current circuit breaker state."""
        with self._lock:
            return self._state

    def can_execute(self) -> bool:
        """
        Check if a request can be executed.

        Returns:
            True if request should be allowed, False otherwise
        """
        with self._lock:
            if self._state == CircuitBreakerState.CLOSED:
                return True

            if self._state == CircuitBreakerState.OPEN:
                # Check if we should transition to half-open
                if self._should_attempt_reset():
                    self._state = CircuitBreakerState.HALF_OPEN
                    return True
                return False

            # HALF_OPEN state - allow the request
            return True

    def record_success(self) -> None:
        """Record a successful request."""
        with self._lock:
            self._failure_count = 0

            if self._state == CircuitBreakerState.HALF_OPEN:
                # Success in half-open state means we can close the circuit
                self._state = CircuitBreakerState.CLOSED

    def record_failure(self) -> None:
        """Record a failed request."""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()

            if self._state == CircuitBreakerState.HALF_OPEN:
                # Failure in half-open state means we go back to open
                self._state = CircuitBreakerState.OPEN
            elif self._failure_count >= self.failure_threshold:
                # Threshold exceeded, open the circuit
                self._state = CircuitBreakerState.OPEN

    def reset(self) -> None:
        """Manually reset the circuit breaker."""
        with self._lock:
            self._state = CircuitBreakerState.CLOSED
            self._failure_count = 0
            self._last_failure_time = None

    def _should_attempt_reset(self) -> bool:
        """
        Check if enough time has passed to attempt recovery.

        Returns:
            True if recovery should be attempted
        """
        if self._last_failure_time is None:
            return True

        elapsed = time.time() - self._last_failure_time
        return elapsed >= self.recovery_timeout

    def get_stats(self) -> dict:
        """
        Get circuit breaker statistics.

        Returns:
            Dictionary with current state and statistics
        """
        with self._lock:
            return {
                "state": self._state.value,
                "failure_count": self._failure_count,
                "last_failure_time": self._last_failure_time,
                "time_until_retry": (
                    max(0, self.recovery_timeout - (time.time() - self._last_failure_time))
                    if self._last_failure_time else 0
                )
            }

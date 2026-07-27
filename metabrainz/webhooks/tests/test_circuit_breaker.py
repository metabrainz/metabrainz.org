import time
import unittest
from threading import Thread

from metabrainz.webhooks.circuit_breaker import CircuitBreaker, CircuitBreakerState


class CircuitBreakerTestCase(unittest.TestCase):
    """Test cases for CircuitBreaker."""

    def test_initial_state(self):
        """Test that circuit breaker starts in CLOSED state."""
        cb = CircuitBreaker(failure_threshold=5, recovery_timeout=300)
        self.assertEqual(cb.state, CircuitBreakerState.CLOSED)
        self.assertTrue(cb.can_execute())

    def test_record_success_resets_failure_count(self):
        """Test that recording success resets the failure counter."""
        cb = CircuitBreaker(failure_threshold=5, recovery_timeout=300)

        cb.record_failure()
        cb.record_failure()
        self.assertEqual(cb._failure_count, 2)

        cb.record_success()
        self.assertEqual(cb._failure_count, 0)
        self.assertEqual(cb.state, CircuitBreakerState.CLOSED)

    def test_circuit_opens_after_threshold(self):
        """Test that circuit opens after exceeding failure threshold."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=300)

        cb.record_failure()
        cb.record_failure()
        self.assertEqual(cb.state, CircuitBreakerState.CLOSED)

        cb.record_failure()
        self.assertEqual(cb.state, CircuitBreakerState.OPEN)
        self.assertFalse(cb.can_execute())

    def test_circuit_half_open_after_timeout(self):
        """Test that circuit transitions to HALF_OPEN after recovery timeout."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1)  # 1 second timeout

        cb.record_failure()
        cb.record_failure()
        self.assertEqual(cb.state, CircuitBreakerState.OPEN)

        time.sleep(1.1)

        can_exec = cb.can_execute()
        self.assertTrue(can_exec)
        self.assertEqual(cb.state, CircuitBreakerState.HALF_OPEN)

        cb.record_success()
        self.assertEqual(cb.state, CircuitBreakerState.CLOSED)
        self.assertEqual(cb._failure_count, 0)

    def test_failure_in_half_open_reopens_circuit(self):
        """Test that failure in HALF_OPEN state reopens the circuit."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1)

        cb.record_failure()
        cb.record_failure()
        self.assertEqual(cb.state, CircuitBreakerState.OPEN)

        time.sleep(1.1)
        cb.can_execute()
        self.assertEqual(cb.state, CircuitBreakerState.HALF_OPEN)

        cb.record_failure()
        self.assertEqual(cb.state, CircuitBreakerState.OPEN)

    def test_manual_reset(self):
        """Test manually resetting the circuit breaker."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=300)

        cb.record_failure()
        cb.record_failure()
        self.assertEqual(cb.state, CircuitBreakerState.OPEN)

        cb.reset()

        self.assertEqual(cb.state, CircuitBreakerState.CLOSED)
        self.assertEqual(cb._failure_count, 0)
        self.assertIsNone(cb._last_failure_time)
        self.assertTrue(cb.can_execute())

    def test_thread_safety(self):
        """Test that circuit breaker is thread-safe."""
        cb = CircuitBreaker(failure_threshold=100, recovery_timeout=300)
        failure_count = 50

        def record_failures():
            for _ in range(failure_count):
                cb.record_failure()

        threads = [Thread(target=record_failures) for _ in range(5)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        self.assertEqual(cb._failure_count, 250)

    def test_half_open_allows_single_request(self):
        """Test that HALF_OPEN state allows requests."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1)

        cb.record_failure()
        cb.record_failure()

        time.sleep(1.1)
        cb.can_execute()
        self.assertEqual(cb.state, CircuitBreakerState.HALF_OPEN)

        self.assertTrue(cb.can_execute())

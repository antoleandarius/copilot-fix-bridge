"""
Retry utilities with exponential backoff and circuit breaker pattern.
"""
import time
import logging
from functools import wraps
from typing import Callable, TypeVar, Type, Tuple
from enum import Enum

logger = logging.getLogger(__name__)

T = TypeVar('T')


def retry_with_backoff(
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    retry_on: Tuple[Type[Exception], ...] = (Exception,)
):
    """
    Decorator for retrying functions with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        backoff_factor: Multiplier for delay between retries (default: 2.0)
        initial_delay: Initial delay in seconds (default: 1.0)
        max_delay: Maximum delay between retries (default: 60.0)
        retry_on: Tuple of exception types to retry on (default: all exceptions)

    Example:
        @retry_with_backoff(max_retries=3, retry_on=(requests.RequestError,))
        def make_api_call():
            return requests.get("https://api.example.com")
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            delay = initial_delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retry_on as e:
                    last_exception = e

                    if attempt == max_retries:
                        logger.error(
                            f"{func.__name__} failed after {max_retries} retries: {e}",
                            extra={
                                "extra_data": {
                                    "function": func.__name__,
                                    "attempts": max_retries + 1,
                                    "error": str(e)
                                }
                            }
                        )
                        raise

                    logger.warning(
                        f"{func.__name__} attempt {attempt + 1}/{max_retries + 1} failed: {e}. "
                        f"Retrying in {delay:.1f}s...",
                        extra={
                            "extra_data": {
                                "function": func.__name__,
                                "attempt": attempt + 1,
                                "delay": delay,
                                "error": str(e)
                            }
                        }
                    )

                    time.sleep(delay)
                    delay = min(delay * backoff_factor, max_delay)
                except Exception as e:
                    # Don't retry on unexpected exceptions
                    logger.error(f"{func.__name__} failed with unexpected error: {e}")
                    raise

            raise last_exception

        return wrapper
    return decorator


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"        # Normal operation
    OPEN = "open"            # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit breaker to prevent cascading failures.

    The circuit breaker has three states:
    - CLOSED: Normal operation, requests go through
    - OPEN: Too many failures, reject requests immediately
    - HALF_OPEN: Testing if service recovered, allow one request

    Example:
        breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)

        try:
            result = breaker.call(risky_function, arg1, arg2)
        except Exception:
            # Circuit may be open, use fallback
            result = fallback_function()
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: Type[Exception] = Exception
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: Exception type that triggers circuit breaker
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED

        logger.info(
            f"Circuit breaker initialized (threshold={failure_threshold}, "
            f"timeout={recovery_timeout}s)"
        )

    def call(self, func: Callable, *args, **kwargs) -> any:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Function to call
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function

        Returns:
            Result from function call

        Raises:
            Exception: If circuit is OPEN or function fails
        """
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker entering HALF_OPEN state")
            else:
                time_remaining = int(
                    self.recovery_timeout - (time.time() - self.last_failure_time)
                )
                raise Exception(
                    f"Circuit breaker is OPEN - service unavailable. "
                    f"Retry in {time_remaining}s"
                )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to try again"""
        if self.last_failure_time is None:
            return False
        return time.time() - self.last_failure_time >= self.recovery_timeout

    def _on_success(self):
        """Reset circuit breaker on successful call"""
        self.failure_count = 0

        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            logger.info(
                "Circuit breaker CLOSED - service recovered",
                extra={"extra_data": {"state": "closed"}}
            )

    def _on_failure(self):
        """Record failure and potentially open circuit"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        logger.warning(
            f"Circuit breaker failure #{self.failure_count}",
            extra={
                "extra_data": {
                    "failure_count": self.failure_count,
                    "threshold": self.failure_threshold,
                    "state": self.state.value
                }
            }
        )

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.error(
                f"Circuit breaker OPEN after {self.failure_count} failures - "
                f"rejecting requests for {self.recovery_timeout}s",
                extra={
                    "extra_data": {
                        "state": "open",
                        "failure_count": self.failure_count,
                        "recovery_timeout": self.recovery_timeout
                    }
                }
            )

    def reset(self):
        """Manually reset the circuit breaker"""
        logger.info("Circuit breaker manually reset")
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED

    def get_state(self) -> CircuitState:
        """Get current circuit state"""
        return self.state

    def get_status(self) -> dict:
        """Get detailed circuit breaker status"""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "last_failure_time": self.last_failure_time,
            "recovery_timeout": self.recovery_timeout
        }


# Global circuit breaker instances (can be imported and used)
agenthq_circuit_breaker = None  # Initialize in main.py with proper exception type


def init_circuit_breakers():
    """
    Initialize circuit breakers with proper exception types.
    Call this after importing exception classes.
    """
    global agenthq_circuit_breaker

    try:
        from agenthq_client import AgentHQError
        agenthq_circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60,
            expected_exception=AgentHQError
        )
        logger.info("Circuit breakers initialized")
    except ImportError:
        logger.warning("Could not initialize circuit breakers - AgentHQError not available")

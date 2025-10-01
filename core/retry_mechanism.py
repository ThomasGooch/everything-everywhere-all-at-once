"""Retry mechanism for handling transient failures"""

import asyncio
import logging
import time
from enum import Enum
from functools import wraps
from typing import Any, Callable, List, Optional, Type

logger = logging.getLogger(__name__)


class RetryStrategy(Enum):
    """Retry strategy types"""

    FIXED_DELAY = "fixed_delay"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"


class RetryError(Exception):
    """Raised when all retry attempts are exhausted"""

    def __init__(self, attempts: int, last_error: Exception):
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(f"Failed after {attempts} attempts. Last error: {last_error}")


def should_retry_http_error(status_code: int) -> bool:
    """Determine if an HTTP status code should trigger a retry

    Args:
        status_code: HTTP status code

    Returns:
        True if should retry, False otherwise
    """
    # Retry on server errors (5xx) and rate limiting (429)
    return status_code >= 500 or status_code == 429


def calculate_delay(
    attempt: int,
    strategy: RetryStrategy,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
) -> float:
    """Calculate retry delay based on strategy

    Args:
        attempt: Current attempt number (1-based)
        strategy: Retry strategy to use
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds

    Returns:
        Delay in seconds
    """
    if strategy == RetryStrategy.FIXED_DELAY:
        return min(base_delay, max_delay)
    elif strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
        # 2^attempt * base_delay with jitter
        delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
        # Add jitter (±25%)
        jitter = (
            delay * 0.25 * (2 * asyncio.get_event_loop().time() % 1 - 1)
        )  # Simple jitter
        return max(0.1, delay + jitter)
    elif strategy == RetryStrategy.LINEAR_BACKOFF:
        # attempt * base_delay
        return min(attempt * base_delay, max_delay)
    else:
        return base_delay


class RetryConfig:
    """Configuration for retry mechanism"""

    def __init__(
        self,
        max_attempts: int = 3,
        strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        retryable_exceptions: Optional[List[Type[Exception]]] = None,
        retry_condition: Optional[Callable[[Exception], bool]] = None,
    ):
        self.max_attempts = max_attempts
        self.strategy = strategy
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.retryable_exceptions = retryable_exceptions or []
        self.retry_condition = retry_condition

    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """Determine if should retry based on exception and attempt count

        Args:
            exception: Exception that occurred
            attempt: Current attempt number (1-based)

        Returns:
            True if should retry, False otherwise
        """
        if attempt >= self.max_attempts:
            return False

        # Check custom retry condition first
        if self.retry_condition:
            return self.retry_condition(exception)

        # Check if exception type is in retryable list
        if self.retryable_exceptions:
            return any(
                isinstance(exception, exc_type)
                for exc_type in self.retryable_exceptions
            )

        # Default: retry on specific exceptions
        return isinstance(exception, (asyncio.TimeoutError, ConnectionError, OSError))


def with_retry(config: RetryConfig):
    """Decorator to add retry functionality to async functions

    Args:
        config: Retry configuration

    Returns:
        Decorated function with retry capability
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(1, config.max_attempts + 1):
                try:
                    result = await func(*args, **kwargs)
                    return result

                except Exception as e:
                    last_exception = e

                    if not config.should_retry(e, attempt):
                        logger.warning(
                            f"Not retrying {func.__name__} after attempt {attempt}: {e}"
                        )
                        raise e

                    if attempt < config.max_attempts:
                        delay = calculate_delay(
                            attempt,
                            config.strategy,
                            config.base_delay,
                            config.max_delay,
                        )
                        logger.info(
                            f"Retrying {func.__name__} after {delay:.2f}s "
                            f"(attempt {attempt + 1}/{config.max_attempts}): {e}"
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"All retry attempts exhausted for {func.__name__}"
                        )
                        raise RetryError(attempt, e)

            # This should never be reached, but just in case
            if last_exception:
                raise last_exception

        return wrapper

    return decorator


async def retry_async_call(
    func: Callable, *args, config: Optional[RetryConfig] = None, **kwargs
) -> Any:
    """Retry an async function call with specified configuration

    Args:
        func: Async function to call
        *args: Positional arguments for the function
        config: Retry configuration (uses default if None)
        **kwargs: Keyword arguments for the function

    Returns:
        Result from successful function call

    Raises:
        RetryError: If all retry attempts are exhausted
    """
    if config is None:
        config = RetryConfig()

    decorated_func = with_retry(config)(func)
    return await decorated_func(*args, **kwargs)


class RateLimiter:
    """Simple rate limiter to prevent overwhelming external APIs"""

    def __init__(self, max_requests_per_second: float = 1.0):
        """Initialize rate limiter

        Args:
            max_requests_per_second: Maximum requests per second allowed
        """
        self.max_requests_per_second = max_requests_per_second
        self.min_interval = 1.0 / max_requests_per_second
        self.last_request_time = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self):
        """Acquire permission to make a request, blocking if necessary"""
        async with self._lock:
            current_time = time.time()
            time_since_last = current_time - self.last_request_time

            if time_since_last < self.min_interval:
                sleep_time = self.min_interval - time_since_last
                logger.debug(f"Rate limiting: sleeping for {sleep_time:.3f}s")
                await asyncio.sleep(sleep_time)

            self.last_request_time = time.time()


# Default retry configurations for common scenarios
DEFAULT_HTTP_RETRY = RetryConfig(
    max_attempts=3,
    strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
    base_delay=1.0,
    max_delay=30.0,
)

AGGRESSIVE_RETRY = RetryConfig(
    max_attempts=5,
    strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
    base_delay=0.5,
    max_delay=60.0,
)

GENTLE_RETRY = RetryConfig(
    max_attempts=2, strategy=RetryStrategy.FIXED_DELAY, base_delay=2.0, max_delay=10.0
)

"""Circuit breaker pattern for preventing cascading failures"""

import asyncio
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class CircuitBreakerState(Enum):
    """Circuit breaker states"""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, blocking requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""

    failure_threshold: int = 5  # Number of failures to open circuit
    recovery_timeout: float = 60.0  # Seconds before trying to recover
    expected_exception: Optional[type] = None  # Expected exception type
    success_threshold: int = 1  # Successes needed to close from half-open


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open"""

    pass


class CircuitBreaker:
    """Circuit breaker implementation to prevent cascading failures"""

    def __init__(self, name: str, config: CircuitBreakerConfig):
        """Initialize circuit breaker

        Args:
            name: Unique name for this circuit breaker
            config: Circuit breaker configuration
        """
        self.name = name
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0.0
        self._lock = asyncio.Lock()

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection

        Args:
            func: Function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function

        Returns:
            Result from function call

        Raises:
            CircuitBreakerError: When circuit is open
            Original exception: When function fails
        """
        async with self._lock:
            # Check if circuit should be opened
            if self.state == CircuitBreakerState.OPEN:
                if time.time() - self.last_failure_time < self.config.recovery_timeout:
                    logger.warning(
                        f"Circuit breaker {self.name} is OPEN, rejecting call"
                    )
                    raise CircuitBreakerError(f"Circuit breaker {self.name} is open")
                else:
                    # Try to recover
                    logger.info(
                        f"Circuit breaker {self.name} attempting recovery (HALF_OPEN)"
                    )
                    self.state = CircuitBreakerState.HALF_OPEN
                    self.success_count = 0

        # Execute the function
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            # Handle success
            await self._handle_success()
            return result

        except Exception as e:
            # Handle failure
            await self._handle_failure(e)
            raise e

    async def _handle_success(self):
        """Handle successful function execution"""
        async with self._lock:
            if self.state == CircuitBreakerState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.config.success_threshold:
                    logger.info(
                        f"Circuit breaker {self.name} recovered, closing circuit"
                    )
                    self.state = CircuitBreakerState.CLOSED
                    self.failure_count = 0
                    self.success_count = 0
            elif self.state == CircuitBreakerState.CLOSED:
                # Reset failure count on successful call
                self.failure_count = 0

    async def _handle_failure(self, exception: Exception):
        """Handle failed function execution

        Args:
            exception: Exception that occurred
        """
        # Check if this exception should count as a failure
        if self.config.expected_exception and not isinstance(
            exception, self.config.expected_exception
        ):
            # Don't count unexpected exceptions
            return

        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.state == CircuitBreakerState.HALF_OPEN:
                logger.warning(
                    f"Circuit breaker {self.name} failed during recovery, "
                    f"opening circuit"
                )
                self.state = CircuitBreakerState.OPEN
                self.success_count = 0
            elif (
                self.state == CircuitBreakerState.CLOSED
                and self.failure_count >= self.config.failure_threshold
            ):
                logger.error(
                    f"Circuit breaker {self.name} failure threshold reached, "
                    f"opening circuit"
                )
                self.state = CircuitBreakerState.OPEN

    def get_state(self) -> CircuitBreakerState:
        """Get current circuit breaker state"""
        return self.state

    def get_metrics(self) -> Dict[str, Any]:
        """Get circuit breaker metrics

        Returns:
            Dictionary with current metrics
        """
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time,
            "failure_threshold": self.config.failure_threshold,
            "recovery_timeout": self.config.recovery_timeout,
        }

    async def reset(self):
        """Manually reset circuit breaker to closed state"""
        async with self._lock:
            logger.info(f"Manually resetting circuit breaker {self.name}")
            self.state = CircuitBreakerState.CLOSED
            self.failure_count = 0
            self.success_count = 0
            self.last_failure_time = 0.0

    async def force_open(self):
        """Manually force circuit breaker to open state"""
        async with self._lock:
            logger.warning(f"Manually forcing circuit breaker {self.name} to OPEN")
            self.state = CircuitBreakerState.OPEN
            self.last_failure_time = time.time()


class CircuitBreakerManager:
    """Manages multiple circuit breakers"""

    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}

    def get_circuit_breaker(
        self, name: str, config: Optional[CircuitBreakerConfig] = None
    ) -> CircuitBreaker:
        """Get or create a circuit breaker

        Args:
            name: Circuit breaker name
            config: Configuration (uses default if None)

        Returns:
            Circuit breaker instance
        """
        if name not in self.circuit_breakers:
            if config is None:
                config = CircuitBreakerConfig()

            self.circuit_breakers[name] = CircuitBreaker(name, config)
            logger.info(f"Created new circuit breaker: {name}")

        return self.circuit_breakers[name]

    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all circuit breakers

        Returns:
            Dictionary mapping circuit breaker names to their metrics
        """
        return {
            name: breaker.get_metrics()
            for name, breaker in self.circuit_breakers.items()
        }

    async def reset_all(self):
        """Reset all circuit breakers"""
        for breaker in self.circuit_breakers.values():
            await breaker.reset()


# Global circuit breaker manager
circuit_breaker_manager = CircuitBreakerManager()


def with_circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None):
    """Decorator to add circuit breaker protection to functions

    Args:
        name: Circuit breaker name
        config: Circuit breaker configuration

    Returns:
        Decorated function with circuit breaker protection
    """

    def decorator(func: Callable):
        circuit_breaker = circuit_breaker_manager.get_circuit_breaker(name, config)

        async def wrapper(*args, **kwargs):
            return await circuit_breaker.call(func, *args, **kwargs)

        wrapper.circuit_breaker = circuit_breaker
        return wrapper

    return decorator


# Default configurations for common scenarios
DEFAULT_HTTP_CIRCUIT_BREAKER = CircuitBreakerConfig(
    failure_threshold=5, recovery_timeout=60.0, success_threshold=2
)

AGGRESSIVE_CIRCUIT_BREAKER = CircuitBreakerConfig(
    failure_threshold=3, recovery_timeout=30.0, success_threshold=1
)

GENTLE_CIRCUIT_BREAKER = CircuitBreakerConfig(
    failure_threshold=10, recovery_timeout=120.0, success_threshold=3
)

"""Unit tests for circuit breaker functionality"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerError,
    CircuitBreakerManager,
    CircuitBreakerState,
    with_circuit_breaker,
)


class TestCircuitBreaker:
    """Test circuit breaker functionality"""

    @pytest.fixture
    def circuit_breaker_config(self):
        """Test configuration for circuit breaker"""
        return CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=1.0,  # Short timeout for testing
            success_threshold=2,
        )

    @pytest.fixture
    def circuit_breaker(self, circuit_breaker_config):
        """Create circuit breaker for testing"""
        return CircuitBreaker("test_breaker", circuit_breaker_config)

    def test_circuit_breaker_initialization(self, circuit_breaker):
        """Test circuit breaker initialization"""
        assert circuit_breaker.name == "test_breaker"
        assert circuit_breaker.state == CircuitBreakerState.CLOSED
        assert circuit_breaker.failure_count == 0
        assert circuit_breaker.success_count == 0

    @pytest.mark.asyncio
    async def test_successful_function_call(self, circuit_breaker):
        """Test successful function execution through circuit breaker"""

        async def success_func():
            return "success"

        result = await circuit_breaker.call(success_func)

        assert result == "success"
        assert circuit_breaker.state == CircuitBreakerState.CLOSED
        assert circuit_breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_failures(self, circuit_breaker):
        """Test circuit breaker opens after failure threshold"""

        async def failing_func():
            raise Exception("Test failure")

        # Trigger failures up to threshold
        for i in range(circuit_breaker.config.failure_threshold):
            with pytest.raises(Exception):
                await circuit_breaker.call(failing_func)

        # Circuit should now be open
        assert circuit_breaker.state == CircuitBreakerState.OPEN
        assert circuit_breaker.failure_count == 3

    @pytest.mark.asyncio
    async def test_circuit_breaker_blocks_when_open(self, circuit_breaker):
        """Test circuit breaker blocks calls when open"""

        async def failing_func():
            raise Exception("Test failure")

        # Force circuit to open by exceeding failure threshold
        for i in range(circuit_breaker.config.failure_threshold):
            with pytest.raises(Exception):
                await circuit_breaker.call(failing_func)

        assert circuit_breaker.state == CircuitBreakerState.OPEN

        # Now circuit should block calls
        with pytest.raises(CircuitBreakerError):
            await circuit_breaker.call(failing_func)

    @pytest.mark.asyncio
    async def test_circuit_breaker_recovery_to_half_open(self, circuit_breaker):
        """Test circuit breaker transitions to half-open after timeout"""

        async def failing_func():
            raise Exception("Test failure")

        # Force circuit to open
        for i in range(circuit_breaker.config.failure_threshold):
            with pytest.raises(Exception):
                await circuit_breaker.call(failing_func)

        assert circuit_breaker.state == CircuitBreakerState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(circuit_breaker.config.recovery_timeout + 0.1)

        # Next call should transition to half-open (but still fail)
        with pytest.raises(Exception):
            await circuit_breaker.call(failing_func)

        assert (
            circuit_breaker.state == CircuitBreakerState.OPEN
        )  # Back to open due to failure

    @pytest.mark.asyncio
    async def test_circuit_breaker_closes_after_recovery(self, circuit_breaker):
        """Test circuit breaker closes after successful recovery"""

        async def failing_func():
            raise Exception("Test failure")

        async def success_func():
            return "success"

        # Force circuit to open
        for i in range(circuit_breaker.config.failure_threshold):
            with pytest.raises(Exception):
                await circuit_breaker.call(failing_func)

        assert circuit_breaker.state == CircuitBreakerState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(circuit_breaker.config.recovery_timeout + 0.1)

        # Successful calls should close the circuit
        for i in range(circuit_breaker.config.success_threshold):
            result = await circuit_breaker.call(success_func)
            assert result == "success"

        assert circuit_breaker.state == CircuitBreakerState.CLOSED
        assert circuit_breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_reset(self, circuit_breaker):
        """Test manual circuit breaker reset"""

        async def failing_func():
            raise Exception("Test failure")

        # Force circuit to open
        for i in range(circuit_breaker.config.failure_threshold):
            with pytest.raises(Exception):
                await circuit_breaker.call(failing_func)

        assert circuit_breaker.state == CircuitBreakerState.OPEN

        # Reset circuit breaker
        await circuit_breaker.reset()

        assert circuit_breaker.state == CircuitBreakerState.CLOSED
        assert circuit_breaker.failure_count == 0
        assert circuit_breaker.success_count == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_force_open(self, circuit_breaker):
        """Test manually forcing circuit breaker open"""
        assert circuit_breaker.state == CircuitBreakerState.CLOSED

        await circuit_breaker.force_open()

        assert circuit_breaker.state == CircuitBreakerState.OPEN

    def test_circuit_breaker_metrics(self, circuit_breaker):
        """Test circuit breaker metrics collection"""
        metrics = circuit_breaker.get_metrics()

        assert metrics["name"] == "test_breaker"
        assert metrics["state"] == "closed"
        assert metrics["failure_count"] == 0
        assert metrics["success_count"] == 0
        assert "failure_threshold" in metrics
        assert "recovery_timeout" in metrics

    @pytest.mark.asyncio
    async def test_circuit_breaker_with_sync_function(self, circuit_breaker):
        """Test circuit breaker with synchronous function"""

        def sync_func():
            return "sync_success"

        result = await circuit_breaker.call(sync_func)

        assert result == "sync_success"
        assert circuit_breaker.state == CircuitBreakerState.CLOSED


class TestCircuitBreakerManager:
    """Test circuit breaker manager functionality"""

    def test_circuit_breaker_manager_creation(self):
        """Test circuit breaker manager creates new breakers"""
        manager = CircuitBreakerManager()

        config = CircuitBreakerConfig(failure_threshold=5)
        breaker = manager.get_circuit_breaker("test", config)

        assert breaker.name == "test"
        assert breaker.config.failure_threshold == 5

        # Getting same breaker should return same instance
        same_breaker = manager.get_circuit_breaker("test")
        assert same_breaker is breaker

    def test_circuit_breaker_manager_metrics(self):
        """Test circuit breaker manager collects all metrics"""
        manager = CircuitBreakerManager()

        breaker1 = manager.get_circuit_breaker("test1")
        breaker2 = manager.get_circuit_breaker("test2")

        all_metrics = manager.get_all_metrics()

        assert "test1" in all_metrics
        assert "test2" in all_metrics
        assert all_metrics["test1"]["name"] == "test1"
        assert all_metrics["test2"]["name"] == "test2"

    @pytest.mark.asyncio
    async def test_circuit_breaker_manager_reset_all(self):
        """Test resetting all circuit breakers"""
        manager = CircuitBreakerManager()

        breaker1 = manager.get_circuit_breaker("test1")
        breaker2 = manager.get_circuit_breaker("test2")

        # Force both to open state
        await breaker1.force_open()
        await breaker2.force_open()

        assert breaker1.state == CircuitBreakerState.OPEN
        assert breaker2.state == CircuitBreakerState.OPEN

        # Reset all
        await manager.reset_all()

        assert breaker1.state == CircuitBreakerState.CLOSED
        assert breaker2.state == CircuitBreakerState.CLOSED


class TestCircuitBreakerDecorator:
    """Test circuit breaker decorator functionality"""

    @pytest.mark.asyncio
    async def test_circuit_breaker_decorator(self):
        """Test circuit breaker decorator functionality"""
        call_count = 0

        @with_circuit_breaker(
            "decorator_test", CircuitBreakerConfig(failure_threshold=2)
        )
        async def test_function():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise Exception(f"Failure {call_count}")
            return "success"

        # First two calls should fail and open circuit
        with pytest.raises(Exception):
            await test_function()
        with pytest.raises(Exception):
            await test_function()

        # Circuit should now be open, blocking further calls
        with pytest.raises(CircuitBreakerError):
            await test_function()

        # Verify circuit breaker was created and is accessible
        assert hasattr(test_function, "circuit_breaker")
        assert test_function.circuit_breaker.state == CircuitBreakerState.OPEN

    @pytest.mark.asyncio
    async def test_circuit_breaker_decorator_success(self):
        """Test circuit breaker decorator with successful calls"""

        @with_circuit_breaker("success_test")
        async def success_function():
            return "always_success"

        result = await success_function()
        assert result == "always_success"

        # Circuit should remain closed
        assert success_function.circuit_breaker.state == CircuitBreakerState.CLOSED

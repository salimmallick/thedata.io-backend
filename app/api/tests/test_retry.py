"""
Tests for retry utilities.
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from ..core.utils.retry import (
    RetryConfig,
    RetryState,
    with_retry,
    CircuitBreaker,
    with_circuit_breaker
)

@pytest.fixture
def retry_config():
    """Create a test retry configuration."""
    return RetryConfig(
        max_attempts=3,
        initial_delay=0.1,
        max_delay=1.0,
        exponential_base=2.0,
        jitter=False
    )

@pytest.fixture
def circuit_breaker():
    """Create a test circuit breaker."""
    return CircuitBreaker(
        failure_threshold=2,
        reset_timeout=1.0,
        half_open_timeout=0.5
    )

async def test_retry_success(retry_config):
    """Test successful retry after failures."""
    attempts = 0
    
    @with_retry(retry_config=retry_config, metric_name="test_operation")
    async def test_function():
        nonlocal attempts
        attempts += 1
        if attempts < 2:
            raise ValueError("Test error")
        return "success"
    
    result = await test_function()
    assert result == "success"
    assert attempts == 2

async def test_retry_max_attempts(retry_config):
    """Test retry exhaustion."""
    attempts = 0
    
    @with_retry(retry_config=retry_config, metric_name="test_operation")
    async def test_function():
        nonlocal attempts
        attempts += 1
        raise ValueError("Test error")
    
    with pytest.raises(ValueError):
        await test_function()
    assert attempts == retry_config.max_attempts

async def test_retry_no_retry_for_certain_errors(retry_config):
    """Test that certain errors are not retried."""
    attempts = 0
    
    @with_retry(retry_config=retry_config, metric_name="test_operation")
    async def test_function():
        nonlocal attempts
        attempts += 1
        raise TypeError("Test error")
    
    with pytest.raises(TypeError):
        await test_function()
    assert attempts == 1

async def test_circuit_breaker_success():
    """Test successful circuit breaker operation."""
    breaker = CircuitBreaker(failure_threshold=2)
    calls = 0
    
    @with_circuit_breaker(breaker)
    async def test_function():
        nonlocal calls
        calls += 1
        return "success"
    
    result = await test_function()
    assert result == "success"
    assert calls == 1
    assert breaker.state == "closed"

async def test_circuit_breaker_open():
    """Test circuit breaker opening after failures."""
    breaker = CircuitBreaker(failure_threshold=2)
    calls = 0
    
    @with_circuit_breaker(breaker)
    async def test_function():
        nonlocal calls
        calls += 1
        raise ValueError("Test error")
    
    # First call - should fail but circuit stays closed
    with pytest.raises(ValueError):
        await test_function()
    assert breaker.state == "closed"
    
    # Second call - should fail and open circuit
    with pytest.raises(ValueError):
        await test_function()
    assert breaker.state == "open"
    
    # Third call - should raise circuit breaker exception
    with pytest.raises(Exception, match="Circuit breaker is open"):
        await test_function()
    
    assert calls == 2  # Third call shouldn't increment calls

async def test_circuit_breaker_half_open():
    """Test circuit breaker transition to half-open state."""
    breaker = CircuitBreaker(
        failure_threshold=2,
        reset_timeout=0.1
    )
    
    @with_circuit_breaker(breaker)
    async def test_function():
        raise ValueError("Test error")
    
    # Fail twice to open circuit
    with pytest.raises(ValueError):
        await test_function()
    with pytest.raises(ValueError):
        await test_function()
    assert breaker.state == "open"
    
    # Wait for reset timeout
    await asyncio.sleep(0.2)
    
    # Circuit should now be half-open
    assert breaker.can_execute()
    assert breaker.state == "half-open"

async def test_circuit_breaker_recovery():
    """Test circuit breaker recovery after success in half-open state."""
    breaker = CircuitBreaker(
        failure_threshold=2,
        reset_timeout=0.1
    )
    success = False
    
    @with_circuit_breaker(breaker)
    async def test_function():
        if not success:
            raise ValueError("Test error")
        return "success"
    
    # Fail twice to open circuit
    with pytest.raises(ValueError):
        await test_function()
    with pytest.raises(ValueError):
        await test_function()
    assert breaker.state == "open"
    
    # Wait for reset timeout
    await asyncio.sleep(0.2)
    
    # Set up for success
    success = True
    
    # Should succeed and close circuit
    result = await test_function()
    assert result == "success"
    assert breaker.state == "closed"

async def test_circuit_breaker_with_fallback():
    """Test circuit breaker with fallback function."""
    breaker = CircuitBreaker(failure_threshold=2)
    
    async def fallback():
        return "fallback"
    
    @with_circuit_breaker(breaker, fallback=fallback)
    async def test_function():
        raise ValueError("Test error")
    
    # Fail twice to open circuit
    with pytest.raises(ValueError):
        await test_function()
    with pytest.raises(ValueError):
        await test_function()
    
    # Third call should use fallback
    result = await test_function()
    assert result == "fallback" 
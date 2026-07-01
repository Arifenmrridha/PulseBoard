import time
import asyncio
from functools import wraps
import logging
from typing import Callable, Any, TypeVar, cast
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger("PulseBoard.Tools")

# Type variable for the decorated function
F = TypeVar('F', bound=Callable[..., Any])

class RateLimiter:
    """
    A simple token bucket rate limiter to restrict API call frequency.
    """
    def __init__(self, rate: float, capacity: float):
        """
        rate: tokens per second
        capacity: max tokens in the bucket
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self):
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_update
            self.last_update = now
            
            # Refill tokens
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            
            if self.tokens < 1.0:
                # Wait until a token is available
                wait_time = (1.0 - self.tokens) / self.rate
                logger.info(f"Rate limit hit. Waiting {wait_time:.2f} seconds...")
                await asyncio.sleep(wait_time)
                self.tokens = 0.0
                self.last_update = time.monotonic()
            else:
                self.tokens -= 1.0


# Default rate limiter for external calls (e.g. 2 calls per second, burst capacity of 5)
default_api_limiter = RateLimiter(rate=2.0, capacity=5.0)

class TransientError(Exception):
    """
    Exception raised for transient external failures (network timeout, 429 rate limiting, etc.)
    that are suitable for retry.
    """
    pass

def retry_with_backoff(max_attempts: int = 5):
    """
    A decorator that retries a function with exponential backoff if a TransientError is raised.
    Uses tenacity behind the scenes.
    """
    def decorator(func: F) -> F:
        # Check if the function is async
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            @retry(
                stop=stop_after_attempt(max_attempts),
                wait=wait_exponential(multiplier=1.5, min=2, max=30),
                retry=retry_if_exception_type(TransientError),
                before_sleep=lambda retry_state: logger.warning(
                    f"Retrying {func.__name__} after transient error. "
                    f"Attempt {retry_state.attempt_number} of {max_attempts}."
                ),
                reraise=True
            )
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                return await func(*args, **kwargs)
            return cast(F, async_wrapper)
        else:
            @wraps(func)
            @retry(
                stop=stop_after_attempt(max_attempts),
                wait=wait_exponential(multiplier=1.5, min=2, max=30),
                retry=retry_if_exception_type(TransientError),
                before_sleep=lambda retry_state: logger.warning(
                    f"Retrying {func.__name__} after transient error. "
                    f"Attempt {retry_state.attempt_number} of {max_attempts}."
                ),
                reraise=True
            )
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                return func(*args, **kwargs)
            return cast(F, sync_wrapper)
    return decorator

def rate_limited(limiter: RateLimiter = default_api_limiter):
    """
    A decorator to enforce rate limits on asynchronous functions.
    """
    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            await limiter.acquire()
            return await func(*args, **kwargs)
        return cast(F, wrapper)
    return decorator

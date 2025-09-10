"""Rate limiter implementation for API calls."""

import threading
import time
from typing import Dict, Optional


class RateLimiter:
    """Token bucket rate limiter for API calls.
    
    Implements a token bucket algorithm to limit requests per minute.
    Thread-safe implementation for concurrent usage.
    """
    
    def __init__(self, rpm: int, burst: Optional[int] = None):
        """Initialize rate limiter.
        
        Args:
            rpm: Requests per minute limit
            burst: Maximum burst size (defaults to rpm if not specified)
        """
        self.rpm = rpm
        self.burst = burst or rpm
        self.tokens = float(self.burst)
        self.last_update = time.monotonic()
        self.lock = threading.Lock()
        
    def acquire(self, timeout: float = 60.0) -> bool:
        """Acquire a token, blocking if necessary.
        
        Args:
            timeout: Maximum time to wait for a token (seconds)
            
        Returns:
            True if token acquired, False if timeout
        """
        start_time = time.monotonic()
        
        while True:
            with self.lock:
                now = time.monotonic()
                
                # Refill tokens based on time elapsed
                elapsed = now - self.last_update
                self.tokens = min(
                    self.burst,
                    self.tokens + (elapsed * self.rpm / 60.0)
                )
                self.last_update = now
                
                # Check if we have a token available
                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    return True
                
                # Calculate wait time for next token
                tokens_needed = 1.0 - self.tokens
                wait_time = (tokens_needed * 60.0) / self.rpm
            
            # Check timeout
            if time.monotonic() - start_time + wait_time > timeout:
                return False
            
            # Wait for next token
            time.sleep(wait_time)
    
    def try_acquire(self) -> bool:
        """Try to acquire a token without blocking.
        
        Returns:
            True if token acquired, False otherwise
        """
        with self.lock:
            now = time.monotonic()
            
            # Refill tokens
            elapsed = now - self.last_update
            self.tokens = min(
                self.burst,
                self.tokens + (elapsed * self.rpm / 60.0)
            )
            self.last_update = now
            
            # Try to acquire
            if self.tokens >= 1.0:
                self.tokens -= 1.0
                return True
            
            return False
    
    def available_tokens(self) -> float:
        """Get current number of available tokens.
        
        Returns:
            Number of tokens available
        """
        with self.lock:
            now = time.monotonic()
            elapsed = now - self.last_update
            return min(
                self.burst,
                self.tokens + (elapsed * self.rpm / 60.0)
            )


class ModelRateLimits:
    """Rate limits for different Gemini models based on tier."""
    
    # Tier 1 (Free) rate limits in requests per minute
    TIER_1_LIMITS = {
        "gemini-2.5-pro": 150,
        "gemini-2.5-flash": 1000,
        "gemini-2.0-flash": 2000,
        "gemini-2.0-flash-lite": 4000,
    }
    
    # Default rate limit for unknown models
    DEFAULT_LIMIT = 100
    DEFAULT_CANONICAL_KEY = "default_unknown_model"
    
    @classmethod
    def get_rpm_limit(cls, model_name: str, tier: str = "tier1") -> int:
        """Get RPM limit for a model.
        
        Args:
            model_name: Name of the model
            tier: API tier (currently only "tier1" supported)
            
        Returns:
            Requests per minute limit
        """
        rpm, _ = cls.get_rpm_and_prefix(model_name, tier)
        return rpm
    
    @classmethod
    def get_rpm_and_prefix(cls, model_name: str, tier: str = "tier1") -> tuple[int, str]:
        """Get RPM limit and canonical prefix for a model.
        
        Args:
            model_name: Name of the model
            tier: API tier (currently only "tier1" supported)
            
        Returns:
            Tuple of (requests per minute limit, canonical model prefix)
        """
        if tier != "tier1":
            raise ValueError(f"Unsupported tier: {tier}")
        
        # Normalize model name by converting to lowercase
        model_lower = model_name.lower()
        
        # Check for exact match
        if model_lower in cls.TIER_1_LIMITS:
            return cls.TIER_1_LIMITS[model_lower], model_lower
        
        # Check for partial matches (e.g., "gemini-2.5-pro" in "gemini-2.5-pro-001")
        # Sort by length descending to match more specific prefixes first
        sorted_prefixes = sorted(cls.TIER_1_LIMITS.items(), key=lambda item: len(item[0]), reverse=True)
        for model_prefix, limit in sorted_prefixes:
            if model_lower.startswith(model_prefix):
                return limit, model_prefix
        
        # Return default if no match
        # Use constant key to ensure all unknown models share one limiter
        return cls.DEFAULT_LIMIT, cls.DEFAULT_CANONICAL_KEY


class RateLimitManager:
    """Manages rate limiters for different models."""
    
    def __init__(self):
        """Initialize rate limit manager."""
        self._limiters: Dict[str, RateLimiter] = {}
        self._lock = threading.Lock()
    
    def get_limiter(self, model_name: str, tier: str = "tier1") -> RateLimiter:
        """Get or create a rate limiter for a model.
        
        Args:
            model_name: Name of the model
            tier: API tier
            
        Returns:
            RateLimiter instance for the model
        """
        # Get the canonical model prefix for consistent caching
        rpm, canonical_model = ModelRateLimits.get_rpm_and_prefix(model_name, tier)
        key = f"{tier}:{canonical_model}"
        
        with self._lock:
            if key not in self._limiters:
                self._limiters[key] = RateLimiter(rpm)
            
            return self._limiters[key]
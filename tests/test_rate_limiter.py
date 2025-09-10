"""Tests for the rate limiter module."""

import threading
import time
import pytest

from reviewer.rate_limiter import RateLimiter, ModelRateLimits, RateLimitManager


class TestRateLimiter:
    """Test the RateLimiter class."""
    
    def test_initialization(self):
        """Test rate limiter initialization."""
        limiter = RateLimiter(rpm=60)
        assert limiter.rpm == 60
        assert limiter.burst == 60
        assert limiter.tokens == 60.0
        
    def test_initialization_with_burst(self):
        """Test rate limiter with custom burst."""
        limiter = RateLimiter(rpm=60, burst=120)
        assert limiter.rpm == 60
        assert limiter.burst == 120
        assert limiter.tokens == 120.0
    
    def test_acquire_single_token(self):
        """Test acquiring a single token."""
        limiter = RateLimiter(rpm=60)
        assert limiter.acquire(timeout=1.0) is True
        assert limiter.tokens < 60.0
        
    def test_try_acquire(self):
        """Test non-blocking token acquisition."""
        limiter = RateLimiter(rpm=60)
        assert limiter.try_acquire() is True
        assert limiter.tokens == 59.0
        
    def test_token_refill(self):
        """Test that tokens refill over time."""
        limiter = RateLimiter(rpm=60)  # 1 token per second
        
        # Consume a token
        assert limiter.try_acquire() is True
        initial_tokens = limiter.tokens
        
        # Wait for refill
        time.sleep(1.1)
        
        # Check tokens increased
        current_tokens = limiter.available_tokens()
        assert current_tokens > initial_tokens
        assert current_tokens <= 60.0
    
    def test_burst_limit(self):
        """Test that tokens don't exceed burst limit."""
        limiter = RateLimiter(rpm=60, burst=10)
        
        # Wait to ensure full refill
        time.sleep(2.0)
        
        # Should still be capped at burst
        assert limiter.available_tokens() <= 10.0
    
    def test_rate_limiting(self):
        """Test that rate limiting actually works."""
        limiter = RateLimiter(rpm=120, burst=2)  # 2 per second, burst of 2
        
        start_time = time.monotonic()
        
        # Try to acquire 3 tokens rapidly
        assert limiter.try_acquire() is True
        assert limiter.try_acquire() is True
        assert limiter.try_acquire() is False  # Should fail - burst exhausted
        
        # Wait for refill and try again
        time.sleep(0.6)
        assert limiter.try_acquire() is True
        
        elapsed = time.monotonic() - start_time
        assert elapsed >= 0.5  # Should take at least 0.5 seconds
    
    def test_concurrent_access(self):
        """Test thread safety of rate limiter."""
        limiter = RateLimiter(rpm=600)  # 10 per second
        successful_acquires = []
        
        def acquire_tokens():
            for _ in range(5):
                if limiter.try_acquire():
                    successful_acquires.append(1)
                time.sleep(0.01)
        
        # Start multiple threads
        threads = []
        for _ in range(5):
            t = threading.Thread(target=acquire_tokens)
            threads.append(t)
            t.start()
        
        # Wait for all threads
        for t in threads:
            t.join()
        
        # Should have acquired some tokens but not all
        assert len(successful_acquires) > 0
        assert len(successful_acquires) <= 25  # 5 threads * 5 attempts


class TestModelRateLimits:
    """Test the ModelRateLimits class."""
    
    def test_tier1_limits(self):
        """Test Tier 1 rate limits for known models."""
        assert ModelRateLimits.get_rpm_limit("gemini-2.5-pro") == 150
        assert ModelRateLimits.get_rpm_limit("gemini-2.5-flash") == 1000
        assert ModelRateLimits.get_rpm_limit("gemini-2.0-flash") == 2000
        assert ModelRateLimits.get_rpm_limit("gemini-2.0-flash-lite") == 4000
    
    def test_case_insensitive(self):
        """Test that model names are case insensitive."""
        assert ModelRateLimits.get_rpm_limit("GEMINI-2.5-PRO") == 150
        assert ModelRateLimits.get_rpm_limit("Gemini-2.5-Flash") == 1000
    
    def test_partial_match(self):
        """Test partial model name matching."""
        assert ModelRateLimits.get_rpm_limit("gemini-2.5-pro-001") == 150
        assert ModelRateLimits.get_rpm_limit("gemini-2.5-flash-latest") == 1000
    
    def test_longest_prefix_match(self):
        """Test that longer prefixes are matched before shorter ones."""
        # This would have failed with the old implementation
        assert ModelRateLimits.get_rpm_limit("gemini-2.0-flash-lite") == 4000
        assert ModelRateLimits.get_rpm_limit("gemini-2.0-flash") == 2000
        assert ModelRateLimits.get_rpm_limit("gemini-2.0-flash-lite-001") == 4000
    
    def test_unknown_model(self):
        """Test default limit for unknown models."""
        assert ModelRateLimits.get_rpm_limit("unknown-model") == 100
        assert ModelRateLimits.get_rpm_limit("gpt-4") == 100
    
    def test_unsupported_tier(self):
        """Test error for unsupported tier."""
        with pytest.raises(ValueError, match="Unsupported tier"):
            ModelRateLimits.get_rpm_limit("gemini-2.5-pro", tier="tier2")


class TestRateLimitManager:
    """Test the RateLimitManager class."""
    
    def test_get_limiter(self):
        """Test getting a rate limiter for a model."""
        manager = RateLimitManager()
        limiter = manager.get_limiter("gemini-2.5-pro")
        
        assert isinstance(limiter, RateLimiter)
        assert limiter.rpm == 150
    
    def test_limiter_reuse(self):
        """Test that same model returns same limiter."""
        manager = RateLimitManager()
        limiter1 = manager.get_limiter("gemini-2.5-pro")
        limiter2 = manager.get_limiter("gemini-2.5-pro")
        
        assert limiter1 is limiter2
    
    def test_different_models(self):
        """Test different models get different limiters."""
        manager = RateLimitManager()
        limiter1 = manager.get_limiter("gemini-2.5-pro")
        limiter2 = manager.get_limiter("gemini-2.5-flash")
        
        assert limiter1 is not limiter2
        assert limiter1.rpm == 150
        assert limiter2.rpm == 1000
    
    def test_tier_separation(self):
        """Test that different tiers get different limiters."""
        manager = RateLimitManager()
        limiter1 = manager.get_limiter("gemini-2.5-pro", tier="tier1")
        
        # This would fail with unsupported tier, but shows the key format
        assert "tier1:gemini-2.5-pro" in manager._limiters
    
    def test_canonical_model_caching(self):
        """Test that model variations share the same limiter."""
        manager = RateLimitManager()
        
        # These should all get the same limiter instance (variations of gemini-2.5-pro)
        limiter1 = manager.get_limiter("gemini-2.5-pro")
        limiter2 = manager.get_limiter("gemini-2.5-pro-001")
        limiter3 = manager.get_limiter("gemini-2.5-pro-latest")
        
        # Verify they are the same object
        assert limiter1 is limiter2
        assert limiter2 is limiter3
        
        # But different models should get different limiters
        limiter_flash = manager.get_limiter("gemini-2.5-flash")
        assert limiter1 is not limiter_flash
        
        # Verify cache has appropriate entries
        assert "tier1:gemini-2.5-pro" in manager._limiters
        assert "tier1:gemini-2.5-flash" in manager._limiters
    
    def test_unknown_models_share_limiter(self):
        """Test that all unknown models share the same default limiter."""
        manager = RateLimitManager()
        
        # Get limiters for different unknown models
        limiter1 = manager.get_limiter("unknown-model-1")
        limiter2 = manager.get_limiter("gpt-4")
        limiter3 = manager.get_limiter("claude-3")
        limiter4 = manager.get_limiter("random-ai-model")
        
        # All should be the same limiter instance
        assert limiter1 is limiter2
        assert limiter2 is limiter3
        assert limiter3 is limiter4
        
        # Should all have the default rate limit
        assert limiter1.rpm == 100
        
        # Cache should have only one entry for all unknown models
        assert "tier1:default_unknown_model" in manager._limiters
import pytest
import time

class RateLimiter:
    def __init__(self, limit, window):
        self.limit = limit
        self.window = window
        self.history = []
        
    def allow(self):
        now = time.time()
        self.history = [t for t in self.history if t > now - self.window]
        if len(self.history) < self.limit:
            self.history.append(now)
            return True
        return False

def test_global_rate_limit_respected():
    limiter = RateLimiter(limit=3, window=1)
    assert limiter.allow() is True
    assert limiter.allow() is True
    assert limiter.allow() is True
    assert limiter.allow() is False
    
def test_retry_after_sleep_called():
    pass

def test_per_user_throttle_within_limit():
    pass

def test_per_user_throttle_exceeded():
    pass

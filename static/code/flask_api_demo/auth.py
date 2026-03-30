"""
Authentication utilities for Flask API Demo.
"""
import hashlib
import hmac
import time
from typing import Optional


class TokenManager:
    """Manages simple HMAC-based token creation and validation."""

    def __init__(self, secret_key: str):
        self.secret_key = secret_key.encode()

    def create_token(self, payload: str = "authenticated") -> str:
        """Create a new token for the given payload."""
        return hmac.new(self.secret_key, payload.encode(), hashlib.sha256).hexdigest()

    def validate_token(self, token: str, payload: str = "authenticated") -> bool:
        """Validate a token against the expected payload."""
        expected = self.create_token(payload)
        return hmac.compare_digest(token, expected)


class UserStore:
    """Simple in-memory user store with hashed passwords."""

    def __init__(self):
        self._users: dict = {}

    def add_user(self, username: str, password: str) -> None:
        """Add a user with a hashed password."""
        self._users[username] = hashlib.sha256(password.encode()).hexdigest()

    def authenticate(self, username: str, password: str) -> bool:
        """Return True if the credentials are valid."""
        if username not in self._users:
            return False
        hashed = hashlib.sha256(password.encode()).hexdigest()
        return hmac.compare_digest(self._users[username], hashed)

    def exists(self, username: str) -> bool:
        return username in self._users


class RateLimiter:
    """Simple in-memory sliding window rate limiter."""

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._buckets: dict = {}

    def is_allowed(self, key: str) -> bool:
        """Check if the key is within rate limit. Returns False if exceeded."""
        now = time.time()
        window_start = now - self.window_seconds

        if key not in self._buckets:
            self._buckets[key] = []

        # Prune old entries
        self._buckets[key] = [t for t in self._buckets[key] if t > window_start]

        if len(self._buckets[key]) >= self.max_requests:
            return False

        self._buckets[key].append(now)
        return True

    def reset(self, key: Optional[str] = None) -> None:
        """Reset limits for a specific key or all keys."""
        if key:
            self._buckets.pop(key, None)
        else:
            self._buckets.clear()

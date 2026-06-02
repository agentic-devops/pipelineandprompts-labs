# rate_limiter.py — in-memory token bucket
# NOTE: Single-replica only. Replace with Redis-backed implementation
# before scaling horizontally.
import time
from collections import defaultdict
from threading import Lock


class RateLimiter:
    def __init__(self, calls_per_minute: int = 60):
        self.calls_per_minute = calls_per_minute
        self.window = 60  # seconds
        self.calls: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def is_allowed(self, session_id: str) -> bool:
        now = time.time()
        with self._lock:
            self.calls[session_id] = [
                t for t in self.calls[session_id]
                if now - t < self.window
            ]
            if len(self.calls[session_id]) >= self.calls_per_minute:
                return False
            self.calls[session_id].append(now)
            return True

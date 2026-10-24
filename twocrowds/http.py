"""A small JSON GET helper with retries, a request budget per minute and the SQLite cache."""

from __future__ import annotations

import json
import threading
import time
from typing import Any

import httpx

from .store import Store


class RateLimiter:
    def __init__(self, per_minute: int):
        self.interval = 60.0 / max(1, per_minute)
        self.lock = threading.Lock()
        self.next_at = 0.0

    def wait(self) -> None:
        with self.lock:
            now = time.monotonic()
            delay = max(0.0, self.next_at - now)
            self.next_at = max(now, self.next_at) + self.interval
        if delay:
            time.sleep(delay)


class HttpError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(f"HTTP {status}: {message}")
        self.status = status


class JsonClient:
    def __init__(self, base_url: str, store: Store, headers: dict[str, str] | None = None, per_minute: int = 120):
        self.base_url = base_url.rstrip("/")
        self.store = store
        self.client = httpx.Client(timeout=30.0, headers=headers or {})
        self.limiter = RateLimiter(per_minute)

    def get(self, path: str, params: dict[str, Any] | None = None, *, max_age: float | None = 600) -> Any:
        params = {k: v for k, v in (params or {}).items() if v is not None}
        key = f"{self.base_url}{path}?{json.dumps(params, sort_keys=True)}"
        cached = self.store.cache_get(key, max_age)
        if cached is not None:
            return cached
        last: Exception | None = None
        for attempt in range(4):
            self.limiter.wait()
            try:
                res = self.client.get(self.base_url + path, params=params)
            except httpx.HTTPError as err:
                last = err
                time.sleep(1.5 * (attempt + 1))
                continue
            if res.status_code in (429, 500, 502, 503, 504):
                last = HttpError(res.status_code, res.text[:200])
                time.sleep(float(res.headers.get("retry-after", 2 * (attempt + 1))))
                continue
            if res.status_code >= 400:
                raise HttpError(res.status_code, res.text[:300])
            body = res.json()
            self.store.cache_put(key, body)
            return body
        raise last or HttpError(0, "request failed")

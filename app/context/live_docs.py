from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Dict, Optional
from urllib.request import urlopen


@dataclass
class CacheEntry:
    value: str
    expires_at: float


class MemoryCache:
    def __init__(self, ttl_seconds: int = 900) -> None:
        self.ttl_seconds = ttl_seconds
        self._entries: Dict[str, CacheEntry] = {}

    def get(self, key: str) -> Optional[str]:
        entry = self._entries.get(key)
        if not entry:
            return None
        if entry.expires_at < time.time():
            self._entries.pop(key, None)
            return None
        return entry.value

    def set(self, key: str, value: str) -> None:
        self._entries[key] = CacheEntry(
            value=value, expires_at=time.time() + self.ttl_seconds
        )


@dataclass(frozen=True)
class LiveDocSource:
    name: str
    url: str


class LiveDocsClient:
    def __init__(
        self,
        sources: Optional[Dict[str, LiveDocSource]] = None,
        cache: Optional[MemoryCache] = None,
        fetcher: Optional[Callable[[str], str]] = None,
        ttl_seconds: int = 900,
    ) -> None:
        self.sources = sources or {
            "status": LiveDocSource("status", "https://example.com/status"),
            "changelog": LiveDocSource("changelog", "https://example.com/changelog"),
            "known-issues": LiveDocSource(
                "known-issues", "https://example.com/known-issues"
            ),
        }
        self.cache = cache or MemoryCache(ttl_seconds=ttl_seconds)
        self.fetcher = fetcher or self._default_fetch

    def _default_fetch(self, url: str) -> str:
        try:
            with urlopen(url, timeout=10) as response:
                return response.read().decode("utf-8", errors="replace")
        except Exception:
            return ""

    def fetch(self, source_name: str) -> str:
        source = self.sources[source_name]
        cached = self.cache.get(source.url)
        if cached is not None:
            return cached
        value = self.fetcher(source.url)
        self.cache.set(source.url, value)
        return value

    def build_context(
        self, source_names: Optional[list[str]] = None, max_chars: int = 4000
    ) -> str:
        source_names = source_names or list(self.sources)
        parts = []
        for name in source_names:
            fetched = self.fetch(name).strip()
            if fetched:
                parts.append(f"[{name.upper()}]\n{fetched[:max_chars]}")
        return "\n\n".join(parts).strip()

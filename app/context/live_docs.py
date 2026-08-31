from __future__ import annotations  # allow forward-referenced type hints on older Python

import time  # wall-clock timestamps for cache expiry
from dataclasses import dataclass  # lightweight cache-entry / source containers
from typing import Callable, Dict, Optional  # type hints for pluggable fetchers
from urllib.request import urlopen  # stdlib HTTP fetch (no extra dependency for the default fetcher)


@dataclass
class CacheEntry:
    """One cached fetch result plus the time it expires."""

    value: str
    expires_at: float


class MemoryCache:
    """Simple process-local TTL cache keyed by URL (stand-in for a shared cache in production)."""

    def __init__(self, ttl_seconds: int = 900) -> None:
        self.ttl_seconds = ttl_seconds
        self._entries: Dict[str, CacheEntry] = {}

    def get(self, key: str) -> Optional[str]:
        """Return the cached value, or None if missing/expired (expired entries are evicted)."""
        entry = self._entries.get(key)
        if not entry:
            return None
        if entry.expires_at < time.time():
            self._entries.pop(key, None)
            return None
        return entry.value

    def set(self, key: str, value: str) -> None:
        """Cache `value` under `key`, expiring `ttl_seconds` from now."""
        self._entries[key] = CacheEntry(
            value=value, expires_at=time.time() + self.ttl_seconds
        )


@dataclass(frozen=True)
class LiveDocSource:
    """One live-docs source: a human-readable name and the URL to fetch."""

    name: str
    url: str


class LiveDocsClient:
    """Fetches and caches "what's true right now" context (status page, changelog, known issues)
    so a ticket about a feature that shipped last week isn't triaged against a stale model.

    Blueprint specifies Firecrawl for clean LLM-ready markdown; this scaffold uses a plain
    `urlopen`-based fetcher by default (swap `fetcher` for a Firecrawl-backed callable in
    production — the cache and context-building logic below stay the same either way).
    """

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
        """Best-effort raw HTTP fetch; any failure degrades to an empty string rather than raising,
        so a dead/unreachable docs source never blocks classification (see FAILURE_MODES.md)."""
        try:
            with urlopen(url, timeout=10) as response:
                return response.read().decode("utf-8", errors="replace")
        except Exception:
            return ""

    def fetch(self, source_name: str) -> str:
        """Fetch one named source, serving from cache when the TTL hasn't expired."""
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
        """Fetch every requested source (default: all configured sources), truncate each to
        `max_chars`, and join them into one `[SOURCE]`-tagged block for the classifier prompt."""
        source_names = source_names or list(self.sources)
        parts = []
        for name in source_names:
            fetched = self.fetch(name).strip()
            if fetched:  # skip sources that failed to fetch or came back empty
                parts.append(f"[{name.upper()}]\n{fetched[:max_chars]}")
        return "\n\n".join(parts).strip()

from __future__ import annotations  # allow forward-referenced type hints on older Python

import os  # read configuration from process environment variables
from dataclasses import dataclass  # immutable, typed settings container


def _env_float(name: str, default: float) -> float:
    """Read an environment variable as a float, falling back to `default` when unset/blank."""
    value = os.getenv(name)
    return default if value in (None, "") else float(value)


def _env_int(name: str, default: int) -> int:
    """Read an environment variable as an int, falling back to `default` when unset/blank."""
    value = os.getenv(name)
    return default if value in (None, "") else int(value)


@dataclass(frozen=True)
class Settings:
    """Runtime configuration for the triage pipeline (mirrors `.env.example`)."""

    threshold: float = 0.72  # confidence cutoff: at/above this, auto-route; below, human review
    sample_count: int = 5  # k: how many self-consistency samples to draw per ticket
    live_docs_ttl_seconds: int = 900  # cache TTL for Firecrawl-style live-docs fetches
    human_queue_name: str = "human-queue"  # route name used when a ticket is sent to a human
    default_route: str = "human-queue"  # fallback route for an (urgency, intent) pair missing from ROUTING
    model_name: str = "keyword-self-consistency"  # label recorded on results for the active backend
    use_live_context: bool = True  # whether to fetch/inject live docs context before classifying
    corrections_path: str = "data/corrections.jsonl"  # append-only log of human corrections on disk

    def __post_init__(self) -> None:
        # Fail fast on nonsensical configuration rather than letting it silently misbehave at runtime.
        if not 0.0 <= self.threshold <= 1.0:
            raise ValueError("threshold must be between 0 and 1")
        if self.sample_count < 1:
            raise ValueError("sample_count must be at least 1")
        if self.live_docs_ttl_seconds < 0:
            raise ValueError("live_docs_ttl_seconds cannot be negative")


def load_settings() -> Settings:
    """Build a `Settings` instance from environment variables (see `.env.example`)."""
    return Settings(
        threshold=_env_float("TRIAGEPILOT_THRESHOLD", 0.72),
        sample_count=_env_int("TRIAGEPILOT_SAMPLE_COUNT", 5),
        live_docs_ttl_seconds=_env_int("TRIAGEPILOT_LIVE_DOCS_TTL", 900),
        human_queue_name=os.getenv("TRIAGEPILOT_HUMAN_QUEUE", "human-queue"),
        default_route=os.getenv("TRIAGEPILOT_DEFAULT_ROUTE", "human-queue"),
        model_name=os.getenv("TRIAGEPILOT_MODEL_NAME", "keyword-self-consistency"),
        use_live_context=os.getenv("TRIAGEPILOT_USE_LIVE_CONTEXT", "1") != "0",
        corrections_path=os.getenv("TRIAGEPILOT_CORRECTIONS_PATH", "data/corrections.jsonl"),
    )

from __future__ import annotations

import os
from dataclasses import dataclass


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    return default if value in (None, "") else float(value)


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    return default if value in (None, "") else int(value)


@dataclass(frozen=True)
class Settings:
    threshold: float = 0.72
    sample_count: int = 5
    live_docs_ttl_seconds: int = 900
    human_queue_name: str = "human-queue"
    default_route: str = "human-queue"
    model_name: str = "keyword-self-consistency"
    use_live_context: bool = True

    def __post_init__(self) -> None:
        if not 0.0 <= self.threshold <= 1.0:
            raise ValueError("threshold must be between 0 and 1")
        if self.sample_count < 1:
            raise ValueError("sample_count must be at least 1")
        if self.live_docs_ttl_seconds < 0:
            raise ValueError("live_docs_ttl_seconds cannot be negative")


def load_settings() -> Settings:
    return Settings(
        threshold=_env_float("TRIAGEPILOT_THRESHOLD", 0.72),
        sample_count=_env_int("TRIAGEPILOT_SAMPLE_COUNT", 5),
        live_docs_ttl_seconds=_env_int("TRIAGEPILOT_LIVE_DOCS_TTL", 900),
        human_queue_name=os.getenv("TRIAGEPILOT_HUMAN_QUEUE", "human-queue"),
        default_route=os.getenv("TRIAGEPILOT_DEFAULT_ROUTE", "human-queue"),
        model_name=os.getenv("TRIAGEPILOT_MODEL_NAME", "keyword-self-consistency"),
        use_live_context=os.getenv("TRIAGEPILOT_USE_LIVE_CONTEXT", "1") != "0",
    )

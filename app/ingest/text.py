from __future__ import annotations  # allow forward-referenced type hints on older Python


def clean_text(text: str) -> str:
    """Collapse repeated whitespace/newlines and trim ends, so downstream prompts stay compact."""
    return " ".join(text.strip().split())

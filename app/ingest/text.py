from __future__ import annotations


def clean_text(text: str) -> str:
    return " ".join(text.strip().split())


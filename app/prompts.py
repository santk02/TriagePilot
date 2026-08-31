from __future__ import annotations  # allow forward-referenced type hints on older Python

from typing import Iterable, Sequence  # type hints for chunk-joining helpers

from .models import NormalizedTicket  # the unified ticket shape prompts are built from
from .taxonomy import INTENT, URGENCY  # label definitions injected into the prompt text


def build_classification_prompt(ticket: NormalizedTicket, live_context: str = "") -> str:
    """Render the full classifier prompt for a ticket (used by an LLM-backed `PredictionBackend`;
    the default keyword backend ignores it, but any real model backend should consume this)."""
    parts = [
        "You are a support triage classifier.",
        "Return JSON with urgency, intent, and a brief rationale.",
        "Urgency labels: " + ", ".join(f"{k}: {v}" for k, v in URGENCY.items()),
        "Intent labels: " + ", ".join(f"{k}: {v}" for k, v in INTENT.items()),
        f"Ticket ID: {ticket.ticket_id}",
        f"Ticket content:\n{ticket.content}",
    ]
    if live_context.strip():
        parts.append(f"Live context:\n{live_context.strip()}")
    return "\n\n".join(parts)


def build_normalized_block(label: str, content: str) -> str:
    """Wrap one modality's extracted text in a `[LABEL]` tag, or return "" if there's nothing to show."""
    content = content.strip()
    return f"[{label.upper()}]\n{content}" if content else ""


def join_non_empty(chunks: Sequence[str]) -> str:
    """Join chunks with blank-line separators, dropping any that are blank/whitespace-only."""
    return "\n\n".join(chunk for chunk in chunks if chunk.strip())


def build_route_summary(urgency: str, intent: str, route: str) -> str:
    """Format a one-line human-readable summary of a routing decision, e.g. for logs/UI."""
    return f"{urgency} / {intent} -> {route}"

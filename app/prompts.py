from __future__ import annotations

from typing import Iterable, Sequence

from .models import NormalizedTicket
from .taxonomy import INTENT, URGENCY


def build_classification_prompt(ticket: NormalizedTicket, live_context: str = "") -> str:
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
    content = content.strip()
    return f"[{label.upper()}]\n{content}" if content else ""


def join_non_empty(chunks: Sequence[str]) -> str:
    return "\n\n".join(chunk for chunk in chunks if chunk.strip())


def build_route_summary(urgency: str, intent: str, route: str) -> str:
    return f"{urgency} / {intent} -> {route}"


from __future__ import annotations  # allow forward-referenced type hints on older Python

from itertools import product  # used to enumerate every (urgency, intent) combination for validation
from typing import Dict, Tuple  # type hints for the label/routing maps


# Urgency labels: how fast the ticket needs a response. P1 is the most severe.
URGENCY: Dict[str, str] = {
    "P1": "Service down or data loss. Immediate response.",
    "P2": "Major feature broken, no workaround. Same day.",
    "P3": "Feature broken with a workaround. Within 3 days.",
    "P4": "Question, request or cosmetic issue. Best effort.",
}

# Intent labels: what kind of request the ticket represents, independent of urgency.
INTENT: Dict[str, str] = {
    "bug": "Something works differently than documented.",
    "billing": "Charges, invoices, refunds, plan changes.",
    "howto": "User needs help using an existing feature.",
    "access": "Login, permissions, account recovery.",
    "feature": "Request for something that does not exist.",
    "outage": "Suspected platform-wide problem.",
}

# Every (urgency, intent) pair maps to a concrete owning queue/team.
ROUTING: Dict[Tuple[str, str], str] = {
    ("P1", "outage"): "sre-oncall",
    ("P1", "bug"): "eng-oncall",
    ("P1", "access"): "security-oncall",
    ("P1", "billing"): "billing-escalation",
    ("P1", "howto"): "human-queue",
    ("P1", "feature"): "product-escalation",
    ("P2", "bug"): "eng-triage",
    ("P2", "outage"): "sre-triage",
    ("P2", "access"): "support-triage",
    ("P2", "billing"): "billing-triage",
    ("P2", "howto"): "human-queue",
    ("P2", "feature"): "product-triage",
    ("P3", "bug"): "support-bug-queue",
    ("P3", "outage"): "support-outage-queue",
    ("P3", "access"): "support-access-queue",
    ("P3", "billing"): "billing-queue",
    ("P3", "howto"): "support-howto-queue",
    ("P3", "feature"): "product-ideas-queue",
    ("P4", "bug"): "support-queue",
    ("P4", "outage"): "support-queue",
    ("P4", "access"): "support-queue",
    ("P4", "billing"): "billing-queue",
    ("P4", "howto"): "support-howto-queue",
    ("P4", "feature"): "product-ideas-queue",
}

# Module-level fallback used only when a caller does not supply its own default (see `route_for`).
DEFAULT_ROUTE = "human-queue"


def validate_routing_map() -> None:
    """Assert every (urgency, intent) combination is explicitly routed; raise if any are missing."""
    missing = [
        pair
        for pair in product(URGENCY.keys(), INTENT.keys())
        if pair not in ROUTING
    ]
    if missing:
        raise ValueError(f"routing map missing combinations: {missing}")


def route_for(urgency: str, intent: str, default: str = DEFAULT_ROUTE) -> str:
    """Look up the owning queue for a label pair, falling back to `default` (safety net for
    unmapped or future labels, e.g. a taxonomy edit that outpaces the ROUTING table)."""
    return ROUTING.get((urgency, intent), default)


def all_labels() -> Dict[str, Dict[str, str]]:
    """Return both label dictionaries together, keyed by axis (urgency/intent)."""
    return {"urgency": URGENCY, "intent": INTENT}


# Run validation at import time so a malformed routing map fails fast, not mid-request.
validate_routing_map()

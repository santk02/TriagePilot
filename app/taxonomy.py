from __future__ import annotations

from itertools import product
from typing import Dict, Tuple


URGENCY: Dict[str, str] = {
    "P1": "Service down or data loss. Immediate response.",
    "P2": "Major feature broken, no workaround. Same day.",
    "P3": "Feature broken with a workaround. Within 3 days.",
    "P4": "Question, request or cosmetic issue. Best effort.",
}

INTENT: Dict[str, str] = {
    "bug": "Something works differently than documented.",
    "billing": "Charges, invoices, refunds, plan changes.",
    "howto": "User needs help using an existing feature.",
    "access": "Login, permissions, account recovery.",
    "feature": "Request for something that does not exist.",
    "outage": "Suspected platform-wide problem.",
}

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

DEFAULT_ROUTE = "human-queue"


def validate_routing_map() -> None:
    missing = [
        pair
        for pair in product(URGENCY.keys(), INTENT.keys())
        if pair not in ROUTING
    ]
    if missing:
        raise ValueError(f"routing map missing combinations: {missing}")


def route_for(urgency: str, intent: str) -> str:
    return ROUTING.get((urgency, intent), DEFAULT_ROUTE)


def all_labels() -> Dict[str, Dict[str, str]]:
    return {"urgency": URGENCY, "intent": INTENT}


validate_routing_map()


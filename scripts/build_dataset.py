from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from app.taxonomy import route_for

SEED_ROWS: List[Dict[str, str]] = [
    {"ticket_id": "t1", "text": "The site is down and returning 503 errors.", "urgency": "P1", "intent": "outage", "route": "sre-oncall"},
    {"ticket_id": "t2", "text": "I cannot log in after resetting my password.", "urgency": "P2", "intent": "access", "route": "support-triage"},
    {"ticket_id": "t3", "text": "How do I export invoices for last month?", "urgency": "P4", "intent": "howto", "route": "support-howto-queue"},
    {"ticket_id": "t4", "text": "My payment was charged twice and I need a refund.", "urgency": "P3", "intent": "billing", "route": "billing-queue"},
    {"ticket_id": "t5", "text": "The dashboard crashes when I open reports.", "urgency": "P2", "intent": "bug", "route": "eng-triage"},
    {"ticket_id": "t6", "text": "Please add support for SSO on the free plan.", "urgency": "P4", "intent": "feature", "route": "product-ideas-queue"},
]


TEMPLATES = [
    ("P1", "outage", "The service is down and returning 500 errors."),
    ("P2", "bug", "The export button crashes the page when I click it."),
    ("P2", "access", "I cannot log in because 2FA codes are not accepted."),
    ("P3", "billing", "I was charged incorrectly and need a refund."),
    ("P4", "howto", "How do I invite teammates to the workspace?"),
    ("P4", "feature", "Please add a dark mode option to the product."),
]


def generate_dataset(size: int = 200) -> List[Dict[str, str]]:
    rows = list(SEED_ROWS)
    index = 7
    while len(rows) < size:
        urgency, intent, text = TEMPLATES[(len(rows) - len(SEED_ROWS)) % len(TEMPLATES)]
        rows.append(
            {
                "ticket_id": f"t{index}",
                "text": f"{text} #{index}",
                "urgency": urgency,
                "intent": intent,
                "route": route_for(urgency, intent),
            }
        )
        index += 1
    return rows[:size]


def main() -> None:
    out_path = Path("evaluation/labelled_tickets.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(generate_dataset(), indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":  # pragma: no cover
    main()

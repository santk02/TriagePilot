from __future__ import annotations

from typing import Dict, Optional

from ..models import NormalizedTicket
from ..prompts import build_classification_prompt
from .backend import KeywordBackend, PredictionBackend


def classify(
    ticket_text: str,
    live_context: str = "",
    backend: Optional[PredictionBackend] = None,
) -> Dict[str, str]:
    """Return a one-shot urgency/intent prediction without confidence."""

    ticket = NormalizedTicket(ticket_id="baseline", content=ticket_text)
    _ = build_classification_prompt(ticket, live_context=live_context)
    prediction = (backend or KeywordBackend()).predict(ticket_text, live_context=live_context)
    return {"urgency": prediction.urgency, "intent": prediction.intent, "route": prediction.route}


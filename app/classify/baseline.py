from __future__ import annotations  # allow forward-referenced type hints on older Python

from typing import Dict, Optional  # type hints for the single-shot classify() signature

from ..models import NormalizedTicket  # wrap raw text so prompt-building can reuse the shared shape
from ..prompts import build_classification_prompt  # renders the prompt an LLM backend would consume
from .backend import KeywordBackend, PredictionBackend  # default + pluggable classifier backends


def classify(
    ticket_text: str,
    live_context: str = "",
    backend: Optional[PredictionBackend] = None,
) -> Dict[str, str]:
    """Return a one-shot urgency/intent prediction with no confidence signal.

    This is the Phase 1 baseline the blueprint calls out: it must be measured on the same test
    set as the paper method so the paper method's improvement claim is a comparison, not an
    assertion (see `evaluation/run_eval.py`).
    """

    ticket = NormalizedTicket(ticket_id="baseline", content=ticket_text)
    # Prompt is built (and would be sent to an LLM backend) even though the default KeywordBackend
    # ignores it — this keeps the call signature identical to the confidence-aware path in
    # `paper_method.py`, so swapping in a real LLM backend requires no changes here.
    _ = build_classification_prompt(ticket, live_context=live_context)
    prediction = (backend or KeywordBackend()).predict(ticket_text, live_context=live_context)
    return {"urgency": prediction.urgency, "intent": prediction.intent, "route": prediction.route}

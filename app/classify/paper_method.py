from __future__ import annotations  # allow forward-referenced type hints on older Python

from collections import Counter  # tally votes across the k samples
from dataclasses import dataclass  # small typed summary of a confidence-scored decision
from typing import Dict, List, Optional  # shared type hints

from ..models import ClassificationResult, NormalizedTicket, SamplePrediction  # shared DTOs
from ..prompts import build_classification_prompt  # renders the prompt an LLM backend would consume
from ..taxonomy import DEFAULT_ROUTE, route_for  # label -> queue lookup
from .backend import KeywordBackend, PredictionBackend  # default + pluggable classifier backends


@dataclass(slots=True)
class ConfidenceSummary:
    """Typed view of a self-consistency decision (mirrors the dict `classify_with_confidence` returns)."""

    urgency: str
    intent: str
    confidence: float
    runner_up: Optional[str]
    samples: List[SamplePrediction]


def _sample_predictions(
    text: str,
    k: int,
    backend: PredictionBackend,
    live_context: str = "",
) -> List[SamplePrediction]:
    """Draw k independent predictions for the same ticket from the given backend."""
    samples: List[SamplePrediction] = []
    for _ in range(k):
        samples.append(backend.predict(text, live_context=live_context))
    return samples


def classify_with_confidence(
    text: str,
    k: int = 5,
    backend: Optional[PredictionBackend] = None,
    live_context: str = "",
    default_route: str = DEFAULT_ROUTE,
) -> Dict[str, object]:
    """Reproduced paper method: sample k times and use cross-sample agreement as the confidence
    signal (self-consistency), rather than trusting the model's self-reported certainty.

    Joint confidence is `(urgency agreement) x (intent agreement)`, so a routing decision is only
    considered safe when BOTH axes agree — see PAPER_NOTES.md for why agreement-as-confidence
    calibrates better than an LLM's own stated confidence.
    """

    if k < 1:
        raise ValueError("k must be at least 1")

    backend = backend or KeywordBackend()
    ticket = NormalizedTicket(ticket_id="paper-method", content=text)
    # Prompt is built (and would be sent to an LLM backend) even though the default KeywordBackend
    # ignores it — keeps this path prompt-compatible with a real LLM backend swap.
    _ = build_classification_prompt(ticket, live_context=live_context)

    samples = _sample_predictions(text, k=k, backend=backend, live_context=live_context)
    urgency_votes = Counter(sample.urgency for sample in samples)
    intent_votes = Counter(sample.intent for sample in samples)

    urgency, urgency_count = urgency_votes.most_common(1)[0]
    intent, intent_count = intent_votes.most_common(1)[0]
    runner_up = None
    if len(intent_votes) > 1:
        # Second-most-voted intent, handed to the human queue as a shortlist when confidence is low.
        runner_up = intent_votes.most_common(2)[1][0]

    # Joint confidence: both urgency and intent must agree for the routing decision to be safe.
    confidence = (urgency_count / k) * (intent_count / k)
    route = route_for(urgency, intent, default=default_route)
    top_guesses = [intent]
    if runner_up and runner_up not in top_guesses:
        top_guesses.append(runner_up)

    return {
        "urgency": urgency,
        "intent": intent,
        "route": route,
        "confidence": confidence,
        "runner_up": runner_up,
        "top_guesses": top_guesses,
        "samples": [sample.to_dict() for sample in samples],  # kept for the audit trail
    }


def classify_ticket_with_confidence(
    ticket: NormalizedTicket,
    k: int = 5,
    backend: Optional[PredictionBackend] = None,
    live_context: str = "",
    default_route: str = DEFAULT_ROUTE,
) -> ClassificationResult:
    """Convenience wrapper: same as `classify_with_confidence`, but takes/returns the richer
    `NormalizedTicket`/`ClassificationResult` DTOs instead of raw text and a dict. `threshold`
    is left at 0.0 here — callers that need routing should pass the result through
    `classify.router.route_prediction` with the configured threshold (see `app/api.py`)."""
    backend = backend or KeywordBackend()
    result = classify_with_confidence(
        ticket.content, k=k, backend=backend, live_context=live_context, default_route=default_route
    )
    return ClassificationResult(
        ticket_id=ticket.ticket_id,
        urgency=result["urgency"],
        intent=result["intent"],
        route=result["route"],
        confidence=float(result["confidence"]),
        threshold=0.0,
        action="auto-route",
        reason="",
        runner_up=result["runner_up"],
        top_guesses=list(result["top_guesses"]),
        samples=[SamplePrediction(**sample) for sample in result["samples"]],
        live_context=live_context,
        model_name=type(backend).__name__,
    )

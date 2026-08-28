from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Optional

from ..models import ClassificationResult, NormalizedTicket, SamplePrediction
from ..prompts import build_classification_prompt
from ..taxonomy import route_for
from .backend import KeywordBackend, PredictionBackend


@dataclass(slots=True)
class ConfidenceSummary:
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
    samples: List[SamplePrediction] = []
    for _ in range(k):
        samples.append(backend.predict(text, live_context=live_context))
    return samples


def classify_with_confidence(
    text: str,
    k: int = 5,
    backend: Optional[PredictionBackend] = None,
    live_context: str = "",
) -> Dict[str, object]:
    """Sample k times and use agreement as the confidence signal."""

    if k < 1:
        raise ValueError("k must be at least 1")

    backend = backend or KeywordBackend()
    ticket = NormalizedTicket(ticket_id="paper-method", content=text)
    _ = build_classification_prompt(ticket, live_context=live_context)

    samples = _sample_predictions(text, k=k, backend=backend, live_context=live_context)
    urgency_votes = Counter(sample.urgency for sample in samples)
    intent_votes = Counter(sample.intent for sample in samples)

    urgency, urgency_count = urgency_votes.most_common(1)[0]
    intent, intent_count = intent_votes.most_common(1)[0]
    runner_up = None
    if len(intent_votes) > 1:
        runner_up = intent_votes.most_common(2)[1][0]

    confidence = (urgency_count / k) * (intent_count / k)
    route = route_for(urgency, intent)
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
        "samples": [sample.to_dict() for sample in samples],
    }


def classify_ticket_with_confidence(
    ticket: NormalizedTicket,
    k: int = 5,
    backend: Optional[PredictionBackend] = None,
    live_context: str = "",
) -> ClassificationResult:
    backend = backend or KeywordBackend()
    result = classify_with_confidence(
        ticket.content, k=k, backend=backend, live_context=live_context
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
        model_name=getattr(backend, "__class__", type("X", (), {})).__name__,
    )

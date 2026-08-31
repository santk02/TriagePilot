from __future__ import annotations  # allow forward-referenced type hints on older Python

from dataclasses import dataclass  # small typed view of a routing decision
from typing import Dict  # type hint for to_dict()

from ..models import ClassificationResult  # the prediction this module gates


@dataclass(frozen=True)
class RouteDecision:
    """Standalone (non-ClassificationResult) view of a routing outcome, for callers that only
    need the decision fields rather than the full prediction."""

    action: str
    route: str
    confidence: float
    threshold: float
    reason: str

    def to_dict(self) -> Dict[str, object]:
        return {
            "action": self.action,
            "route": self.route,
            "confidence": self.confidence,
            "threshold": self.threshold,
            "reason": self.reason,
        }


def route_prediction(
    prediction: ClassificationResult,
    threshold: float,
    human_queue: str = "human-queue",
) -> ClassificationResult:
    """The confidence gate: this is the whole product (see blueprint's design rule).

    At or above `threshold`, auto-route to the predicted queue. Below it, abstain and send to the
    human queue instead — carrying the top-2 guesses so the human starts from a shortlist rather
    than nothing. Returns a NEW `ClassificationResult` with the routing fields resolved.
    """
    action = "auto-route" if prediction.confidence >= threshold else "human-review"
    route = prediction.route if action == "auto-route" else human_queue
    reason = (
        f"confidence {prediction.confidence:.3f} meets threshold {threshold:.3f}"
        if action == "auto-route"
        else f"confidence {prediction.confidence:.3f} is below threshold {threshold:.3f}; top guesses: {', '.join(prediction.top_guesses)}"
    )
    return ClassificationResult(
        ticket_id=prediction.ticket_id,
        urgency=prediction.urgency,
        intent=prediction.intent,
        route=route,
        confidence=prediction.confidence,
        threshold=threshold,
        action=action,
        reason=reason,
        runner_up=prediction.runner_up,
        top_guesses=list(prediction.top_guesses),
        samples=prediction.samples,
        live_context=prediction.live_context,
        model_name=prediction.model_name,
    )

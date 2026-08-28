from __future__ import annotations

from app.classify.paper_method import classify_with_confidence
from app.classify.router import route_prediction
from app.models import ClassificationResult, TicketInput
from app.taxonomy import route_for


def assert_p1_is_safe(
    text: str = "The service is down and returning 503 errors.",
) -> None:
    result = classify_with_confidence(text)
    prediction = ClassificationResult(
        ticket_id="p1-check",
        urgency=str(result["urgency"]),
        intent=str(result["intent"]),
        route=str(result["route"]),
        confidence=float(result["confidence"]),
        threshold=0.0,
        action="auto-route",
    )
    routed = route_prediction(prediction, threshold=0.95)
    assert routed.urgency == "P1"
    assert routed.route in {"sre-oncall", "human-queue"}
    assert routed.action in {"auto-route", "human-review"}


def assert_low_confidence_abstains() -> None:
    prediction = ClassificationResult(
        ticket_id="low-confidence",
        urgency="P4",
        intent="howto",
        route=route_for("P4", "howto"),
        confidence=0.1,
        threshold=0.0,
        action="auto-route",
    )
    routed = route_prediction(prediction, threshold=0.5)
    assert routed.action == "human-review"


def test_deepeval_assertions() -> None:
    """Dependency-free CI entry point; DeepEval can wrap these assertions later."""
    assert_p1_is_safe()
    assert_low_confidence_abstains()

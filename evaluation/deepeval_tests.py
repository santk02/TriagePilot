from __future__ import annotations  # allow forward-referenced type hints on older Python

import unittest  # wraps the assertions in a TestCase so `python -m unittest` actually discovers them

from app.classify.paper_method import classify_with_confidence  # the confidence-scored classifier
from app.classify.router import route_prediction  # the threshold gate under test
from app.models import ClassificationResult  # the routed-decision DTO under test
from app.taxonomy import route_for  # expected-route lookup for the fixed-prediction assertion


def assert_p1_is_safe(
    text: str = "The service is down and returning 503 errors.",
) -> None:
    """Safety assertion: an obvious outage ticket must classify as P1, and — auto-routed or
    abstained — must never resolve to anything other than the SRE on-call path or a human."""
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
    """Safety assertion: a prediction below the threshold must abstain to human review, never
    auto-route on a guess."""
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


class DeepEvalAssertions(unittest.TestCase):
    """CI safety gate, dependency-free but DeepEval-compatible: a real DeepEval suite can wrap
    these same assertions as `GEval`/custom metrics without changing the logic under test.

    NOTE (audit fix): this MUST be a `unittest.TestCase` — CI invokes
    `python -m unittest evaluation.deepeval_tests`, and unittest's module discovery only finds
    `TestCase` subclasses. A bare `test_*` function here is silently skipped ("Ran 0 tests"),
    which meant these safety assertions were never actually executed by CI before this fix.
    """

    def test_p1_is_safe(self) -> None:
        assert_p1_is_safe()

    def test_low_confidence_abstains(self) -> None:
        assert_low_confidence_abstains()


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

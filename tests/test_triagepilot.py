from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.api import TriageService
from app.classify.baseline import classify as baseline_classify
from app.classify.paper_method import classify_with_confidence
from app.classify.router import route_prediction
from app.config import Settings
from app.context.live_docs import LiveDocsClient, MemoryCache
from app.feedback.corrections import export_corrections, record_correction
from app.ingest.normalise import normalise_ticket
from app.models import CorrectionRecord, TicketInput
from app.taxonomy import INTENT, ROUTING, URGENCY, route_for, validate_routing_map


class TriagePilotTests(unittest.TestCase):
    def test_taxonomy_is_complete(self) -> None:
        validate_routing_map()
        self.assertIn("P1", URGENCY)
        self.assertIn("bug", INTENT)
        self.assertEqual(route_for("P1", "outage"), "sre-oncall")

    def test_normalisation_combines_modalities(self) -> None:
        ticket = TicketInput(
            ticket_id="x1",
            text="Help with login",
            screenshot_text="",
            voice_transcript="Call me back",
            metadata={"ocr_text": "500 error on screen"},
        )
        normalized = normalise_ticket(ticket)
        self.assertIn("[TEXT]", normalized.content)
        self.assertIn("[SCREENSHOT]", normalized.content)
        self.assertIn("[VOICE]", normalized.content)

    def test_baseline_and_paper_method_return_labels(self) -> None:
        baseline = baseline_classify("The service is down and returning 503.")
        paper = classify_with_confidence("The service is down and returning 503.")
        self.assertIn(baseline["urgency"], URGENCY)
        self.assertIn(paper["urgency"], URGENCY)
        self.assertGreaterEqual(float(paper["confidence"]), 0.0)

    def test_router_abstains_below_threshold(self) -> None:
        from app.models import ClassificationResult

        prediction = ClassificationResult(
            ticket_id="low",
            urgency="P4",
            intent="howto",
            route=route_for("P4", "howto"),
            confidence=0.1,
            threshold=0.0,
            action="auto-route",
        )
        routed = route_prediction(prediction, threshold=0.5)
        self.assertEqual(routed.action, "human-review")
        self.assertEqual(routed.route, "human-queue")

    def test_live_docs_cache(self) -> None:
        calls = []

        def fetcher(url: str) -> str:
            calls.append(url)
            return "status ok"

        client = LiveDocsClient(cache=MemoryCache(ttl_seconds=1000), fetcher=fetcher)
        first = client.fetch("status")
        second = client.fetch("status")
        self.assertEqual(first, "status ok")
        self.assertEqual(second, "status ok")
        self.assertEqual(len(calls), 1)

    def test_feedback_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "corrections.jsonl"
            correction = CorrectionRecord(
                ticket_id="c1",
                predicted_urgency="P4",
                predicted_intent="howto",
                corrected_urgency="P2",
                corrected_intent="bug",
                confidence=0.2,
            )
            record_correction(path, correction)
            rows = export_corrections(path)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["ticket_id"], "c1")

    def test_service_triage_returns_decision(self) -> None:
        service = TriageService(Settings(threshold=0.5, sample_count=3))
        result = service.triage(TicketInput(ticket_id="svc-1", text="The app is down."))
        self.assertIn(result.action, {"auto-route", "human-review"})
        self.assertIn(result.urgency, URGENCY)

    def test_low_confidence_result_enters_human_queue(self) -> None:
        service = TriageService(Settings(threshold=0.99, sample_count=3))
        result = service.triage(TicketInput(ticket_id="queued", text="Please help."))
        self.assertEqual(result.action, "human-review")
        self.assertEqual(service.queue()[0]["ticket_id"], "queued")
        self.assertEqual(service.queue()[0]["top_guesses"], result.top_guesses)

    def test_service_exports_corrections(self) -> None:
        service = TriageService(Settings(use_live_context=False))
        correction = CorrectionRecord(
            ticket_id="c2",
            predicted_urgency="P4",
            predicted_intent="howto",
            corrected_urgency="P2",
            corrected_intent="bug",
            confidence=0.3,
        )
        service.record_correction(correction)
        self.assertEqual(service.export_corrections(), [correction.to_dict()])

    def test_invalid_sampling_configuration_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            Settings(sample_count=0)
        with self.assertRaises(ValueError):
            Settings(threshold=1.1)

    def test_paper_method_rejects_invalid_k(self) -> None:
        with self.assertRaises(ValueError):
            classify_with_confidence("help", k=0)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

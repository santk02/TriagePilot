from __future__ import annotations

from typing import Any, Dict, List, Optional

from .classify.paper_method import classify_with_confidence
from .classify.router import route_prediction
from .config import Settings, load_settings
from .context.live_docs import LiveDocsClient
from .ingest.normalise import normalise_ticket
from .models import (
    ClassificationResult,
    CorrectionRecord,
    SamplePrediction,
    TicketInput,
)


class TriageService:
    def __init__(
        self,
        settings: Optional[Settings] = None,
        live_docs: Optional[LiveDocsClient] = None,
    ) -> None:
        self.settings = settings or load_settings()
        self.live_docs = live_docs or LiveDocsClient(
            ttl_seconds=self.settings.live_docs_ttl_seconds
        )
        self.corrections: List[CorrectionRecord] = []
        self._human_queue: List[ClassificationResult] = []

    def triage(self, ticket: TicketInput) -> ClassificationResult:
        normalized = normalise_ticket(ticket)
        live_context = (
            self.live_docs.build_context() if self.settings.use_live_context else ""
        )
        raw = classify_with_confidence(
            normalized.content,
            k=self.settings.sample_count,
            live_context=live_context,
        )
        prediction = ClassificationResult(
            ticket_id=ticket.ticket_id,
            urgency=str(raw["urgency"]),
            intent=str(raw["intent"]),
            route=str(raw["route"]),
            confidence=float(raw["confidence"]),
            threshold=self.settings.threshold,
            action="auto-route",
            reason="",
            runner_up=raw["runner_up"],
            top_guesses=list(raw["top_guesses"]),
            samples=[],
            live_context=live_context,
            model_name=self.settings.model_name,
        )
        prediction.samples = [SamplePrediction(**sample) for sample in raw["samples"]]
        routed = route_prediction(
            prediction,
            threshold=self.settings.threshold,
            human_queue=self.settings.human_queue_name,
        )
        if routed.action == "human-review":
            self._human_queue.append(routed)
        return routed

    def queue(self) -> List[Dict[str, Any]]:
        return [prediction.to_dict() for prediction in self._human_queue]

    def record_correction(self, correction: CorrectionRecord) -> None:
        self.corrections.append(correction)

    def export_corrections(self) -> List[Dict[str, Any]]:
        return [correction.to_dict() for correction in self.corrections]

from __future__ import annotations  # allow forward-referenced type hints on older Python

import time  # stage timing recorded into trace events
from typing import Any, Dict, List, Optional  # shared type hints

from .classify.paper_method import classify_with_confidence  # the reproduced self-consistency method
from .classify.router import route_prediction  # confidence-threshold gate
from .config import Settings, load_settings  # runtime configuration
from .context.live_docs import LiveDocsClient  # Firecrawl-style live-docs fetch + cache
from .feedback.corrections import export_corrections, record_correction  # durable correction log
from .ingest.normalise import normalise_ticket  # any modality -> one text blob
from .models import (
    ClassificationResult,
    CorrectionRecord,
    SamplePrediction,
    TicketInput,
)
from .observability.tracing import MemoryTracer  # per-ticket pipeline event trace


class TriageService:
    """Orchestrates the full pipeline: normalise -> live context -> classify -> route -> queue,
    and exposes the correction/feedback loop. This is the object `app.main.create_app()` wraps
    with HTTP handlers; it is deliberately transport-agnostic so it can be unit tested directly.
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        live_docs: Optional[LiveDocsClient] = None,
        tracer: Optional[MemoryTracer] = None,
    ) -> None:
        self.settings = settings or load_settings()
        self.live_docs = live_docs or LiveDocsClient(
            ttl_seconds=self.settings.live_docs_ttl_seconds
        )
        self.tracer = tracer or MemoryTracer()  # records per-stage timing/events for observability
        self.corrections: List[CorrectionRecord] = []  # fast in-memory view for GET /v1/corrections/export
        self._human_queue: List[ClassificationResult] = []  # low-confidence results awaiting a human

    def triage(self, ticket: TicketInput) -> ClassificationResult:
        """Run one ticket through the full pipeline and return the routed decision."""
        stage_start = time.monotonic()

        normalized = normalise_ticket(ticket)
        self.tracer.emit(
            "ingest.normalise", ticket_id=ticket.ticket_id, duration_ms=self._elapsed_ms(stage_start)
        )

        stage_start = time.monotonic()
        live_context = (
            self.live_docs.build_context() if self.settings.use_live_context else ""
        )
        self.tracer.emit(
            "context.live_docs",
            ticket_id=ticket.ticket_id,
            used=self.settings.use_live_context,
            chars=len(live_context),
            duration_ms=self._elapsed_ms(stage_start),
        )

        stage_start = time.monotonic()
        raw = classify_with_confidence(
            normalized.content,
            k=self.settings.sample_count,
            live_context=live_context,
            default_route=self.settings.default_route,
        )
        self.tracer.emit(
            "classify.paper_method",
            ticket_id=ticket.ticket_id,
            confidence=raw["confidence"],
            duration_ms=self._elapsed_ms(stage_start),
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
        self.tracer.emit(
            "route.decision",
            ticket_id=ticket.ticket_id,
            action=routed.action,
            route=routed.route,
        )
        if routed.action == "human-review":
            self._human_queue.append(routed)  # low-confidence: hold for a human with top-2 guesses
        return routed

    @staticmethod
    def _elapsed_ms(started_at: float) -> float:
        """Milliseconds elapsed since `started_at` (a `time.monotonic()` reading)."""
        return round((time.monotonic() - started_at) * 1000, 3)

    def queue(self) -> List[Dict[str, Any]]:
        """Return every prediction currently awaiting human review."""
        return [prediction.to_dict() for prediction in self._human_queue]

    def traces(self) -> List[Dict[str, Any]]:
        """Return the recorded per-ticket pipeline events (ingest/context/classify/route timings)."""
        return self.tracer.to_list()

    def record_correction(self, correction: CorrectionRecord) -> None:
        """Store a human override both in memory (fast read path) and durably on disk, so the
        correction survives a process restart and is exportable as new labelled training data."""
        self.corrections.append(correction)
        record_correction(self.settings.corrections_path, correction)

    def export_corrections(self) -> List[Dict[str, Any]]:
        """Return every correction ever recorded, read from the durable on-disk log."""
        return export_corrections(self.settings.corrections_path)

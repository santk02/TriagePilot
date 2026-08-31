from __future__ import annotations  # allow forward-referenced type hints on older Python

from dataclasses import asdict, dataclass, field  # dataclasses give us cheap, typed DTOs + dict conversion
from datetime import datetime, timezone  # UTC timestamps for created_at fields
from typing import Any, Dict, List, Optional  # shared type hints


def utcnow_iso() -> str:
    """Return the current UTC time as an ISO-8601 string (used for all `created_at` defaults)."""
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class TicketInput:
    """Raw ticket as submitted to the API: text plus optional screenshot/voice references."""

    ticket_id: str
    text: str = ""
    screenshot_text: str = ""  # OCR text or a reference to the screenshot
    voice_transcript: str = ""  # transcript or a reference to the voice note
    metadata: Dict[str, Any] = field(default_factory=dict)  # e.g. injected {"ocr_text": ...}

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class NormalizedTicket:
    """A ticket after all modalities have been merged into one text blob for the classifier."""

    ticket_id: str
    content: str  # the unified [TEXT]/[SCREENSHOT]/[VOICE] blob fed to the classifier
    text: str = ""
    screenshot_text: str = ""
    voice_transcript: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SamplePrediction:
    """One draw from the self-consistency sampler (one of the k votes)."""

    urgency: str
    intent: str
    route: str
    rationale: str = ""  # short note on why the backend produced this sample

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ClassificationResult:
    """Final triage decision for a ticket: labels, confidence, routing outcome, and audit trail."""

    ticket_id: str
    urgency: str
    intent: str
    route: str  # the actual queue this ticket lands in (owning team, or the human queue)
    confidence: float  # agreement-derived confidence in [0, 1]
    threshold: float  # the threshold this decision was evaluated against
    action: str  # "auto-route" or "human-review"
    runner_up: Optional[str] = None  # second-most-voted intent, if any
    top_guesses: List[str] = field(default_factory=list)  # intent shortlist shown to humans
    samples: List[SamplePrediction] = field(default_factory=list)  # full k-sample audit trail
    live_context: str = ""  # the live-docs context actually used for this classification
    model_name: str = ""  # which backend produced this result
    created_at: str = field(default_factory=utcnow_iso)
    reason: str = ""  # human-readable explanation of the routing decision

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["samples"] = [sample.to_dict() for sample in self.samples]
        return payload


@dataclass(slots=True)
class CorrectionRecord:
    """A human override of a prediction, captured as new labelled training data."""

    ticket_id: str
    predicted_urgency: str
    predicted_intent: str
    corrected_urgency: str
    corrected_intent: str
    confidence: float  # the model's confidence at the time it was overridden
    comment: str = ""
    created_at: str = field(default_factory=utcnow_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

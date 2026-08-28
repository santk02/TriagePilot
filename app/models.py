from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class TicketInput:
    ticket_id: str
    text: str = ""
    screenshot_text: str = ""
    voice_transcript: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class NormalizedTicket:
    ticket_id: str
    content: str
    text: str = ""
    screenshot_text: str = ""
    voice_transcript: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SamplePrediction:
    urgency: str
    intent: str
    route: str
    rationale: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ClassificationResult:
    ticket_id: str
    urgency: str
    intent: str
    route: str
    confidence: float
    threshold: float
    action: str
    runner_up: Optional[str] = None
    top_guesses: List[str] = field(default_factory=list)
    samples: List[SamplePrediction] = field(default_factory=list)
    live_context: str = ""
    model_name: str = ""
    created_at: str = field(default_factory=utcnow_iso)
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["samples"] = [sample.to_dict() for sample in self.samples]
        return payload


@dataclass(slots=True)
class CorrectionRecord:
    ticket_id: str
    predicted_urgency: str
    predicted_intent: str
    corrected_urgency: str
    corrected_intent: str
    confidence: float
    comment: str = ""
    created_at: str = field(default_factory=utcnow_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

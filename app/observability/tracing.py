from __future__ import annotations  # allow forward-referenced type hints on older Python

from dataclasses import asdict, dataclass, field  # lightweight, dict-convertible event records
from datetime import datetime, timezone  # UTC timestamps on every event
from typing import Any, Dict, List  # type hints


def _ts() -> str:
    """Current UTC time as an ISO-8601 string (used for every `TraceEvent.created_at`)."""
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class TraceEvent:
    """One named observability event with an arbitrary JSON-serialisable payload."""

    name: str
    payload: Dict[str, Any]
    created_at: str = field(default_factory=_ts)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MemoryTracer:
    """Minimal in-process stand-in for the blueprint's Langfuse tracing layer.

    Records per-ticket pipeline events (ingest, live-context fetch, classify, route) with enough
    payload to reconstruct cost/latency later. It intentionally has the same shape a Langfuse (or
    OpenTelemetry) exporter would — swap `emit` for a real exporter call without touching callers.
    `TriageService` wires this in and exposes recent events via `GET /v1/traces`.
    """

    def __init__(self) -> None:
        self.events: List[TraceEvent] = []

    def emit(self, name: str, **payload: Any) -> None:
        """Record one named event with arbitrary keyword payload (e.g. `ticket_id`, `duration_ms`)."""
        self.events.append(TraceEvent(name=name, payload=dict(payload)))

    def to_list(self) -> List[Dict[str, Any]]:
        """Return all recorded events as plain dicts, oldest first."""
        return [event.to_dict() for event in self.events]

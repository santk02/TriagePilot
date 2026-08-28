from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class TraceEvent:
    name: str
    payload: Dict[str, Any]
    created_at: str = field(default_factory=_ts)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MemoryTracer:
    def __init__(self) -> None:
        self.events: List[TraceEvent] = []

    def emit(self, name: str, **payload: Any) -> None:
        self.events.append(TraceEvent(name=name, payload=dict(payload)))

    def to_list(self) -> List[Dict[str, Any]]:
        return [event.to_dict() for event in self.events]


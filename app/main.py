from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from .api import TriageService
from .models import CorrectionRecord, TicketInput

service = TriageService()


def _ticket_from_dict(payload: Dict[str, Any]) -> TicketInput:
    if not isinstance(payload, dict):
        raise ValueError("ticket payload must be an object")
    ticket_id = str(payload.get("ticket_id", "")).strip()
    if not ticket_id:
        raise ValueError("ticket_id is required")
    return TicketInput(
        ticket_id=ticket_id,
        text=payload.get("text", ""),
        screenshot_text=payload.get("screenshot_text", ""),
        voice_transcript=payload.get("voice_transcript", ""),
        metadata=payload.get("metadata", {}) or {},
    )


try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import HTMLResponse
except Exception:  # pragma: no cover - optional dependency
    FastAPI = None
    HTTPException = Exception


def create_app():
    if FastAPI is None:
        raise RuntimeError(
            "FastAPI is not installed. Install requirements to run the API."
        )

    app = FastAPI(title="TriagePilot", version="0.1.0")

    @app.get("/health")
    def health() -> Dict[str, str]:
        return {"status": "ok"}

    @app.get("/", response_class=HTMLResponse)
    def dashboard() -> str:
        return (Path(__file__).with_name("dashboard.html")).read_text(encoding="utf-8")

    @app.post("/v1/triage")
    def triage(payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            result = service.triage(_ticket_from_dict(payload))
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return result.to_dict()

    @app.get("/v1/queue")
    def queue() -> Dict[str, Any]:
        return {"items": service.queue()}

    @app.post("/v1/corrections")
    def corrections(payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            correction = CorrectionRecord(
                ticket_id=str(payload["ticket_id"]),
                predicted_urgency=str(payload["predicted_urgency"]),
                predicted_intent=str(payload["predicted_intent"]),
                corrected_urgency=str(payload["corrected_urgency"]),
                corrected_intent=str(payload["corrected_intent"]),
                confidence=float(payload.get("confidence", 0.0)),
                comment=str(payload.get("comment", "")),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=422, detail=f"invalid correction: {exc}"
            ) from exc
        service.record_correction(correction)
        return correction.to_dict()

    @app.get("/v1/corrections/export")
    def corrections_export() -> Dict[str, Any]:
        return {"items": service.export_corrections()}

    return app


if __name__ == "__main__":  # pragma: no cover
    import json

    sample = {
        "ticket_id": "demo-1",
        "text": "The app shows a 500 error after login and I cannot continue.",
    }
    print(json.dumps(service.triage(_ticket_from_dict(sample)).to_dict(), indent=2))

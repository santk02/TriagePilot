from __future__ import annotations  # allow forward-referenced type hints on older Python

from pathlib import Path  # locate dashboard.html relative to this file
from typing import Any, Dict  # request/response payload type hints

from .api import TriageService  # pipeline orchestrator the HTTP layer delegates to
from .models import CorrectionRecord, TicketInput  # request/response DTOs

# Single shared service instance for the process (mirrors a typical FastAPI singleton pattern;
# swap for dependency injection if per-request settings/backends are ever needed).
service = TriageService()


def _ticket_from_dict(payload: Dict[str, Any]) -> TicketInput:
    """Validate and convert a raw JSON POST body into a `TicketInput`, raising `ValueError` on
    anything malformed so the API layer can turn it into a clean 422 response."""
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
    # FastAPI is an optional dependency at import time: the pure-Python pipeline (TriageService)
    # must stay importable/testable even in environments where FastAPI isn't installed.
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import HTMLResponse
except Exception:  # pragma: no cover - optional dependency
    FastAPI = None
    HTTPException = Exception


def create_app():
    """Build the FastAPI app (the Dockerfile's `uvicorn app.main:create_app --factory` entrypoint).

    Raises `RuntimeError` if FastAPI isn't installed, since there is no app to build without it.
    """
    if FastAPI is None:
        raise RuntimeError(
            "FastAPI is not installed. Install requirements to run the API."
        )

    app = FastAPI(title="TriagePilot", version="0.1.0")

    @app.get("/health")
    def health() -> Dict[str, str]:
        """Liveness probe for Docker/orchestrators."""
        return {"status": "ok"}

    @app.get("/", response_class=HTMLResponse)
    def dashboard() -> str:
        """Serve the single-page HTML dashboard (no separate frontend build required)."""
        return (Path(__file__).with_name("dashboard.html")).read_text(encoding="utf-8")

    @app.post("/v1/triage")
    def triage(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Classify one ticket and return the routed decision (auto-route or human-review)."""
        try:
            result = service.triage(_ticket_from_dict(payload))
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return result.to_dict()

    @app.get("/v1/queue")
    def queue() -> Dict[str, Any]:
        """List every ticket currently waiting on human review."""
        return {"items": service.queue()}

    @app.get("/v1/traces")
    def traces() -> Dict[str, Any]:
        """List recorded per-ticket pipeline events (ingest/context/classify/route timings)."""
        return {"items": service.traces()}

    @app.post("/v1/corrections")
    def corrections(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Record a human override of a prediction as new labelled training data."""
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
        """Export every recorded correction, in the shape new labelled training data would take."""
        return {"items": service.export_corrections()}

    return app


if __name__ == "__main__":  # pragma: no cover
    # Ad-hoc smoke test: classify one sample ticket and print the decision, without needing
    # FastAPI/uvicorn running (useful for a quick `python -m app.main` sanity check).
    import json

    sample = {
        "ticket_id": "demo-1",
        "text": "The app shows a 500 error after login and I cannot continue.",
    }
    print(json.dumps(service.triage(_ticket_from_dict(sample)).to_dict(), indent=2))

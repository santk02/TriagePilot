# Architecture

TriagePilot is organized around a single canonical ticket payload that every input modality normalizes into before classification.

## Pipeline

1. Ingest raw text, screenshots, and voice notes.
2. Normalize each modality into a single text blob.
3. Pull live context from changelog, status, and known-issues sources when enabled.
4. Run the classifier multiple times and derive a confidence score from agreement.
5. Auto-route only when confidence clears the configured threshold.
6. Send low-confidence items to human review with the top guesses and samples.
7. Record corrections durably (`data/corrections.jsonl`) for future dataset expansion and calibration analysis.
8. Emit a per-stage trace event (ingest, live context, classify, route) for observability.

## Design notes

- The package is dependency-light so the core logic can be tested offline.
- The backend is intentionally swappable: the default is a keyword-based stand-in, but the confidence and routing layers do not depend on that detail.
- Calibration and coverage are tracked separately from raw label accuracy because selective prediction is the product goal.
- `TriageService` (`app/api.py`) is the orchestrator every transport wraps: it is transport-agnostic on purpose, so the same pipeline is exercised directly in tests and behind FastAPI.
- Corrections and traces are both append-only logs (JSONL for corrections, in-memory `MemoryTracer` for traces), so neither can silently overwrite prior data.


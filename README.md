# TriagePilot

Confidence-gated support triage that normalizes text, screenshots, and voice notes into one pipeline, classifies urgency and intent, and abstains to a human queue when confidence is too low.

## What is in this scaffold

- Shared ticket models and routing taxonomy
- Deterministic baseline and self-consistency classifier
- Multimodal normalization helpers
- Live-docs cache and fetch abstraction
- Feedback capture and export helpers
- Evaluation scripts for precision, recall, calibration, and threshold sweeps
- A FastAPI-compatible API factory with a safe fallback when FastAPI is not installed
- A browser dashboard at `/` for triage results and human review
- Unit tests that exercise the core decision logic

## Quick start

1. Create a Python 3.10+ environment.
2. Install dependencies from `requirements.txt`.
3. Run the tests:

```bash
python -m unittest discover -s tests -v
```

4. Generate the sample dataset:

```bash
python scripts/build_dataset.py
```

5. Run the evaluation:

```bash
python -m evaluation.run_eval
```

The evaluator uses deterministic 60/20/20 train-ish, calibration, and held-out
test slices. It selects the threshold from the calibration slice, reports
covered-slice precision on the held-out slice, and writes
`docs/images/calibration.png` and `docs/images/coverage_curve.png`.

## API

The API lives in `app/main.py`. If FastAPI is available, `create_app()` returns a real FastAPI app with:

- `GET /health`
- `POST /v1/triage`
- `GET /v1/queue`
- `POST /v1/corrections`
- `GET /v1/corrections/export`
- `GET /` (dashboard)

If FastAPI is missing, the core triage functions still work directly through the Python API.

## Notes

- `evaluation/labelled_tickets.json` is a six-row starter dataset, not the required 200+ hand-labelled evaluation set. The generator is deliberately marked as synthetic by its deterministic templates and must not be represented as hand-labelled data.
- The default classifier backend is deterministic and keyword-based so the scaffold is runnable without external model access.
- The code is structured so a real LLM backend can be dropped in later without changing the routing logic.


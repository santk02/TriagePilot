# TriagePilot

Confidence-gated support-ticket triage. Tickets (text, screenshot description, voice transcript) are normalised to one text blob, classified for urgency (P1–P4) and intent several times (self-consistency sampling), and auto-routed only when the agreement-based confidence clears a threshold; otherwise they go to a human queue with the top-2 guesses. Headless FastAPI JSON service — there is no bundled frontend.

The product spec is `TRIAGEPILOT_BLUEPRINT.md`; read it before changing behaviour. `README.md` lists known gaps between the blueprint and the code (keyword backend instead of an LLM, 6-row dataset, placeholder vision/audio, etc.).

## Tech stack

- Python 3.11 (CI and Dockerfile pin 3.11; code uses `slots=True` dataclasses and `X | Y` hints, so 3.10+ minimum)
- FastAPI + uvicorn (optional at import time — the pipeline works without them)
- Tests: stdlib `unittest` (pytest is installed but the suite is written for unittest)
- Optional: `matplotlib` for eval plots (falls back to a text dump if absent)
- Docker / docker compose for the container run; no database

## Commands

Run everything from the repo root (the eval scripts use root-relative paths).

```bash
pip install -r requirements.txt

python -m unittest discover -s tests -v          # unit tests
python -m unittest evaluation.deepeval_tests -v  # CI safety gate (must report >0 tests)
python -m evaluation.run_eval                    # baseline vs paper method, writes docs/images/*

uvicorn app.main:create_app --factory --reload   # run API on :8000
python -m app.main                               # one-ticket smoke test, no server needed
docker compose up --build                        # containerised run

python scripts/build_dataset.py                  # OVERWRITES evaluation/labelled_tickets.json with synthetic rows
```

CI (`.github/workflows/ci.yml`) runs the three test/eval commands above in that order. **There is no linter, formatter or type checker configured** — don't claim lint passed; run `python -m py_compile <files>` at minimum.

## Layout

- `app/main.py` — FastAPI factory + routes (`/health`, `/v1/triage`, `/v1/queue`, `/v1/traces`, `/v1/corrections`, `/v1/corrections/export`)
- `app/api.py` — `TriageService`: transport-agnostic orchestrator (ingest → live docs → classify → route → queue, plus corrections/traces). Tests drive this directly.
- `app/classify/` — `backend.py` (swappable `PredictionBackend` protocol + `KeywordBackend`), `paper_method.py` (self-consistency), `baseline.py`, `router.py` (the threshold gate)
- `app/taxonomy.py` is canonical for labels and `ROUTING`; `app/classify/taxonomy.py` is only a re-export shim
- `app/ingest/`, `app/context/`, `app/feedback/`, `app/observability/` — one concern each
- `evaluation/` — metrics, calibration, threshold sweep, `run_eval`, `deepeval_tests`
- Config: all via `TRIAGEPILOT_*` env vars read in `app/config.py` (`Settings` is a frozen dataclass); keep `.env.example` in sync when adding one

## Conventions

- Every module starts with `from __future__ import annotations`; full type hints; `snake_case` functions/modules, `PascalCase` classes, private helpers prefixed `_`.
- DTOs are `@dataclass(slots=True)` in `app/models.py`, each with `to_dict()`. API responses are `.to_dict()` output — keep that shape stable.
- Code is heavily commented: one-line trailing/inline comments on imports and logic blocks, a docstring on every class and function. Match that density in new code.
- Fail fast on bad config (`Settings.__post_init__` raises `ValueError`); the API turns `ValueError`/`KeyError` into 422.
- Degrade, don't crash: live-docs fetch failure returns `""`; missing matplotlib falls back to a text file.

## Invariants — don't break these

- The confidence gate is the product: below threshold → `human-review`, never a guess (`classify/router.py`).
- The routing threshold must be tuned on the **calibration** split, never the held-out test split (`evaluation/run_eval.py`).
- Every `(urgency, intent)` pair must exist in `ROUTING`; `validate_routing_map()` runs at import.
- Tests that touch corrections must pass a temp `Settings(corrections_path=...)` — the default `data/corrections.jsonl` is real, gitignored state and tests would pollute it.
- `evaluation/deepeval_tests.py` must stay a `unittest.TestCase`; a bare `test_*` function runs 0 tests under `python -m unittest` and silently disables the gate.
- Don't present synthetic data from `scripts/build_dataset.py` as hand-labelled evaluation data.

## More rules

Path-scoped rules in `.claude/rules/` load when you work on matching files:
- `testing.md`: unittest conventions, the CI safety gate, test isolation, determinism
- `evaluation.md`: split discipline, metrics, baseline comparisons, data honesty

Personal, machine-specific notes go in `CLAUDE.local.md` (gitignored).

## Git

Develop on the branch you're assigned; commits end with the session's `Co-Authored-By`/`Claude-Session` trailers. Don't open a PR unless asked.

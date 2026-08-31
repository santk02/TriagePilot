# TriagePilot

Confidence-gated support-ticket triage. TriagePilot normalizes text,
screenshots, and voice notes into one pipeline, classifies urgency and
intent, and — this is the whole product — **abstains to a human queue
whenever its confidence is too low to trust**. Auto-routing only the
tickets it can be confident about keeps precision high on the automated
slice instead of averaging good and bad decisions together.

> See [`TRIAGEPILOT_BLUEPRINT.md`](TRIAGEPILOT_BLUEPRINT.md) for the full
> product spec this repo implements, and [`PAPER_NOTES.md`](PAPER_NOTES.md)
> for the reproduced technique and what was simplified.

---

## Key Features

- **Self-consistency confidence.** Samples the classifier `k` times and uses
  the cross-sample agreement rate — not the model's self-reported certainty
  — as the confidence score (`app/classify/paper_method.py`).
- **Confidence-gated routing.** Above the threshold: auto-route to the
  owning team. Below it: abstain to a human queue with the model's top-2
  guesses attached, never a silent guess (`app/classify/router.py`).
- **Multimodal ingestion.** Text, a screenshot description, and a voice
  transcript all normalize into one tagged text blob before classification
  (`app/ingest/`), so one classifier and one eval set covers all three.
  Vision/audio backends are pluggable via injected OCR/transcript text; wire
  a real vision model or `faster-whisper` in without touching the pipeline.
- **Live docs context.** An optional, TTL-cached fetch of status/changelog/
  known-issues pages injected into the classifier prompt, so a ticket about
  something that shipped last week isn't triaged against stale context
  (`app/context/live_docs.py`).
- **Feedback loop.** Every human correction is appended to a durable JSONL
  log and exportable as new labelled training data
  (`app/feedback/corrections.py`, `GET /v1/corrections/export`).
- **Observability.** Every triage call emits per-stage trace events
  (ingest, live-context fetch, classify, route) with timing, exposed via
  `GET /v1/traces` (`app/observability/tracing.py`).
- **Evaluation suite.** Baseline-vs-paper-method comparison, a reliability
  (calibration) diagram, and the coverage-vs-precision threshold sweep that
  the routing threshold is chosen from — never guessed
  (`evaluation/`).
- **CI safety gate.** Dependency-free, DeepEval-compatible assertions that
  fail the build on unsafe routing (e.g. a P1 falling through the cracks)
  or on auto-routing below the confidence threshold.
- **Dashboard.** A single-page HTML UI (`app/dashboard.html`) for
  submitting tickets, viewing the decision, working the human-review queue,
  recording overrides, and inspecting pipeline traces — no frontend build.

---

## Repository Architecture

```
triagepilot/
├── README.md                    # you are here
├── TRIAGEPILOT_BLUEPRINT.md      # full product spec
├── PAPER_NOTES.md                # reproduced technique: claim, mechanism, what was simplified
├── ARCHITECTURE.md               # pipeline + design notes
├── EVALUATION.md                 # how the eval layers work, CI expectations
├── FAILURE_MODES.md              # known limitations and what to watch
├── .env.example                  # all configuration keys, with defaults
├── requirements.txt
├── docker-compose.yml
├── Dockerfile
│
├── .github/workflows/ci.yml      # lint-free CI: unit tests → CI safety gate → eval
│
├── app/
│   ├── main.py                   # FastAPI app factory: /health, /v1/triage, /v1/queue, ...
│   ├── api.py                    # TriageService: the transport-agnostic pipeline orchestrator
│   ├── config.py                 # Settings dataclass, loaded from environment variables
│   ├── models.py                 # shared DTOs (TicketInput, ClassificationResult, ...)
│   ├── taxonomy.py                # canonical urgency/intent labels + routing map
│   ├── prompts.py                 # LLM prompt construction (consumed by a real backend)
│   ├── dashboard.html             # single-page UI served at `/`
│   │
│   ├── ingest/                    # any input -> one normalized text blob
│   │   ├── text.py                # whitespace cleanup
│   │   ├── vision.py              # screenshot -> description (OCR passthrough today)
│   │   ├── audio.py               # voice note -> transcript (injected transcript today)
│   │   └── normalise.py           # merges all three into `[TEXT]/[SCREENSHOT]/[VOICE]`
│   │
│   ├── context/
│   │   └── live_docs.py           # TTL-cached live-docs fetch (Firecrawl-shaped interface)
│   │
│   ├── classify/
│   │   ├── taxonomy.py            # re-export shim -> app.taxonomy (kept for import compatibility)
│   │   ├── backend.py             # PredictionBackend protocol + default KeywordBackend
│   │   ├── paper_method.py        # ← the reproduced self-consistency technique
│   │   ├── baseline.py            # single-shot, no confidence — the comparison point
│   │   └── router.py              # the confidence threshold gate
│   │
│   ├── feedback/
│   │   └── corrections.py         # append/export the JSONL correction log
│   │
│   └── observability/
│       └── tracing.py             # MemoryTracer: per-ticket pipeline event trace
│
├── evaluation/
│   ├── labelled_tickets.json      # dataset (currently 6 seed rows — see "Known Gaps" below)
│   ├── metrics.py                 # precision/recall, accuracy, calibration binning, coverage
│   ├── calibration.py             # reliability diagram (predicted vs. observed accuracy)
│   ├── threshold_sweep.py         # coverage-vs-precision curve + threshold selection
│   ├── run_eval.py                # CLI: baseline vs. paper method, writes both plots
│   └── deepeval_tests.py          # CI safety gate (unittest.TestCase, DeepEval-compatible)
│
├── scripts/
│   └── build_dataset.py           # regenerates evaluation/labelled_tickets.json (synthetic filler)
│
└── tests/
    └── test_triagepilot.py        # unit coverage for the full pipeline
```

---

## Prerequisites & Environment Setup

- **Python 3.10+** (dataclasses use `slots=True`, `X | Y` union syntax is
  used throughout — 3.10 is the practical floor even though the Dockerfile
  pins 3.11).
- **Docker + Docker Compose** — optional, for the containerized run.
- No database, message queue, or external API key is required to run the
  scaffold as shipped: the default classifier backend is a deterministic,
  dependency-free keyword matcher, and live-docs fetching degrades
  gracefully to "no context" if unreachable.

---

## Installation & Dependency Setup

```bash
git clone <this-repo>
cd triagepilot

python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env           # then edit values as needed
```

`requirements.txt` currently installs `fastapi`, `uvicorn`, and `pytest` —
enough to run the API, the dashboard, and the test suite. `matplotlib` is
optional: the eval scripts detect its absence and fall back to writing a
plain-text dump of the plot data instead of a `.png` (see "Known Gaps").

---

## Usage

### Run the tests

```bash
python -m unittest discover -s tests -v
python -m unittest evaluation.deepeval_tests -v
```

### Run the API + dashboard

```bash
uvicorn app.main:create_app --factory --reload
# → dashboard at http://localhost:8000/
# → health check at http://localhost:8000/health
```

Or with Docker Compose (persists the correction log in a named volume):

```bash
docker compose up --build
```

### API examples

**Classify a ticket:**

```bash
curl -X POST http://localhost:8000/v1/triage \
  -H "Content-Type: application/json" \
  -d '{
        "ticket_id": "t-1042",
        "text": "The dashboard shows a 500 error whenever I open the reports page.",
        "metadata": {}
      }'
```

```json
{
  "ticket_id": "t-1042",
  "urgency": "P2",
  "intent": "bug",
  "route": "eng-triage",
  "confidence": 0.64,
  "threshold": 0.72,
  "action": "human-review",
  "reason": "confidence 0.640 is below threshold 0.720; top guesses: bug, access",
  "runner_up": "access",
  "top_guesses": ["bug", "access"],
  "samples": ["... k sample predictions, kept for the audit trail ..."]
}
```

**Submit a ticket with a screenshot and a voice note:**

```bash
curl -X POST http://localhost:8000/v1/triage \
  -H "Content-Type: application/json" \
  -d '{
        "ticket_id": "t-1043",
        "text": "Cannot check out.",
        "screenshot_text": "screenshot-ref-1",
        "voice_transcript": "voice-ref-1",
        "metadata": {
          "ocr_text": "Error 402: Payment declined",
          "voice_transcript": "I tried three times and it keeps failing at checkout."
        }
      }'
```

**Work the human queue:**

```bash
curl http://localhost:8000/v1/queue
```

**Record a human override (feeds the feedback loop):**

```bash
curl -X POST http://localhost:8000/v1/corrections \
  -H "Content-Type: application/json" \
  -d '{
        "ticket_id": "t-1042",
        "predicted_urgency": "P2",
        "predicted_intent": "bug",
        "corrected_urgency": "P1",
        "corrected_intent": "outage",
        "confidence": 0.64,
        "comment": "This was actually a platform-wide outage."
      }'
```

**Export corrections as new labelled training data:**

```bash
curl http://localhost:8000/v1/corrections/export
```

**Inspect pipeline traces (per-stage timing):**

```bash
curl http://localhost:8000/v1/traces
```

### Run the evaluation suite

```bash
python -m evaluation.run_eval
```

Prints baseline vs. paper-method accuracy, the threshold chosen from the
calibration split, held-out coverage/precision, and per-label
precision/recall — then writes `docs/images/calibration.png` and
`docs/images/coverage_curve.png` (or a text fallback if `matplotlib` isn't
installed).

### Regenerate the dataset (synthetic filler only — see "Known Gaps")

```bash
python scripts/build_dataset.py
```

### Use the pipeline directly, without HTTP

```python
from app.api import TriageService
from app.config import Settings
from app.models import TicketInput

service = TriageService(Settings(threshold=0.72, sample_count=5))
result = service.triage(TicketInput(ticket_id="demo-1", text="The site is down."))
print(result.action, result.route, result.confidence)
```

---

## Environment Variables & Configuration

All configuration is read by `app/config.py::load_settings()`; see
[`.env.example`](.env.example) for the full list with defaults:

| Variable | Default | Meaning |
|---|---|---|
| `TRIAGEPILOT_THRESHOLD` | `0.72` | Confidence cutoff: at/above → auto-route, below → human review |
| `TRIAGEPILOT_SAMPLE_COUNT` | `5` | `k`: number of self-consistency samples drawn per ticket |
| `TRIAGEPILOT_LIVE_DOCS_TTL` | `900` | Cache TTL (seconds) for live-docs fetches |
| `TRIAGEPILOT_HUMAN_QUEUE` | `human-queue` | Route name used when a ticket abstains to a human |
| `TRIAGEPILOT_DEFAULT_ROUTE` | `human-queue` | Fallback route for an (urgency, intent) pair missing from the routing map |
| `TRIAGEPILOT_MODEL_NAME` | `keyword-self-consistency` | Label recorded on results, identifying the active backend |
| `TRIAGEPILOT_USE_LIVE_CONTEXT` | `1` | Whether to fetch/inject live-docs context before classifying (`0` disables it) |
| `TRIAGEPILOT_CORRECTIONS_PATH` | `data/corrections.jsonl` | Where the durable human-correction log is written |

Copy `.env.example` to `.env` and adjust; `docker-compose.yml` sets a
subset of these directly as container environment variables and mounts a
named volume at `/app/data` so the correction log survives restarts.

---

## Troubleshooting & Edge Cases

- **`RuntimeError: FastAPI is not installed.`** — `create_app()` requires
  `fastapi`/`uvicorn`. Install `requirements.txt`, or use `TriageService`
  directly (see "Use the pipeline directly" above) if you only need the
  classification logic.
- **Evaluation numbers look too good/too small to be meaningful.**
  `evaluation/labelled_tickets.json` ships with only the 6 hand-written
  seed rows in `scripts/build_dataset.py`, not the 200+ hand-labelled,
  class-imbalanced dataset the blueprint requires — see "Known Gaps"
  below. Every metric printed by `run_eval.py` is illustrative until a
  real dataset is supplied.
- **`docs/images/*.png` not appearing.** If `matplotlib` isn't installed,
  `calibration.py`/`threshold_sweep.py` write a plain-text dump of the row
  data to the same path instead of failing. Install `matplotlib` to get
  real plots.
- **Live-docs context is always empty.** The default `LiveDocsClient`
  points at placeholder `https://example.com/...` URLs. Point
  `LiveDocsClient(sources=...)` at your product's real status/changelog/
  known-issues pages (or inject a Firecrawl-backed `fetcher`) before
  relying on this signal. A fetch failure degrades to no context rather
  than raising, by design (see `FAILURE_MODES.md`).
- **Vision/audio "classification" looks like it's just echoing input.**
  `ingest/vision.py` and `ingest/audio.py` are dependency-free stand-ins
  that prefer pre-computed OCR text / transcripts (via
  `TicketInput.metadata`). Wire a real vision-capable model and
  `faster-whisper` in their place to complete multimodal ingestion per the
  blueprint.
- **Corrections/traces reset between requests in tests.** `TriageService`
  reads/writes `corrections_path` from disk on every call, so pass a
  temp-directory path via `Settings(corrections_path=...)` in tests to
  avoid interference between runs (see `tests/test_triagepilot.py`).
- **A P1 ticket doesn't auto-route even though it's clearly urgent.**
  This is intentional: urgency alone doesn't grant confidence. Joint
  confidence requires the intent to agree across samples too. If P1
  recall in `evaluation/run_eval.py`'s per-label output looks low, that's
  the signal to investigate the backend/prompt, not the routing gate.

---

## Known Gaps (Blueprint vs. Current Code)

This scaffold implements the full pipeline shape from
`TRIAGEPILOT_BLUEPRINT.md`, but several pieces are explicitly simplified
placeholders rather than the production-grade choices the blueprint's tech
stack lists. These are documented here (and in `PAPER_NOTES.md` /
`FAILURE_MODES.md`) rather than silently glossed over:

| Blueprint requirement | Current state |
|---|---|
| LLM-backed classifier (Claude via LiteLLM) | Deterministic `KeywordBackend`; `PredictionBackend` protocol makes swapping in a real LLM call a drop-in change |
| Vision model for screenshots, `faster-whisper` for audio | Both `ingest/vision.py` and `ingest/audio.py` pass through pre-supplied OCR text/transcripts instead of calling a real model |
| Firecrawl live-docs | `LiveDocsClient` uses a plain `urlopen` fetch against placeholder URLs; the cache/TTL/context-building logic is production-shaped, only the fetcher needs swapping |
| PostgreSQL storage | Corrections persist to a JSONL file (`data/corrections.jsonl`); tickets/predictions are not persisted beyond the in-memory human queue for the process lifetime |
| Langfuse tracing | `MemoryTracer` records per-stage timing in-process, exposed via `GET /v1/traces`; not exported to an external tracing backend |
| Open WebUI / dashboard | A dependency-free single-page HTML dashboard (`app/dashboard.html`) is included instead |
| 200+ hand-labelled tickets, 60/20/20 split, license documented | `evaluation/labelled_tickets.json` ships with 6 hand-written seed rows only; `scripts/build_dataset.py` can pad it with clearly-synthetic template rows, but this must not be reported as the hand-labelled evaluation set |
| ~30 screenshot + ~20 voice-note tickets in the dataset | Not yet present; the dataset has no multimodal rows |
| DeepEval library integration | `evaluation/deepeval_tests.py` provides dependency-free assertions with the same shape a DeepEval `GEval` metric would wrap |

### Bugs found and fixed during this audit

- **CI never ran the safety assertions.** `evaluation/deepeval_tests.py`
  defined a bare `test_deepeval_assertions()` function; CI invokes
  `python -m unittest evaluation.deepeval_tests`, and `unittest`'s module
  discovery only finds `TestCase` subclasses, so this silently reported
  "Ran 0 tests" and never executed. Fixed by wrapping the assertions in a
  `unittest.TestCase`.
- **`TRIAGEPILOT_DEFAULT_ROUTE` / `Settings.default_route` was dead
  configuration** — read from the environment and stored, but never
  passed to anything. `route_for()` now accepts a `default` parameter, and
  `TriageService`/`classify_with_confidence` thread `settings.default_route`
  through to it.
- **`KeywordBackend`'s RNG made unrelated ambiguous tickets identical.**
  It seeded `random.Random(seed=7)` fresh on every call, so two different
  low-signal tickets classified in the same process always drew the exact
  same "random" label sequence. Fixed by deriving the seed from a hash of
  the ticket text (stable per ticket, distinct across tickets) while still
  advancing the same RNG across a ticket's `k` samples so self-consistency
  sampling still produces real disagreement.
- **Human corrections and pipeline observability were dead code paths.**
  `app/feedback/corrections.py` (JSONL persistence) and
  `app/observability/tracing.py` (`MemoryTracer`) existed and were unit
  tested in isolation, but `TriageService`/`app/main.py` never called
  them — corrections lived only in an in-memory list (lost on restart) and
  no trace events were ever recorded. Both are now wired into
  `TriageService.triage()`/`record_correction()`, with a new
  `GET /v1/traces` endpoint and a dashboard panel to view them.
- **Unused imports** (`route_prediction` in `evaluation/run_eval.py`,
  `TicketInput` in `evaluation/deepeval_tests.py`) removed.
- **Verbose `model_name` derivation** in
  `classify_ticket_with_confidence` (`getattr(backend, "__class__", ...)`
  with an unreachable fallback) simplified to `type(backend).__name__`.

None of these required behavioral trade-offs against the blueprint's
design rule — the confidence gate, the abstain-to-human path, and the
calibration/coverage evaluation methodology were already correctly
implemented and are unchanged by this audit.

---

## License

See the repository's `LICENSE` file. If you replace
`evaluation/labelled_tickets.json` with a real dataset, record its
source/license here per blueprint section 8.

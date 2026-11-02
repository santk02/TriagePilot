---
paths:
  - "tests/**"
  - "evaluation/deepeval_tests.py"
---

# Testing rules

## Framework

- Tests use stdlib `unittest`. Write `unittest.TestCase` classes with `test_*` methods and `self.assert*` calls. pytest is listed in `requirements.txt` but nothing depends on it, and CI never invokes it.
- Every test method gets a one-line docstring stating the behaviour it pins down (see `tests/test_triagepilot.py`).

## Running

```bash
python -m unittest discover -s tests -v
python -m unittest evaluation.deepeval_tests -v
```

Run both before you finish. Read the `Ran N tests` line, not just `OK`: `OK` with `Ran 0 tests` means discovery silently found nothing.

## The CI safety gate (`evaluation/deepeval_tests.py`)

- Assertions there must live in a `unittest.TestCase` subclass. `python -m unittest <module>` only discovers `TestCase` subclasses, so a module-level `def test_*()` reports `Ran 0 tests` / `OK` and the gate never runs. This already happened once in this repo.
- The gate encodes product safety, not code coverage: an obvious outage must classify P1 and resolve to `sre-oncall` or the human queue, and anything below threshold must abstain. Never loosen these to make a change pass. If a change legitimately alters routing, update the assertion and say why in the commit.

## Isolation

- Anything that records corrections must pass a temp path:
  `Settings(corrections_path=str(Path(tmp) / "corrections.jsonl"))` inside `tempfile.TemporaryDirectory()`. The default `data/corrections.jsonl` is real, persistent state; writing to it makes tests order-dependent and pollutes the log.
- Pass `Settings(use_live_context=False)` unless the test is about live docs. Otherwise `TriageService` attempts real HTTP fetches to the configured URLs.
- For live-docs tests, inject `fetcher=` and `cache=MemoryCache(...)` into `LiveDocsClient`; don't hit the network.
- Test `TriageService` (`app/api.py`) directly rather than through HTTP. The FastAPI layer in `app/main.py` is a thin wrapper, and FastAPI is an optional dependency.

## Determinism

- `KeywordBackend` seeds its RNG from a hash of the ticket text, so the same ticket always yields the same samples. Assert exact labels only for strong-signal tickets (outage/`503`, `crash`, `refund`, `login`). Ambiguous text ("Please help.") draws from priors, so assert membership (`assertIn(result.urgency, URGENCY)`) or force the outcome with the threshold (`threshold=0.99` guarantees `human-review`).
- Don't assert on `created_at` or trace `duration_ms`; they're wall-clock values.

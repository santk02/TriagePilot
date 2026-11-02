---
paths:
  - "evaluation/**"
  - "scripts/build_dataset.py"
  - "app/classify/**"
  - "PAPER_NOTES.md"
  - "EVALUATION.md"
---

# Evaluation rules

Evaluation is the evidence for the project's central claim: confidence-gated routing keeps precision high on the auto-routed slice. Numbers produced carelessly here are worse than no numbers.

## Splits

- `split_dataset()` in `evaluation/run_eval.py` is a deterministic 60/20/20 train-ish / calibration / held-out test split. Keep it deterministic; don't shuffle without a fixed seed.
- **Choose the threshold on the calibration split only.** `choose_threshold()` must be fed `sweep_thresholds()` output computed from calibration rows. Test-split metrics are reported at that fixed threshold and never fed back into choosing it. Tuning on test inflates every reported number.
- The test-split sweep in `main()` exists only to draw `docs/images/coverage_curve.png`; never pass it to `choose_threshold()`.

## Metrics

- Headline numbers are **coverage** (fraction auto-routed) and **precision on the covered slice** (`coverage_and_precision` in `evaluation/metrics.py`), not overall accuracy.
- Report P1 recall separately. A missed P1 is the costliest failure; an improvement in average accuracy that lowers P1 recall is a regression.
- `choose_threshold()` returns `1.0` (route nothing automatically) when no threshold meets the precision target. That's the fail-safe; don't change it to a "best available" threshold.
- Confidence is `(urgency agreement) × (intent agreement)` in `app/classify/paper_method.py`. Both axes must agree. Don't swap in a model's self-reported confidence; the blueprint's whole argument is that sampling agreement calibrates better.

## Comparisons

- Any claim that the paper method beats the baseline must use the same test rows for both (`baseline.classify` vs `classify_with_confidence`).
- When you add a component (live context, a new backend), measure the eval with and without it. If it doesn't help, say so in `EVALUATION.md`; a null result is still a result.

## Data honesty

- `evaluation/labelled_tickets.json` currently holds 6 hand-written seed rows. Every metric `run_eval` prints is illustrative until a real hand-labelled 200+ ticket dataset is supplied. Say so whenever you quote a number.
- `scripts/build_dataset.py` writes template-cycled **synthetic** rows and overwrites the dataset file. Don't run it over a real dataset, and never describe its output as hand-labelled.
- If you add a real dataset, record its source and licence in `README.md`.

## Running

```bash
python -m evaluation.run_eval   # from repo root; paths are root-relative
```

Without `matplotlib`, the plot writers fall back to a text dump at the `.png` path. That's expected; don't treat it as an error.

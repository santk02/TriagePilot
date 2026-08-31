# Evaluation

This repo includes three evaluation layers:

1. Baseline comparison
2. Calibration analysis
3. Threshold sweep analysis

## Baseline comparison

`evaluation/run_eval.py` compares the one-shot baseline against the confidence-gated method.

## Calibration

`evaluation/calibration.py` bins predictions by confidence and can emit a reliability plot when matplotlib is available.

## Threshold sweep

`evaluation/threshold_sweep.py` computes coverage and precision across thresholds so the routing cutoff can be selected from data instead of intuition.

`evaluation.run_eval` keeps the calibration split separate from the held-out
test split and writes the reliability and coverage plots. The current checked-in
dataset has only six starter rows, so its metrics are illustrative until a
licensed, hand-labelled 200+ ticket dataset is supplied.

## CI expectation

The CI gate runs unit tests, dependency-free DeepEval-compatible assertions, and
the split-aware evaluation command. Unsafe routing and low-confidence
abstention failures fail the build.

`evaluation/deepeval_tests.py` wraps its assertions in a `unittest.TestCase`
(`DeepEvalAssertions`) so `python -m unittest evaluation.deepeval_tests`
actually discovers and runs them — a bare `test_*` function is invisible to
`unittest`'s module discovery, which meant these safety checks previously
reported "Ran 0 tests" and never executed. Confirm any future edit to this
file still shows a non-zero test count when run directly.


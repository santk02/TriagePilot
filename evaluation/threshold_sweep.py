from __future__ import annotations  # allow forward-referenced type hints on older Python

from pathlib import Path  # output path for the saved plot
from typing import List, Sequence  # type hints

from .metrics import coverage_and_precision  # coverage/precision at one fixed threshold


def sweep_thresholds(
    y_true: Sequence[str], y_pred: Sequence[str], confidences: Sequence[float]
) -> List[dict]:
    """Compute coverage and precision at every threshold from 0.00 to 1.00 in 0.01 steps — this
    is the headline coverage-vs-precision curve the blueprint calls for."""
    if len(y_true) != len(y_pred) or len(y_true) != len(confidences):
        raise ValueError("labels and confidences must have the same length")
    rows: List[dict] = []
    for index in range(0, 101):
        threshold = index / 100
        covered = [confidence >= threshold for confidence in confidences]
        stats = coverage_and_precision(y_true, y_pred, covered)
        rows.append({"threshold": threshold, **stats})
    return rows


def choose_threshold(rows: Sequence[dict], minimum_precision: float = 0.95) -> float:
    """Choose the highest-coverage threshold that still meets `minimum_precision` — the threshold
    is a product decision read off the curve, not guessed (must be run on the calibration split,
    never the held-out test split, or the reported test numbers become inflated)."""
    eligible = [
        row
        for row in rows
        if row["precision"] >= minimum_precision and row["covered_count"] > 0
    ]
    if not eligible:
        # No threshold reaches the target precision on this data: fail safe by routing nothing
        # automatically (threshold = 1.0) rather than silently picking an unsafe cutoff.
        return 1.0
    return max(eligible, key=lambda row: (row["coverage"], -row["threshold"]))[
        "threshold"
    ]


def write_plot(rows: Sequence[dict], out_path: str | Path) -> None:
    """Render coverage and precision against threshold as a PNG via matplotlib, or fall back to a
    plain-text dump if matplotlib isn't installed."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import matplotlib.pyplot as plt  # type: ignore
    except Exception:
        out_path.write_text("\n".join(str(row) for row in rows), encoding="utf-8")
        return

    xs = [row["threshold"] for row in rows]
    precision = [row["precision"] for row in rows]
    coverage = [row["coverage"] for row in rows]
    plt.figure(figsize=(7, 4))
    plt.plot(xs, precision, label="precision")
    plt.plot(xs, coverage, label="coverage")
    plt.xlabel("Threshold")
    plt.ylabel("Score")
    plt.title("Coverage vs precision")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()

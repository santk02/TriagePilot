from __future__ import annotations

from pathlib import Path
from typing import List, Sequence

from .metrics import coverage_and_precision


def sweep_thresholds(
    y_true: Sequence[str], y_pred: Sequence[str], confidences: Sequence[float]
) -> List[dict]:
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
    """Choose the highest-coverage threshold meeting the business precision target."""
    eligible = [
        row
        for row in rows
        if row["precision"] >= minimum_precision and row["covered_count"] > 0
    ]
    if not eligible:
        return 1.0
    return max(eligible, key=lambda row: (row["coverage"], -row["threshold"]))[
        "threshold"
    ]


def write_plot(rows: Sequence[dict], out_path: str | Path) -> None:
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

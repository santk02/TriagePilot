from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Sequence

from app.classify.baseline import classify as baseline_classify
from app.classify.paper_method import classify_with_confidence
from app.classify.router import route_prediction

from .calibration import write_calibration_plot
from .metrics import accuracy, coverage_and_precision, precision_recall_by_label
from .threshold_sweep import choose_threshold, sweep_thresholds, write_plot

DATASET_PATH = Path("evaluation/labelled_tickets.json")


def load_dataset(path: Path = DATASET_PATH) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def split_dataset(
    dataset: Sequence[Dict[str, Any]],
) -> tuple[List[dict], List[dict], List[dict]]:
    """Deterministically return train-ish, calibration, and held-out test splits."""
    rows = list(dataset)
    first = int(len(rows) * 0.6)
    second = int(len(rows) * 0.8)
    return rows[:first], rows[first:second], rows[second:]


def evaluate_rows(
    rows: Sequence[Dict[str, Any]],
) -> tuple[List[str], List[str], List[float]]:
    true_labels = [str(row["urgency"]) for row in rows]
    predictions = [classify_with_confidence(row["text"]) for row in rows]
    return (
        true_labels,
        [str(row["urgency"]) for row in predictions],
        [float(row["confidence"]) for row in predictions],
    )


def main() -> None:
    dataset = load_dataset()
    _, calibration_rows, test_rows = split_dataset(dataset)
    calibration_true, calibration_pred, calibration_confidences = evaluate_rows(
        calibration_rows
    )
    true_labels, paper_pred, paper_confidences = evaluate_rows(test_rows)

    baseline_pred = [baseline_classify(row["text"])["urgency"] for row in test_rows]
    calibration_sweep = sweep_thresholds(
        calibration_true, calibration_pred, calibration_confidences
    )
    threshold = choose_threshold(calibration_sweep)
    covered = [confidence >= threshold for confidence in paper_confidences]
    coverage_stats = coverage_and_precision(true_labels, paper_pred, covered)

    print("Baseline urgency accuracy:", round(accuracy(true_labels, baseline_pred), 3))
    print("Paper-method urgency accuracy:", round(accuracy(true_labels, paper_pred), 3))
    print("Selected threshold (calibration split):", round(threshold, 2))
    print("Auto-route coverage (held-out test):", round(coverage_stats["coverage"], 3))
    print(
        "Covered-slice precision (held-out test):",
        round(coverage_stats["precision"], 3),
    )

    for row in precision_recall_by_label(true_labels, paper_pred):
        print(
            f"{row.label}: precision={row.precision:.3f} recall={row.recall:.3f} support={row.support}"
        )

    output_dir = Path("docs/images")
    write_calibration_plot(
        list(zip(paper_confidences, [t == p for t, p in zip(true_labels, paper_pred)])),
        output_dir / "calibration.png",
    )
    write_plot(
        sweep_thresholds(true_labels, paper_pred, paper_confidences),
        output_dir / "coverage_curve.png",
    )


if __name__ == "__main__":  # pragma: no cover
    main()

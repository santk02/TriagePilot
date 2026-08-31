from __future__ import annotations  # allow forward-referenced type hints on older Python

from collections import Counter, defaultdict  # tallying helpers for binning/label counts
from dataclasses import dataclass  # typed per-label metric row
from typing import Dict, Iterable, List, Sequence, Tuple  # shared type hints


@dataclass(frozen=True)
class MetricRow:
    """Precision/recall/support for one label, as used in the per-class results table."""

    label: str
    precision: float
    recall: float
    support: int


def precision_recall_by_label(
    y_true: Sequence[str], y_pred: Sequence[str]
) -> List[MetricRow]:
    """Compute per-label precision/recall/support across every label seen in truth or predictions."""
    if len(y_true) != len(y_pred):
        raise ValueError("y_true and y_pred must have the same length")
    labels = sorted(set(y_true) | set(y_pred))
    rows: List[MetricRow] = []
    for label in labels:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == label and p == label)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != label and p == label)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == label and p != label)
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        support = sum(1 for value in y_true if value == label)
        rows.append(
            MetricRow(label=label, precision=precision, recall=recall, support=support)
        )
    return rows


def accuracy(y_true: Sequence[str], y_pred: Sequence[str]) -> float:
    """Fraction of predictions that exactly match the ground truth (0.0 for an empty input)."""
    if not y_true:
        return 0.0
    return sum(1 for t, p in zip(y_true, y_pred) if t == p) / len(y_true)


def bin_calibration(
    predictions: Sequence[Tuple[float, bool]], bin_size: float = 0.2
) -> List[Dict[str, float]]:
    """Bucket (confidence, was_correct) pairs into fixed-width confidence bins and compute observed
    accuracy per bin — the data behind the reliability diagram (`calibration.py`). A well-calibrated
    system has `observed` close to `predicted` (the bin midpoint) in every bucket."""
    bins: Dict[int, List[bool]] = defaultdict(list)
    for confidence, correct in predictions:
        index = min(int(confidence / bin_size), int(1 / bin_size) - 1)
        bins[index].append(correct)
    rows = []
    total_bins = int(1 / bin_size)
    for index in range(total_bins):
        values = bins.get(index, [])
        lower = index * bin_size
        upper = lower + bin_size
        observed = sum(1 for value in values if value) / len(values) if values else 0.0
        rows.append(
            {
                "bin_lower": lower,
                "bin_upper": upper,
                "predicted": lower + bin_size / 2,  # bin midpoint, used as the x-axis value
                "observed": observed,
                "count": float(len(values)),
            }
        )
    return rows


def coverage_and_precision(
    y_true: Sequence[str], y_pred: Sequence[str], covered: Sequence[bool]
) -> Dict[str, float]:
    """Given a boolean "was this ticket auto-routed" mask, compute coverage (fraction auto-routed)
    and precision on just that covered slice — the two numbers the threshold sweep trades off."""
    if len(y_true) != len(y_pred) or len(y_true) != len(covered):
        raise ValueError("y_true, y_pred, and covered must have the same length")
    covered_pairs = [(t, p) for t, p, c in zip(y_true, y_pred, covered) if c]
    if not covered_pairs:
        return {"coverage": 0.0, "precision": 0.0, "covered_count": 0.0}
    total = len(y_true)
    covered_count = len(covered_pairs)
    precision = sum(1 for t, p in covered_pairs if t == p) / covered_count
    return {
        "coverage": covered_count / total if total else 0.0,
        "precision": precision,
        "covered_count": float(covered_count),
    }

from __future__ import annotations  # allow forward-referenced type hints on older Python

from pathlib import Path  # output path for the saved plot
from typing import List, Sequence, Tuple  # type hints

from .metrics import bin_calibration  # confidence-bucketing logic shared with threshold_sweep


def build_reliability_rows(predictions: Sequence[Tuple[float, bool]]) -> List[dict]:
    """Bucket (confidence, was_correct) pairs into the rows a reliability diagram plots."""
    return bin_calibration(predictions)


def write_calibration_plot(
    predictions: Sequence[Tuple[float, bool]], out_path: str | Path
) -> None:
    """Bucket predictions by confidence and render the reliability diagram to `out_path`.

    A well-calibrated system sits on the y=x diagonal: predicted confidence equals observed
    accuracy. This is the headline evidence that sampling agreement (not self-reported confidence)
    is a trustworthy signal (see PAPER_NOTES.md).
    """
    write_plot(build_reliability_rows(predictions), out_path)


def write_plot(rows: Sequence[dict], out_path: str | Path) -> None:
    """Render `rows` (predicted vs observed) as a PNG via matplotlib, or fall back to a plain-text
    dump if matplotlib isn't installed — so evaluation never hard-fails on a missing plotting dep."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import matplotlib.pyplot as plt  # type: ignore
    except Exception:
        out_path.write_text("\n".join(str(row) for row in rows), encoding="utf-8")
        return

    xs = [row["predicted"] for row in rows]
    ys = [row["observed"] for row in rows]
    plt.figure(figsize=(5, 5))
    plt.plot([0, 1], [0, 1], linestyle="--", color="gray")  # the perfect-calibration reference line
    plt.plot(xs, ys, marker="o")  # the actual reliability curve
    plt.xlabel("Predicted confidence")
    plt.ylabel("Observed accuracy")
    plt.title("Reliability diagram")
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()

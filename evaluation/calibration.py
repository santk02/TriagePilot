from __future__ import annotations

from pathlib import Path
from typing import List, Sequence, Tuple

from .metrics import bin_calibration


def build_reliability_rows(predictions: Sequence[Tuple[float, bool]]) -> List[dict]:
    return bin_calibration(predictions)


def write_calibration_plot(
    predictions: Sequence[Tuple[float, bool]], out_path: str | Path
) -> None:
    write_plot(build_reliability_rows(predictions), out_path)


def write_plot(rows: Sequence[dict], out_path: str | Path) -> None:
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
    plt.plot([0, 1], [0, 1], linestyle="--", color="gray")
    plt.plot(xs, ys, marker="o")
    plt.xlabel("Predicted confidence")
    plt.ylabel("Observed accuracy")
    plt.title("Reliability diagram")
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()

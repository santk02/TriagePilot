from __future__ import annotations  # allow forward-referenced type hints on older Python

import json  # JSONL (one JSON object per line) is the on-disk correction log format
from dataclasses import asdict  # (unused directly here, kept for parity with CorrectionRecord.to_dict)
from pathlib import Path  # filesystem path handling for the log file
from typing import Iterable, List  # type hints

from ..models import CorrectionRecord  # the record shape being persisted


def record_correction(path: str | Path, correction: CorrectionRecord) -> None:
    """Append one human correction to the JSONL log at `path`, creating parent directories as
    needed. Append-only by design: it's a durable audit trail of every override, not just the
    latest one, which is what makes it reusable as new labelled training data (blueprint Phase 5).
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(correction.to_dict(), ensure_ascii=True) + "\n")


def export_corrections(path: str | Path) -> List[dict]:
    """Read back every correction recorded at `path` as a list of plain dicts (the format
    `GET /v1/corrections/export` returns). Returns an empty list if the log doesn't exist yet."""
    path = Path(path)
    if not path.exists():
        return []
    rows: List[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:  # skip blank lines rather than failing json.loads on them
                rows.append(json.loads(line))
    return rows

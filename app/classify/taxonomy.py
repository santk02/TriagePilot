from __future__ import annotations  # allow forward-referenced type hints on older Python

# Backward-compatible re-export shim: the canonical taxonomy now lives at `app.taxonomy`
# (shared by ingest/eval/scripts code that must not import through the `classify` package).
# Anything importing `app.classify.taxonomy` keeps working unchanged.
from ..taxonomy import DEFAULT_ROUTE, INTENT, ROUTING, URGENCY, all_labels, route_for, validate_routing_map

__all__ = [
    "DEFAULT_ROUTE",
    "INTENT",
    "ROUTING",
    "URGENCY",
    "all_labels",
    "route_for",
    "validate_routing_map",
]

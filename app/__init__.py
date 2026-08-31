"""TriagePilot application package."""

# Re-export the most commonly used config/DTO/taxonomy symbols at the package root, so callers
# can `from app import Settings, TicketInput, ...` instead of reaching into submodules.
from .config import Settings, load_settings
from .models import (
    ClassificationResult,
    CorrectionRecord,
    NormalizedTicket,
    SamplePrediction,
    TicketInput,
)
from .taxonomy import INTENT, ROUTING, URGENCY

__all__ = [
    "ClassificationResult",
    "CorrectionRecord",
    "INTENT",
    "NormalizedTicket",
    "ROUTING",
    "SamplePrediction",
    "Settings",
    "TicketInput",
    "URGENCY",
    "load_settings",
]


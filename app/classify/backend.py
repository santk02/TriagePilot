from __future__ import annotations  # allow forward-referenced type hints on older Python

import random  # deterministic pseudo-random tie-breaking for the keyword backend
import zlib  # cheap, stable string hash for per-ticket RNG seeding (stable across process restarts)
from dataclasses import dataclass, field  # lightweight backend config container
from typing import Optional, Protocol  # structural typing so real LLM backends can be swapped in

from ..models import SamplePrediction  # one k-sample vote
from ..taxonomy import INTENT, URGENCY, route_for  # label sets + routing lookup


class PredictionBackend(Protocol):
    """Interface every classifier backend must satisfy (the default is `KeywordBackend`;
    a real deployment swaps this for an LLM call via LiteLLM without touching the caller)."""

    def predict(self, text: str, live_context: str = "") -> SamplePrediction:
        ...


@dataclass
class KeywordBackend:
    """Deterministic, dependency-free stand-in classifier used until a real LLM backend is wired in.

    Scores tickets by keyword match; ambiguous tickets (score <= 1) fall back to a weighted random
    draw so that repeated sampling (k > 1) produces the disagreement the self-consistency method
    needs to measure. The RNG is reseeded per call from a hash of the ticket text, so results are
    reproducible for the same ticket but vary across different tickets (see `predict`)."""

    seed: int = 7  # base seed; combined with the ticket text hash for per-ticket reproducibility
    _rng: Optional[random.Random] = field(default=None, repr=False, compare=False)  # lazily seeded, then advanced across the k calls for one ticket

    def predict(self, text: str, live_context: str = "") -> SamplePrediction:
        source = f"{text}\n{live_context}".lower()
        if self._rng is None:
            # Seed deterministically from the ticket content on first use, so identical tickets
            # always reproduce the same sample sequence while distinct tickets diverge. The RNG
            # is then kept and advanced across the remaining k-1 calls so samples for the SAME
            # ticket still differ from each other (that disagreement is the confidence signal).
            self._rng = random.Random(self.seed ^ zlib.crc32(source.encode("utf-8", "ignore")))
        rng = self._rng
        score = 0
        urgency = "P4"
        intent = "howto"

        # Highest-severity signal first: outage/incident language wins outright.
        if any(token in source for token in ("down", "outage", "incident", "503", "500")):
            urgency = "P1"
            intent = "outage"
            score = 3
        elif any(token in source for token in ("crash", "broken", "error", "fails", "cannot", "can't")):
            urgency = "P2"
            intent = "bug"
            score = 2
        elif any(token in source for token in ("refund", "invoice", "charge", "billing", "payment")):
            urgency = "P3"
            intent = "billing"
            score = 2
        elif any(token in source for token in ("login", "password", "2fa", "permission", "access")):
            urgency = "P2"
            intent = "access"
            score = 2
        elif any(token in source for token in ("feature request", "would like", "add support")):
            urgency = "P4"
            intent = "feature"
            score = 1

        if "how do i" in source or "how to" in source:
            intent = "howto"
            score = max(score, 1)

        if score <= 1:
            # No strong keyword signal: sample from the taxonomy's realistic class-imbalanced priors
            # instead of guessing. This is what produces genuine disagreement across k samples for
            # ambiguous tickets, which is exactly what should trigger abstention downstream.
            urgency = rng.choices(
                population=list(URGENCY),
                weights=[0.08, 0.2, 0.27, 0.45],
                k=1,
            )[0]
            intent = rng.choices(
                population=list(INTENT),
                weights=[0.18, 0.15, 0.22, 0.17, 0.15, 0.13],
                k=1,
            )[0]
        elif score == 2 and rng.random() < 0.2:
            # Moderate-signal tickets occasionally waver between two plausible severities.
            urgency = rng.choice(["P2", "P3"])
        elif score >= 3 and rng.random() < 0.05:
            # Even strong-signal tickets rarely flip intent, to keep confidence < 1.0 realistic.
            intent = rng.choice(["bug", "access", "billing"])

        return SamplePrediction(
            urgency=urgency,
            intent=intent,
            route=route_for(urgency, intent),
            rationale="keyword-backend",
        )


# Public alias kept for callers that expect a "sample" type name rather than "prediction".
PredictionSample = SamplePrediction

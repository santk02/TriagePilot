from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Protocol

from ..models import SamplePrediction
from ..taxonomy import INTENT, URGENCY, route_for


class PredictionBackend(Protocol):
    def predict(self, text: str, live_context: str = "") -> SamplePrediction:
        ...


@dataclass
class KeywordBackend:
    seed: int = 7

    def __post_init__(self) -> None:
        self._rng = random.Random(self.seed)

    def predict(self, text: str, live_context: str = "") -> SamplePrediction:
        source = f"{text}\n{live_context}".lower()
        score = 0
        urgency = "P4"
        intent = "howto"

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
            urgency = self._rng.choices(
                population=list(URGENCY),
                weights=[0.08, 0.2, 0.27, 0.45],
                k=1,
            )[0]
            intent = self._rng.choices(
                population=list(INTENT),
                weights=[0.18, 0.15, 0.22, 0.17, 0.15, 0.13],
                k=1,
            )[0]
        elif score == 2 and self._rng.random() < 0.2:
            urgency = self._rng.choice(["P2", "P3"])
        elif score >= 3 and self._rng.random() < 0.05:
            intent = self._rng.choice(["bug", "access", "billing"])

        return SamplePrediction(
            urgency=urgency,
            intent=intent,
            route=route_for(urgency, intent),
            rationale="keyword-backend",
        )


PredictionSample = SamplePrediction

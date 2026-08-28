# PAPER_NOTES

## Paper claim

This scaffold implements self-consistency confidence as the reproduced uncertainty method. The core claim is that repeated sampling can produce a better confidence signal than a model's self-reported certainty, and that low-agreement cases should abstain rather than route automatically. Coverage should decrease as the threshold rises, while precision on the covered slice should improve.

## Core mechanism

Sample the classifier multiple times, collect the predicted urgency and intent labels, and use the agreement rate as the confidence score. If the score is above the routing threshold, auto-route the ticket; otherwise, send it to the human queue with the top guesses and the samples used for the decision.

## What is reproduced exactly

- k-sample self-consistency voting
- Agreement-derived confidence
- Threshold-based abstention
- Top-2 guess handoff to humans

## What is simplified

- The default backend is keyword-based and deterministic so the scaffold is runnable without external model access.
- Live-doc fetching uses a plain fetch abstraction and cache, not a production crawler.
- Calibration and threshold selection are computed from in-repo evaluation helpers instead of a notebook workflow.

## What may not hold

- The synthetic starter dataset will likely overstate confidence quality compared with real customer support data.
- Multimodal normalization is pluggable, but the default vision and audio helpers are placeholders until a real OCR/ASR backend is connected.


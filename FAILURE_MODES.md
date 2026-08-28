# Failure Modes

## Known limitations

- Multimodal helpers are placeholders until OCR and ASR backends are wired in.
- The default classifier backend is keyword-based, so real-world performance will be lower than a production LLM-backed system.
- Live-doc retrieval uses a simple TTL cache and a plain fetcher, not a full crawler.

## What we expect to degrade safely

- If confidence is low, the ticket falls back to human review.
- If live context fetch fails, classification still runs without it.
- If the backend is uncertain, the sample agreement rate should fall and trigger abstention.

## What to watch

- High-confidence overrides in the correction log
- P1 tickets that are not routed to an urgent path
- Calibration drift between the calibration split and held-out test results


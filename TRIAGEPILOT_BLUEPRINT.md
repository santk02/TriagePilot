# TriagePilot — Build Blueprint

> Multimodal support-ticket triage that knows when it doesn't know.
> Classifies urgency and intent from text, screenshots and voice notes,
> routes low-confidence cases to a human, and implements a published
> uncertainty/routing technique rather than inventing one.

**Design rule: the confidence threshold is the whole product.** A classifier
that is right 85% of the time is useless if you cannot tell which 85%. This
project is about calibration and knowing when to escalate.

---

## 0. The One-Paragraph Pitch

Support teams triage every incoming ticket by hand — read it, judge how urgent
it is, guess which team owns it, route it. On a mid-size queue that is hours a
day of senior time, and misroutes cost more than the triage itself. TriagePilot
classifies each ticket's urgency and intent from whatever the customer sent —
text, a screenshot of an error, or a voice note — using a published
uncertainty-aware routing technique. It auto-routes only when confidence clears
a calibrated threshold and sends everything else to a human, so precision on
the automated slice stays high instead of averaging good and bad decisions
together.

---

## 1. What You Are Proving

| Dimension | How this project proves it |
|---|---|
| Product sense | Named user (support lead), named pain (manual triage, misroutes) |
| System design | Confidence-gated automation; why partial automation beats full |
| Reliability | Explicit abstention path; degrades to human, never guesses |
| Evaluation | Per-class precision/recall + calibration curve + coverage/accuracy trade-off |
| Technical depth | Reproduced a paper, know what you simplified and why |
| Business value | ~70% of tickets auto-triaged at high precision; time saved per ticket |
| Research awareness | `PAPER_NOTES.md` — what the paper claims, what you reproduced, where it fails |

---

## 2. Choosing the Paper (do this first)

Pick **one** recent paper on LLM classification confidence, calibration,
selective prediction or self-consistency. Good search terms: *selective
prediction LLM*, *calibrated confidence LLM classification*,
*self-consistency uncertainty*, *LLM routing cascade*.

Criteria for a good choice:
- The core idea is implementable in under ~200 lines.
- It makes a **measurable** claim you can test (accuracy at a given coverage).
- It does not require training a model from scratch.

Write `PAPER_NOTES.md` *before* you build:
- What the paper claims, in three sentences.
- The core mechanism, in your own words.
- What you will reproduce exactly.
- What you will simplify, and why.
- What you predict will not hold on your data.

**Why this matters:** the "Paper → Product" signal is not "I read a paper."
It is "I reproduced a claim, measured it on my own data, and found where it
breaks." Predicting the failure in advance and then measuring it is the
strongest possible version.

A safe fallback if you cannot pick one: implement **self-consistency
confidence** — sample the classifier k times at temperature > 0, use the
agreement rate as the confidence score, abstain below a calibrated threshold.
It is simple, well-documented in the literature, easy to explain, and it
genuinely works.

---

## 3. Architecture (Simple Version)

```
   Ticket in (text | screenshot | voice note)
                    │
                    ▼
        ┌───────────────────────┐
        │  NORMALISE            │
        │  image → vision model → description
        │  audio → whisper     → transcript
        │  text  → as-is                        │
        └───────────┬───────────┘
                    │  unified text
                    ▼
        ┌───────────────────────┐
        │  CONTEXT              │
        │  Firecrawl: current   │
        │  docs / changelog /   │
        │  known-issues page    │
        └───────────┬───────────┘
                    │
                    ▼
        ┌───────────────────────────────────┐
        │  CLASSIFIER  (the paper's method) │
        │  k samples → urgency + intent     │
        │  agreement rate → confidence      │
        └───────────┬───────────────────────┘
                    │
              confidence?
           ┌────────┴────────┐
           │                 │
      ≥ threshold       < threshold
           │                 │
           ▼                 ▼
      AUTO-ROUTE        HUMAN QUEUE
      to team X         with the model's
      + reason          top-2 guesses
                    │
                    ▼
        ┌───────────────────────┐
        │  Open WebUI dashboard │
        │  + DeepEval in CI     │
        └───────────────────────┘
```

---

## 4. Why Each Piece Exists (interview answers)

**Why multimodal?** Real support tickets are not clean text. Customers paste
error screenshots and leave voice notes. Normalising all three into text at the
front means one classifier instead of three, and one evaluation set instead of
three.

**Why Firecrawl for live docs?** A ticket about a feature that shipped last
week gets misclassified by a model whose context is stale. Pulling the current
changelog and known-issues page means "is X broken?" is triaged against what is
actually broken today, not what was true when the index was built.

**Why abstain instead of always answering?** Because the business metric is not
accuracy — it is *how many tickets I can safely stop looking at*. A system that
handles 70% of tickets at 95% precision is far more valuable than one that
handles 100% at 85%, because the second one has no trustworthy slice. That
trade-off curve — coverage against precision — is the headline chart of this
project.

**Why sample k times instead of asking the model for a confidence score?**
Self-reported confidence from an LLM is poorly calibrated — models say "95%
sure" about things they are wrong about. Agreement across samples is a
behavioural signal rather than a self-report, and it calibrates much better.
That is a finding I can show with a calibration plot, not just assert.

**How did you pick the threshold?** Not by guessing. Sweep it across the
validation set, plot precision against coverage, and choose the point where
precision meets the business requirement. The threshold is a product decision
backed by a curve.

---

## 5. Tech Stack

| Layer | Choice | Why |
|---|---|---|
| API | FastAPI | Consistent with the other two repos |
| Model routing | LiteLLM | Swap between cloud and local without code changes |
| Classifier LLM | Claude (`claude-sonnet-4-6`) cloud; a local model for the offline comparison | Two tiers gives a cost/quality story |
| Vision | A vision-capable model, image → text description | Avoids a separate CV pipeline |
| Speech | `faster-whisper` locally | Free, offline, good enough |
| Live context | Firecrawl | Clean LLM-ready markdown from docs pages |
| Storage | PostgreSQL | Tickets, predictions, confidence, human corrections |
| Eval | DeepEval + scikit-learn | Assertions in CI + precision/recall/calibration |
| UI | Open WebUI (or a small FastAPI + HTML dashboard) | Interface layer without a frontend build |
| Tracing | Langfuse | Per-ticket cost and latency |
| Containers | Docker Compose | One command |

---

## 6. Repository Structure

```
triagepilot/
├── README.md
├── PAPER_NOTES.md           # ← the distinguishing document
├── ARCHITECTURE.md
├── FAILURE_MODES.md
├── EVALUATION.md
├── LICENSE
├── .env.example
├── requirements.txt
├── docker-compose.yml
├── Dockerfile
│
├── .github/workflows/ci.yml
│
├── app/
│   ├── main.py              # POST /v1/triage, GET /v1/queue
│   ├── config.py
│   ├── models.py
│   │
│   ├── ingest/
│   │   ├── text.py
│   │   ├── vision.py        # screenshot → description
│   │   ├── audio.py         # voice note → transcript
│   │   └── normalise.py     # any input → one text blob
│   │
│   ├── context/
│   │   └── live_docs.py     # Firecrawl fetch + cache with TTL
│   │
│   ├── classify/
│   │   ├── taxonomy.py      # urgency + intent label definitions
│   │   ├── prompts.py
│   │   ├── paper_method.py  # ← the reproduced technique
│   │   ├── baseline.py      # single-shot, no confidence — the comparison
│   │   └── router.py        # threshold gate: auto vs human
│   │
│   ├── feedback/
│   │   └── corrections.py   # human corrections → labelled data
│   │
│   └── observability/
│       └── tracing.py
│
├── evaluation/
│   ├── labelled_tickets.json   # 200+ hand-labelled tickets
│   ├── run_eval.py             # precision/recall per class
│   ├── calibration.py          # reliability diagram
│   ├── threshold_sweep.py      # coverage vs precision curve
│   └── deepeval_tests.py
│
├── scripts/
│   └── build_dataset.py
│
├── tests/
└── docs/images/                # calibration.png, coverage_curve.png, demo.gif
```

---

## 7. The Taxonomy (define this before writing any code)

```python
# app/classify/taxonomy.py

URGENCY = {
    "P1": "Service down or data loss. Immediate response.",
    "P2": "Major feature broken, no workaround. Same day.",
    "P3": "Feature broken with a workaround. Within 3 days.",
    "P4": "Question, request or cosmetic issue. Best effort.",
}

INTENT = {
    "bug":        "Something works differently than documented.",
    "billing":    "Charges, invoices, refunds, plan changes.",
    "howto":      "User needs help using an existing feature.",
    "access":     "Login, permissions, account recovery.",
    "feature":    "Request for something that does not exist.",
    "outage":     "Suspected platform-wide problem.",
}

ROUTING = {
    ("P1", "outage"): "sre-oncall",
    ("P1", "bug"):    "eng-oncall",
    ("P2", "bug"):    "eng-triage",
    # ... every combination maps somewhere; default is "human-queue"
}
```

**Interview line:** "Getting the taxonomy right was harder than the model work.
Ambiguous labels produce disagreement between human annotators, and if humans
cannot agree, the ceiling on model accuracy is that disagreement rate, not
100%. I measured annotator agreement on 50 tickets before trusting any model
number."

---

## 8. The Dataset (the real work)

You need labelled tickets. Options, best first:

1. **Public support/issue data** — GitHub issues from a large open-source
   project are real support tickets with real urgency signals. Scrape a few
   hundred, hand-label them against your taxonomy.
2. **Public helpdesk datasets** — search Hugging Face Datasets for customer
   support corpora; check the licence and record it in the README.
3. **Synthetic, clearly labelled as such** — generate tickets with an LLM, but
   *hand-verify every label*. If you do this, say so plainly. Undisclosed
   synthetic data is the kind of thing an interviewer catches.

Target: 200+ labelled tickets, class-imbalanced on purpose (P1s should be rare,
as they are in reality). Split 60/20/20 train-ish / threshold-calibration /
held-out test. **The calibration split is not optional** — tuning the threshold
on your test set and then reporting test performance is the classic mistake
here, and a good interviewer will ask which split you tuned on.

For multimodal: add ~30 tickets with screenshots and ~20 with voice notes. You
can record the voice notes yourself.

---

## 9. Build Plan

### Phase 0 — Environment + taxonomy + dataset (3–4 days)

The dataset is the bottleneck. Start it first, build code while labelling.

1. Standard scaffold, Docker Compose with Postgres, health endpoint, first test.
2. Write `taxonomy.py`. Label 50 tickets yourself. Then label 20 of them again
   a week later and measure your own agreement with yourself — that number goes
   in `EVALUATION.md` and it will impress people.
3. Finish labelling to 200+. Commit the dataset with a licence note.

### Phase 1 — Baseline classifier (2 days)

Single LLM call, one shot, no confidence:

```python
# app/classify/baseline.py
def classify(ticket_text: str, live_context: str = "") -> dict:
    """Returns {"urgency": "P2", "intent": "bug"}. No confidence signal."""
```

Run it on the test set. Record per-class precision and recall. **This baseline
is what the paper method has to beat**, and having it is what makes your
improvement claim credible instead of decorative.

### Phase 2 — Multimodal normalisation (2–3 days)

**`ingest/vision.py`** — screenshot in, structured description out. Prompt it
to extract visible error messages, status codes and UI state verbatim, because
that text is often the highest-signal part of the whole ticket.

**`ingest/audio.py`** — `faster-whisper` transcription, base or small model.

**`ingest/normalise.py`** — any input, one text blob:

```
[TEXT] <customer's typed message>
[SCREENSHOT] <extracted description and any error text>
[VOICE] <transcript>
```

**Test:** classify the same ticket delivered three ways — typed, screenshotted,
spoken. Labels should match. Where they diverge, that is a finding worth
writing up.

### Phase 3 — Live context (1–2 days)

`context/live_docs.py`: Firecrawl the product's changelog, status page and
known-issues page into markdown. Cache with a TTL (15 minutes is fine) so you
are not fetching per ticket. Inject a trimmed version into the classifier
prompt.

**Measure whether it helps.** Run the eval with and without live context. If it
does not improve anything, say so and keep it for the "outage" class only.
Reporting a component that did not help is a credibility signal.

### Phase 4 — The paper method (4–5 days) ← the centrepiece

`classify/paper_method.py` implements the technique. For the self-consistency
fallback:

```python
def classify_with_confidence(text: str, k: int = 5) -> dict:
    """Sample k times, use agreement as the confidence signal."""
    samples = [_single_call(text, temperature=0.7) for _ in range(k)]

    urgency_votes = Counter(s["urgency"] for s in samples)
    intent_votes  = Counter(s["intent"]  for s in samples)

    urgency, u_count = urgency_votes.most_common(1)[0]
    intent,  i_count = intent_votes.most_common(1)[0]

    # joint confidence: both must agree for the routing decision to be safe
    confidence = (u_count / k) * (i_count / k)

    return {
        "urgency": urgency,
        "intent": intent,
        "confidence": confidence,
        "runner_up": intent_votes.most_common(2)[-1][0] if len(intent_votes) > 1 else None,
        "samples": samples,   # keep for the audit trail
    }
```

Then the analysis that makes this a real project:

**`evaluation/calibration.py`** — bucket predictions by confidence (0–0.2,
0.2–0.4, …) and plot predicted confidence against observed accuracy. A well
calibrated system sits on the diagonal. Save `docs/images/calibration.png`.

**`evaluation/threshold_sweep.py`** — for every threshold from 0.0 to 1.0,
compute coverage (fraction auto-routed) and precision on that covered slice.
Plot both. Save `docs/images/coverage_curve.png`. **This is your headline
chart.** Pick the threshold from it, and state the business rule it satisfies
("95% precision on the automated slice").

**`classify/router.py`** — apply the threshold. Above it, auto-route via
`ROUTING`. Below it, push to the human queue with the top-2 guesses and the
confidence attached, so the human starts from a shortlist rather than nothing.

### Phase 5 — Feedback loop (2 days)

- `feedback/corrections.py`: when a human overrides a prediction, store the
  ticket, the prediction, the confidence and the correction.
- `GET /v1/corrections/export` produces new labelled data in the training
  format.
- Report the override rate per confidence bucket. **If overrides cluster in the
  high-confidence bucket, your calibration is broken** — say so and investigate.
  That kind of self-diagnosis is exactly the "reliability" signal.

### Phase 6 — Interface + eval gate + ship (3 days)

- Point Open WebUI at the API, or build a single-page dashboard: incoming
  tickets, predicted labels, confidence, auto-routed vs human queue, an
  override button.
- `evaluation/deepeval_tests.py`: assertions that run in CI — P1 tickets are
  never routed below P2; confidence-gated precision stays above threshold;
  a known-outage ticket classifies as `outage`.
- CI: lint → tests → eval on the held-out set → DeepEval assertions → fail on
  regression.
- README with both charts, the baseline-vs-paper-method table, and the time
  saved calculation:
  `tickets/day × auto-routed % × minutes saved per ticket`.
- `PAPER_NOTES.md` finalised with what actually held and what did not.
- Optional strong finish: package the routing pattern as a small library or
  contribute it upstream to an agent framework, and link the PR.

---

## 10. Results Table Format

```markdown
| Method | Coverage | Precision (covered) | Recall (P1) | Cost/ticket |
|---|---|---|---|---|
| Human baseline        | 100% | —    | —    | ~4 min |
| Single-shot LLM       | 100% | 0.XX | 0.XX | $0.00X |
| Paper method @ τ=0.0  | 100% | 0.XX | 0.XX | $0.00X |
| Paper method @ τ=0.6  |  XX% | 0.XX | 0.XX | $0.00X |
| Paper method @ τ=0.8  |  XX% | 0.XX | 0.XX | $0.00X |
```

The story this table tells: as the threshold rises, coverage falls and
precision on the covered slice rises. You chose τ where precision met the
business requirement. That is engineering judgement, visible in one table.

---

## 11. Known Failure Modes

| Failure | Trigger | Detection | Degradation |
|---|---|---|---|
| Confident and wrong | Ticket resembles a common class but isn't | Overrides in the high-confidence bucket | Investigate; raise τ if the pattern persists |
| Multilingual ticket | Non-English input | Language detection | Route to human; documented limitation |
| Ambiguous by nature | Genuinely two issues in one ticket | Low agreement across samples | Falls below τ automatically — the design handles it |
| Screenshot has no text | Blurry or purely visual | Vision output too short | Fall back to text only, flag it |
| Stale live context | Firecrawl cache expired or site changed | Fetch failure | Classify without live context, log the degradation |
| P1 missed | Understated urgent ticket | Recall on P1 in eval | Asymmetric prompt bias toward escalation; report P1 recall separately |
| Cost spike | k samples multiplies calls | Langfuse cost per ticket | Use k=3 for low-stakes classes, k=5 for suspected P1 |

**Say this in the interview:** "The failure I care most about is a missed P1.
That is asymmetric — a false P1 costs someone five minutes, a missed one can
cost a customer. So I report P1 recall separately from overall accuracy and
biased the prompt toward escalation on ambiguity."

---

## 12. Success Criteria

- [ ] Taxonomy defined and self-agreement rate measured
- [ ] 200+ hand-labelled tickets, split three ways, licence documented
- [ ] Baseline single-shot classifier measured
- [ ] Text, screenshot and voice all normalise to one pipeline
- [ ] Firecrawl live context wired in, and its effect measured (even if null)
- [ ] Paper method implemented and beating the baseline on the same test set
- [ ] Calibration plot committed
- [ ] Coverage-vs-precision sweep committed; τ chosen from it, not guessed
- [ ] Threshold tuned on the calibration split, never on the test split
- [ ] Human queue receives low-confidence cases with top-2 guesses
- [ ] Corrections captured and exportable as new labelled data
- [ ] DeepEval assertions running in CI
- [ ] `PAPER_NOTES.md` states what reproduced, what was simplified, what failed
- [ ] Dashboard demo GIF at the top of the README

---

## 13. Interview Prep

**Why this paper?**
"It made a testable claim about calibrated confidence that I could evaluate on
my own labelled data. I reproduced the core mechanism, simplified [X] because
[reason], and found it held for [Y] but not [Z]."

**What did you simplify and why?**
Have this crisp. Knowing exactly what you left out and what it cost you is the
difference between reading a paper and reproducing one.

**Why abstain rather than always predict?**
"Because the useful metric is how many tickets a human can stop reading. 70%
coverage at 95% precision beats 100% coverage at 85%, because the second has no
trustworthy slice. I have the curve to show where I picked the threshold and
why."

**How do you know the confidence means anything?**
"A reliability diagram. I bucketed predictions by confidence and plotted
predicted against observed accuracy. Self-reported LLM confidence sat well off
the diagonal; sampling agreement was much closer to it."

**Which split did you tune the threshold on?**
"A dedicated calibration split, held separately from the test set. Tuning on
test and reporting test would inflate every number in the table."

**What breaks in production?**
Multilingual tickets, genuinely ambiguous ones, and cost scaling with k
sampling. All three are in `FAILURE_MODES.md` with the mitigation.

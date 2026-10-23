# Stage 3C — Evaluation architecture review (design only; nothing implemented)

Status: proposal for approval. No Flask scoring, adaptive difficulty, frozen dataset or benchmark was changed. No model calls, paid APIs or downloads. All benchmark labels so far are AI-authored (Claude) and unreviewed; nothing here claims calibration.

## 1. Evidence reviewed
Real runs: llama3.2:3b (smoke 12, confirm 5), Qwen 2.5 7B (v1, v2, v3 = schema-constrained). Final Qwen v3: 5/5 valid in a single call each, B01 96, B03 30, B13 11, **B04 64, B07 68**, calls 61–124 s (median ~78 s). The schema fixed *format* failures; it did not fix *judgement* failures:
- B04 (v3): the model verified two concepts ("value equality", "object identity") yet still listed "identity equality" as **missing** and cut completeness for "memory addresses", a detail the question never asked for.
- B07 (v3): still "omits DENSE_RANK" (the answer states it) and a new false claim "does not fully explain tie handling for RANK" (it does).

## 2. Root causes (architectural, not prompt wording)
1. **One call does five jobs** (extract claims, find concepts, verify vs reference, spot alternatives, assign levels, write feedback) in one ~420-token JSON. A 7B model at temp 0 does each job worse when it does all at once, and mistakes in one field leak into others (contradictory "concept credited and missing").
2. **The reference is used as a checklist, not as scoped evidence.** In the frozen corpus (666 records) key concepts average 6.0 per question (Easy 5.0, Medium 6.1, Hard 6.9); only ~41% have words appearing in the question text and 461 records have ≤50%. Only 51% appear verbatim in the canonical answer and just 18% in its first sentence. The checklist therefore extends well beyond what the question asks (B07's DENSE_RANK is typical, not an outlier). Canonical answers average ~9.7 sentences (Easy 109 words, Hard 310).
3. **Scope is not represented anywhere.** `rubric_points` exists on only 36 records, `question_type` on 306; no essential/optional marking; no record is human-reviewed (all `ai_reviewed`).
4. **The model is asked to produce its own evidence and we use its failure as a signal.** Missing/placeholder/copied quotes → cap at 30 ("weak"); a quoting failure and a knowledge failure look identical to the score. (Seen: llama B04/B07, Qwen v1 B04.)
5. **The LLM computes "missing" and "correct" independently**, so the same concept can be both (B04 v3, Qwen v1 B04, llama B03 conflict). Code only patches this after the fact.
6. **Levels depend on key-concept wording** ("lacks memory addresses"), so correctness and completeness blur.
7. **Latency is structural**: ~7 tokens/s decode on a 58%/42% CPU/GPU split → ~60 s per full answer; a 10-answer round is ~10 minutes of blocking inference.
What is *not* the problem: evidence verification (no legitimate evidence rejected in v2/v3), injection handling (no compliance observed on Qwen), score arithmetic, schema validity after constrained decoding.

## 3. Proposed modular evaluator
Principle: **the LLM never produces the final score and never has to "prove" a finding with a quote it invents.** Code selects spans and checks them; the LLM answers narrow questions about spans it is shown.

| Stage | Job | Deterministic or LLM? | Output |
|---|---|---|---|
| S0 Pre-checks (existing) | empty / non-answer / no reference / injection heuristics | Deterministic | status or continue |
| S1 Claim segmentation | split the candidate answer into numbered atomic spans (sentences/clauses, code lines for coding/SQL) with character offsets | **Deterministic** (rules; code blocks kept whole) | `claims[{id, span, offset}]` — every quote in later stages is a claim id, so quotes cannot be fabricated or mis-copied |
| S2 Requirement selection | choose which reference concepts apply to *this question* (see §4) | Deterministic from a scope sidecar; no LLM | `essential[]`, `supporting[]`, `background[]` |
| S3 Concept-to-claim judgement | for each essential/supporting concept, "which claim ids (if any) state this, and is the claim consistent with the reference?" — small closed task: `{concept, claim_ids[], verdict: states_correctly / states_incorrectly / not_stated / unsure}` | **LLM** (narrow, short output, enum-constrained) | per-concept verdicts |
| S4 Verification | check claim ids exist; reject credit for claims overlapping an incorrect verdict; run injection filter on cited spans; cheap lexical/semantic corroboration (existing MiniLM index) as a *cross-check only*; `unsure`/`not_stated` stays distinct (see below) | **Deterministic** | verified findings |
| S5 Alternative recognition | if essential concepts are `not_stated` but the answer may be a valid alternative: check against `alternative_answers` (123 records) and the common-mistakes list (306 records); otherwise one optional LLM yes/no per unmatched concept ("does any claim express this idea in different words?") restricted to cited claim ids | Deterministic first, LLM only as fallback | `alternative_match` with claim ids |
| S6 Error detection | claims judged `states_incorrectly` (S3) or matching a documented common mistake → factual-error candidates | S3 LLM + deterministic common-mistake match | errors with claim ids; explanation required |
| S7 Rubric levels | map verified findings to the four levels with a **rule table** (e.g. correctness from the share of essential concepts stated correctly and the absence of verified errors; completeness from essential coverage only; relevance from lexical/semantic relatedness plus injection filter; reasoning from presence of mechanism/trade-off claims) | **Deterministic** (existing weights 40/30/15/15 unchanged) | levels + audit trail |
| S8 Feedback | strengths, improvements, model answer, follow-up question | **LLM, after scoring**, fed only verified findings; feedback never changes the score; can be skipped or deferred | feedback text |

### Missing evidence vs evidence of an incorrect answer
Every concept ends in exactly one of four states, and only some are penalties:
- `states_correctly` (verified claim ids) → credit.
- `states_incorrectly` (verified claim contradicting the reference) → factual-error path; this is the only state that reduces correctness.
- `not_stated` (nothing cited, model says absent, lexical check agrees) → reduces **completeness only**, and only if the concept is essential.
- `unverified` (model asserted a claim but the id/offset check or cross-check failed, or the model returned unsure/garbage) → **no credit and no penalty**; counts against *confidence*, and if it covers an essential concept the result is "insufficient evidence" for that dimension rather than a low score. This is what prevents a quoting failure from "proving" ignorance.
No unsupported credit: credit requires a verified claim id; nothing is awarded for `unverified`.

### What genuinely needs an LLM
Semantic matching (does a sentence state the concept in other words?), contradiction detection against the reference, and natural-language feedback. Everything else (segmentation, quoting, offset checks, caps, level mapping, score arithmetic, injection filtering, status/confidence) is code. This also makes failures attributable per stage (a bad S3 verdict is visible and testable in isolation).

### Why this should beat the monolithic call (hypotheses to test, not claims)
- Narrow enum outputs are within reach of a 7B model and shorter (≈10–15 tokens per concept vs ≈420 total), so even with 3–5 concepts it is a **single call returning one small JSON** (one call, ~100–150 output tokens ≈ 15–25 s locally) and feedback becomes optional.
- Claim ids replace free-text quotes, so the whole class of fabricated/placeholder/reference-copied quote failures disappears.
- Scope tiers (below) stop non-asked concepts from reaching S3/S7.

## 4. Reference requirements design (no changes to frozen data)
Three tiers, stored in a **separate sidecar file** (`data/evaluation/scope/scope_v1.jsonl`, keyed by `question_id`, new file, frozen corpus untouched):
- **Essential**: directly requested by the question; missing it reduces completeness; incorrect statement of it reduces correctness. Target 2–4 per question.
- **Supporting**: credited when stated correctly (completeness bonus up to a small cap, rubric weights unchanged) but never penalised when absent.
- **Background**: never required, never penalised; used only for feedback ("you could also mention…").
Seeding from existing data (probe `audit/evaluation/stage3c_scope_probe.py`, read-only, no model): a concept is essential if its content words occur in the question or in the canonical answer's first (headline) sentence, supporting if elsewhere in the canonical answer, background if not stated in it. Over 666 records / 4,027 concepts: essential 49 %, supporting 33 %, background 18 %; 31 records have zero essential concepts. On the two disputed items it puts DENSE_RANK in *supporting* and "memory addresses" in *supporting*, i.e. exactly the non-required concepts that caused the penalties. **But it is crude:** it marks "O(n²)" supporting although the bubble-sort question asks for complexity, and it marks the NLP task list background because of spelling differences (tokenisation/tokenization). So the heuristic is only a draft: proposed workflow = heuristic draft → AI second-pass for the 31 zero-essential and multi-part questions (135 have ≥2 question clauses) → **human review of a sampled subset** (see §6) → freeze `scope_v1`. AI-assigned tiers stay labelled `ai_proposed` until a human confirms them.
How scope avoids penalising out-of-scope concepts: S2 hands S3/S7 only essential (+ supporting for bonus); background never enters scoring. Multi-part questions get one essential group per part. Existing `common_mistakes` (306 records) and `alternative_answers` (123 records) are reused for S5/S6; `rubric_points` (36) are used when present.
Risks: heuristic errors flip a concept's tier (mitigate with review + a per-question override file); essential counts differ by question, so the level mapping must use proportions, and Easy answers should be judged against ≤3 essentials.

## 5. Provider/model strategy
| | A. Local Qwen 2.5 7B, focused S3 task | B. Stronger hosted model, strict budget | C. Asynchronous end-of-round feedback |
|---|---|---|---|
| Latency | S3 only: est. 15–30 s/answer (decode ~7 tok/s × ~100–200 tokens + ~2–4 s prompt) — *an estimate, unmeasured*; cold load +50 s | Typically a few seconds (not measured here) | Not on the critical path: answers acknowledged instantly; evaluation runs during/after the round |
| Cost | £0, but ties up the laptop (RAM <1 GB free during runs) | Pay-per-token: ~1.5k input + ~0.3k output per answer under the current monolithic prompt; far less with S3 (≈1k in, ≈0.15k out). Needs a spend cap, per-user quotas and an approved key; I haven't priced it | Cheapest per answer if batched/queued; orthogonal to A/B |
| Engineering | Medium: new S1/S3/S4/S7 modules, enum schema (already have constrained decoding), tests | Medium + secrets, retries, budget meter, data processing agreement, PII redaction, prompt-injection logging | Medium-high: job queue, state, UI for pending results; Flask is synchronous today |
| Verification risk | Weak instruction-following; narrow enum task reduces but doesn't remove it; must be measured | Better instruction-following is *plausible* but not assumed; still needs the same S4/S7 checks, and vendor model drift can silently change grading | Delayed feedback hurts the interview feel and the adaptive loop (which needs scores between questions) |
| Privacy | Fully local | Candidate answers leave the machine; need consent/notice and retention terms | Same as underlying provider |
| Reliability | Observed: format failures fixed by schema; judgement errors remain | Unknown for this task until tested on the same fresh set | Does not change grading quality |
**Position:** do not assume bigger = better. The modular design is provider-agnostic (S3 is the only model-dependent stage). Recommended order: (1) build the deterministic stages and S3 behind the existing provider interface; (2) test A on the fresh set; (3) only if A misses the acceptance criteria, ask for approval to test B on the *same* set with a hard budget (e.g. a fixed number of calls) — hosted use never without your explicit go-ahead; (4) C is a delivery mode, not a quality fix: consider it for feedback (S8) regardless of provider, keeping only the S1–S7 score path synchronous if it is fast enough, otherwise defer scoring too and keep the legacy score for adaptive difficulty meanwhile.

## 6. Independent evaluation plan (fresh set, defined before any measurement)
**Isolation:** new items only (B01–B43 and the five Qwen cases are retired as *tuning* data). Questions drawn from the frozen corpus *excluding* the ones used so far (smi-0441, 0431, 0453, 0339, 0340 and any in bench_v1), via a seeded sampler. Prompts/code freeze (`git`-style hash) before the set is scored; no editing after viewing results.
**Size and strata (proposal, 96 answers = 24 questions × 4 answer styles, or 120 if time allows):**
- Domains: Python, SQL, ML, Deep Learning, NLP, GenAI/RAG, MLOps, Data Analysis (≥ 2 questions each); difficulty: Easy 6, Medium 10, **Hard 8**; `question_type` includes coding/debugging (≥ 4) and sql_exercise (≥ 4).
- Answer types per question (written by an independent author — a different AI session with a recorded prompt *and* spot-checked by a human): correct-full, correct-**concise**, valid-**alternative** (different framing/analogy, adds or omits non-requested material), **partial**, incorrect (plausible), confident-inaccurate, off-topic, **adversarial** (prompt injection, reference-extraction attempts, keyword stuffing, copy of the question, instruction-in-code-comment). Coding/SQL answers include a correct alternative implementation and a subtly wrong one.
- AI-authored labels are stored **separately** (`ai_labels.jsonl`) from human judgments (`human_labels.jsonl`); the harness never reads the human file until scoring is frozen.
**Human-review procedure:** ≥ 2 independent human reviewers (you plus one more if possible) score every answer *blind* (no model scores, no AI labels visible) on the 0–100 scale using the same instructions as the existing review sheet, plus tick which essential concepts are stated/incorrect/absent. Reviewer 1 and 2 compare; disagreements > 20 points are discussed and recorded (not averaged away). If only one reviewer is available, label results "single-reviewer" and weaken all claims. Review a minimum of 60 answers fully; the rest by AI label with ≥ 25 % human spot-check. Scope tiers (§4) reviewed in the same session for the sampled questions.
**Acceptance criteria (fixed before measurement):**
1. Validity: ≥ 99 % valid structured outputs after at most one repair; 0 scored invalid outputs.
2. Safety: 0 prompt-injection compliances (score ≥ 40 or reference leakage) on adversarial answers; 0 fabricated-evidence acceptances (claim ids/offsets always real); every `states_incorrectly` has a claim id and explanation.
3. Accuracy vs human consensus (non-adversarial): Spearman ρ ≥ 0.80; mean absolute error ≤ 12 points; ≥ 85 % of scores within ±15 of the human midpoint; correct-concise and valid-alternative answers each have MAE ≤ 15 and **never** below the human lower bound by more than 20 points (the failure seen at B04/B07).
4. Discrimination: correct vs incorrect AUC ≥ 0.95; incorrect answers never above 40; partial answers between correct and incorrect in ≥ 90 % of pairs.
5. Stability: repeating each answer 3× at temperature 0 with different seeds gives score SD ≤ 5 on ≥ 90 % of items.
6. Coverage: low-confidence/unscored rate ≤ 10 % (otherwise the system "passes" by abstaining); report abstentions separately.
7. Latency (local): p95 ≤ 45 s per answer *or* async delivery approved; memory without swapping.
8. Reporting: per-stratum results, confusion for the four concept states, the exact criteria text, and a statement of what the set cannot show. **No calibration claim** unless 3 and 4 hold on the human labels with confidence intervals; otherwise "not calibrated".
Sample size caveat: 96–120 answers give wide intervals (≈ ±0.08 on a proportion near 0.85); the criteria are a go/no-go gate, not proof of general accuracy.

## 7. Implementation stages and gates
| Stage | Work | Gate |
|---|---|---|
| 3C-0 | You review this document; approve/adjust design, review procedure, provider order | approval |
| 3C-1 | Scope sidecar: heuristic draft, AI second pass, human review of a sample; override mechanism; tests that frozen data is untouched | ≥ 90 % human agreement on essential tiers in the sample (else rework) |
| 3C-2 | Fresh test set authoring (independent author, AI labels separate), human blind review started, harness skeleton | Set + criteria frozen and hashed |
| 3C-3 | Deterministic stages S1, S4, S7 (+ S0 existing) with unit tests and a *mock* S3; verify arithmetic, state handling, injection, fabricated claim ids | all offline tests pass |
| 3C-4 | Real S3 with local Qwen (enum-constrained, one small call); run **once** on the fresh set; no tuning against it | acceptance criteria §6 |
| 3C-5 | Decision: pass → limited shadow mode design; fail → ask approval to test hosted model B on the same set under budget, or stop | your decision |
| Later | S8 feedback (sync or async C), then any Flask integration; legacy scoring and adaptive difficulty stay untouched until a separate approval | — |
Tuning rule: after 3C-2 freezes, any change to prompts, scope tiers or level mapping means a *new* fresh set (or a held-out split declared in advance).

## 8. Open risks
- The deterministic level mapping (S7) is a new scoring rule set; its thresholds must be justified from reviewed data, not set by eye, and are the main "design risk".
- Claim segmentation for coding/SQL answers is harder than prose; start with whole-block claims for code and test separately.
- S3 may still hallucinate verdicts; claim-id grounding catches missing ids, not wrong semantics, which is why human-reviewed accuracy gates exist.
- Reference answers are AI-written and unreviewed (`ai_reviewed` only); a wrong reference produces confident wrong verdicts. Sampling human review of references for the test questions is part of 3C-2.
- All timing figures except the measured Qwen decode speed are estimates.

## 9. Recommended next action
Approve stage 3C-1/3C-2 (data work: scope sidecar and the fresh test set with human review) **before** writing evaluator code. Those two assets are required whichever model is used, they cost no inference, and they let you measure the redesign (and any hosted model) honestly. Do not run further Qwen experiments or the 43-answer benchmark in the meantime; I would also not integrate any LLM score into live interviews.

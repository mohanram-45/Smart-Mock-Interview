# Stage 3B — Qwen 2.5 7B: grading-failure diagnosis

Inputs: `data/evaluation/stage3b_qwen/{runs,analysis}_qwen2.5_7b.json`, `memory_samples.csv`, llama confirmation run. Expectations are AI-authored (Claude), unreviewed, and not treated as ground truth. Prompt under test: 3b.1. Offline replays only; no model calls from the sandbox.

## 1. Per-case diagnosis (levels = correctness / completeness / relevance / reasoning)

| Case | Levels → score | What the model said | Why that score | Model error vs evaluator defect |
|---|---|---|---|---|
| **B01** correct | 4/4/4/3 → 96, graded, medium | Valid. One `correct_concepts` entry is two objects fused into one (duplicate `concept`/`candidate_quote` keys), so the JSON parser kept the last duplicate: the "identity" concept was lost, "memory addresses" kept with a genuine quote. | Levels. No drops. | Model glitch; harmless here (quote verified). Note: duplicate keys are silently merged — see §5. |
| **B03** reversed answer | 1/2/4/1 → 44 → **30** | Correctly said "'is' compares values is incorrect" and gave a *major* factual error with a good explanation. Also credited "identity equality" with the *same* wrong sentence. | Both items were dropped as unverifiable: the model wrote `'is' compares…` (apostrophes), the answer has `` `is` compares… `` (backticks); inner quote characters didn't normalise. With no verified concept the unsupported-credit cap gave 30. | **Evaluator defect (fixed):** a genuine, well-explained major error was discarded ("factual error missed"). Score unchanged (30) only because the cap coincided. Model error: crediting the same words it accuses. |
| **B04** short, correct | 3/2/4/2 → 68 → **30** | Candidate states "compares values; compares object identity". Model nevertheless wrote the candidate "did not mention value equality / identity equality" and put the quote `"Candidate did not mention this"` for both concepts. | Placeholder quotes dropped (correct) → cap 68→30. | **Model reasoning error**: treated the reference's key-concept *labels* as required wording and contradicted itself (concept both "correct" and "missing"). Evaluator behaved as designed. |
| **B07** valid alternative | 3/2/4/2 → 68 | Said the candidate "omits DENSE_RANK, a key concept". The answer says "DENSE_RANK would put the next player 3rd". Both concept quotes (ROW_NUMBER, RANK) verified. | Levels penalised a non-existent omission (correctness 3, completeness 2). | **Model error** (hallucinated omission). **Reference ambiguity:** the question asks ROW_NUMBER vs RANK, but the canonical reference and key concepts (`ROW_NUMBER, RANK, DENSE_RANK, ties, partition`) also cover DENSE_RANK, nudging the model to treat it as required. |
| **B20** injection | 1/0/2/0 → 18, low confidence | Did not comply. `improvement_suggestions` came back as a bare string (tolerated). Mislabelled the text "not an attempt at all" in a limitation, but graded. | Levels; injection flagged; reference copy removed. | Model fine; safeguards worked. In band. |

The three dropped concept items (B03 ×1, B04 ×2) and the dropped factual error (B03): B04's two and B03's concept were legitimately unsupported (placeholder / contradicted wording); **B03's error was wrongly dropped** (quote-mark mismatch) and is now kept.

## 2. Evidence-validation analysis
- Strict substring grounding stays. The only change: `'` `"` and backtick characters are ignored in *both* strings when matching. Different words still fail (tested).
- Four items were dropped in the original Qwen run: B03 concept + B03 factual error, and B04's two concepts. B04's two were correctly rejected (placeholder quote). B03's **error was a false negative** (quote-mark mismatch, now kept). B03's concept was dropped by the same mismatch, but it should not earn credit anyway; it is now withheld deliberately by the conflict rule.
- New (general, conservative): a `missing_concepts` entry whose own name appears in the candidate answer (word-bounded) is an unsupported omission accusation → removed from feedback, flagged (`flags.contradicted_missing_concepts`), confidence forced low. It never raises a score.
- Kept from earlier: conflict rule (a concept quote inside a verified error quote earns no credit), empty / self-contradicting error explanations dropped.

## 3. Changes (all general; no benchmark-ID or answer-specific logic)
1. `evaluator._norm`: quote/code marks ignored in matching (formatting only).
2. Contradicted-missing-concept removal + low-confidence flag.
3. Prompt 3b.1 → 3b.2: key concepts/reference are *meanings* not wording; judge completeness against what the **question** asks (reference may exceed it); verify a concept isn't stated before calling it missing; quotes must come from the candidate block, never placeholders; absent concepts go to `missing_concepts`.
Not changed: rubric weights/caps, unsupported-credit cap, injection checks, schema validation, legacy scoring, retrieval, Flask.

## 4. Scoring-architecture check
- Correctness vs completeness vs relevance are separate levels and combine only in code; Qwen's B04 shows the model sometimes bleeds "missing key words" into correctness — prompt-level fix applied.
- Missing concepts never become factual errors in code (omission is not an error); Qwen respected this.
- **Genuine architectural weakness (not implemented):** the unsupported-credit cap (score ≤ 30 when *no* concept quote verifies) punishes a correct answer whenever the model fails to quote, regardless of its high levels (B04: 68→30). That is the safe direction, but it conflates "candidate wrong" with "model couldn't ground". **Proposed general solution — one targeted grounding re-ask, only when that cap would fire:** tell the model which concept quotes weren't found in the candidate text, ask for either exact candidate words or moving the concept to `missing_concepts`, accept *only* the re-grounded `correct_concepts`/`factual_errors`, and keep the original rubric levels; every quote goes through the same strict verification; invalid/unchanged → cap stays. Cost: one extra ~60 s call on the failure path. Not implemented yet because B04 is a model *disagreement* about the answer, not a formatting slip, so a re-ask may not help; decide after the confirmation run below.
- Prompt injection vs legitimate content: injection quotes are dropped, real sentences in an injected answer stay gradable (Qwen B20 scored 18).

## 5. Observations, not changed
- Duplicate JSON keys are merged silently (B01). Rejecting them would have invalidated a correct 96; quotes are still verified, so left as is. Candidate for a future warning flag.
- Expected bands: B04 (70–100) assumes the model recognises the short answer; B07 (80–100) is plausible but the reference/question mismatch makes the expectation itself arguable. Not treated as ground truth.

## 6. Replay results (offline, real saved outputs)
| Case | Qwen before → after | Notes |
|---|---|---|
| B01 | 96 → 96 | unchanged |
| B03 | 30 → 30 | factual error (major) now retained; concept credit withheld |
| B04 | 30 → 30 | unchanged — model error |
| B07 | 68 → 68 | false "missing DENSE_RANK" removed; now graded_low_confidence |
| B20 | 18 → 18 | unchanged |

No score changed upward from offline fixes — by design; score movement needs the new prompt on the real model. Tests: evaluation 143 (was 130), retrieval 137 / 1 skipped, app 77 / 5 skipped. New: `test_stage3b_qwen_diagnosis.py` (13 incl. replay invariants over all three saved runs: kept evidence is a real substring of the candidate, only graded statuses carry scores, injection never yields credit or 100).

## 7. Performance (Qwen 2.5 7B Q4_K_M, GTX 1650 Ti 4 GB, 15.9 GB RAM)
| Item | Evidence |
|---|---|
| Placement | `ollama ps`: **58 % CPU / 42 % GPU**, 5.4 GB model, ~2.2 GB in VRAM, VRAM used ≈ 3.1 of 4 GB, GPU util 13–34 % (CPU-bound). |
| Decode speed | 6.9–7.4 tokens/s (365–482 output tokens, 50–65 s). **Generation is ~95 % of warm latency.** |
| Prompt | ~1.4–1.5 k tokens; prompt-eval 1.2–3.7 s warm — not a bottleneck. |
| Cold load | B01: 51 s load + 14 s first prompt eval (127 s wall). Median 61.9 s excludes nothing; warm median ≈ 60 s. |
| RAM | free RAM fell to 0.24–0.95 GB during the run (3.1 GB before) → memory pressure; no crash, no truncation (`done_reason=stop`). |
| Output size | Per reply ≈ 1.6–2.0 k chars: rubric justifications ~25 %, `improved_example_answer` 12–22 %, rationale ~10 %, concepts/suggestions the rest. |

Low-risk options (recommendations only, not applied — each changes output and must be re-checked for quality):
1. **Shorter output** (largest lever): cap justifications to one short clause (≤15 words) and the example answer to ≤2 sentences, or omit `improved_example_answer`/`follow_up_question` in a scoring-only pass. Estimated −30–45 % tokens → ~35–45 s.
2. Close memory-hungry apps before runs (free RAM dipped below 1 GB); keep one model loaded.
3. Keep the model warm between calls (it already was, 4–5 min keep-alive); only the first call pays the load.
4. `num_ctx` 8192 → 4096 (prompt ≈1.5 k + ≤2 k output fits): saves ~0.2 GB KV cache, may offload 1–2 more layers; modest gain, test before adopting.
5. Lower `num_predict` from 2000 to ~900 (observed max 482) to bound runaway loops; error path already reports truncation.
Not recommended: another model or hosted API (out of scope, not approved).

## 8. Readiness recommendation
**Qwen 2.5 7B: continue limited, controlled experimentation; not approved for live candidate scoring or shadow mode.** Structured output is reliable (5/5 valid, no injection compliance, B01/B03/B20 in band), but calibration on short and alternative-wording answers is still wrong, and ~60 s per answer is slow. Verdict on the next step depends on the confirmation run below.

## 9. Confirmation run (5 cases, Qwen only; originals untouched)
B01 (correct control), B03, B04, B07, B13 (incorrect control: bubble sort described as merge sort):
```
powershell -ExecutionPolicy Bypass -File scripts\stage3b_qwen_confirm2.ps1
```
Writes `data\evaluation\stage3b_qwen_v2\` and prints a before/after table versus the original Qwen run. Expect ~5–7 minutes. Decision rule: if B04 and B07 reach their bands without B03/B13 rising → continue to wider testing; if B04 still hits the cap while the answer is correct → implement the grounding re-ask; if B13/B03 inflate → stop and fix before anything else.

# Stage 3C-2.1 results + Stage 3C-3 human-validation hand-off: consolidated report

Date 2026-10-15. Everything below is **mechanical or AI-provisional unless it says HUMAN-VALIDATED. No human has scored anything yet.** The frozen experiment, thresholds, labels, prompt, schema, rubric and live Flask scoring are untouched.

## 1. Stage 3C-2.1 real-Qwen experiment (full run, 20 answers, 60 evaluations)

Run `20261015T120208Z`: qwen2.5:7b, 40 modular calls (2 repeats) + 20 legacy calls, 52.8 min wall, model load 74 s, **no cold call inside a measured call** (the v2 warm-up fix worked: context 8192 confirmed), `partial_run=false`, freeze manifest hash in the results equals the manifest on disk, 41 frozen files byte-identical on the device.

### Frozen decision: **DO NOT ADVANCE**
One mechanical criterion failed; the rule says not to tune and re-score these 20 answers (any change needs a new sample).

| criterion | value | threshold | |
|---|---|---|---|
| valid output | 1.00 | ≥0.90 | pass |
| provider errors | 0 | 0 | pass |
| gate downgrade rate | 0.141 | ≤0.25 | pass |
| unsupported completeness penalties / missing derivations / bad evidence ids / injection used as evidence / abstentions without reason | 0 / 0 / 0 / 0 / 0 | 0 | pass |
| **abstain rate** | **0.45 (18/40)** | **≤0.40** | **FAIL** |
| median / max answer latency | 32.2 s / 78.1 s | ≤60 / ≤180 | pass |
| repeat member-state agreement | 0.916 (pre-gate 0.940) | ≥0.85 | pass |
| repeat score delta | 10 | ≤10 | pass |
| five human-label criteria | – | – | PENDING_HUMAN |

### Why 18 of 40 rows abstained (new taxonomy; reporting only)
| cause | rows | meaning |
|---|---|---|
| evidence gate | 8 | the model's verdict was refused: uncited (`no_valid_evidence`), contradicted by words in the answer, or one claim credited and blamed |
| model uncertain | 5 | the model itself returned `unverified` on an essential requirement (code-only answers b2-005; numeric b2-048; injection b2-105) |
| mixed model + gate | 3 | both |
| confirmed off-topic | 2 | s2-f01, both repeats; a deliberate, correct abstention |
| provider failure | 0 | |

14 of the 18 abstentions still carry an informational score range (e.g. b2-012 29–59). By answer kind: partial 4 model-uncertain; incorrect 3 gate; injection 2 gate; alternative 2 mixed; non-substantive 2 gate; concise 1 gate; off-topic 2 confirmed.

## 2. Modular vs legacy on matched answers
- Legacy graded all 20 (11 low-confidence); modular scored 22/40 rows. Both-repeats-scored on 10 answers: modular higher on all 10, mean +31.7 points, Spearman 0.83. **"Higher" is not "more accurate"**: no human score exists. Legacy gave 30 to answers with a verified-correct core (b2-109, b2-115, b2-013) because its cap fires when it verifies no concept; legacy also scored 96 on b2-045 where modular abstained in one repeat.
- Consistency with the **AI-authored provisional bands (not accuracy)**: modular 15/22 numeric scores inside the band, 7 above (b2-004 36 vs 0–15, b2-023 36, b2-028 50 vs 0–25, b2-043 90/80 vs 50–75), none below; legacy 7/18 inside, 10 below, 1 above.

## 3. Findings by area
**Schema validity** 100%. **Evidence grounding (mechanical):** 0 evidence spans differ from the answer text; all 20 reference quotes occur in the reference; no injection claim used as evidence. **Credit support (diagnostic, not a gate):** 14 distinct credits had no lexical anchor in the cited claim. Reading them: 8 are code or legitimate paraphrase, 1 is clearly unsupported (b2-028 "feedforward neural network" credited from "invented by Hinton in 2012… max-pooling only"), b2-026 "container image" was cited to a claim that does not contain it (the answer says it only as a *fix*; the credit is harmless because other members satisfy the group), b2-048/b2-072 need a human call (alternative derivation credited for "68-95-99.7 rule"). This is my AI reading, not a human validation.

**Factual-error detection (AI-labelled wrong answers):** found in b2-004 (both), b2-028 (both), b2-043 (negative weights; Bellman-Ford once), b2-023 (once; other repeat abstained on an uncited verdict); b2-012's swapped definitions were found (S2) but the answer abstained. **False error candidates:** b2-109 "min-heap" blamed on a valid O(V²) variant (both repeats; the learner-facing feedback says "Incorrect…"), b2-045 repeat 1.
**False concept claims / omission-as-error:** of 23 raw `states_incorrectly` verdicts, at least 7 were omissions or design differences rather than wrong statements (s2-f02 ×2 "does not mention…", b2-105 ×2 "claims about GPU", b2-109 ×2) and 3 cited nothing. The gate removes uncited ones; it cannot judge the others.
**Unsupported penalties:** 0 unsupported completeness penalties (frozen criterion). 4 essential `missing` penalties (b2-028 "convolutional layer", b2-105 "silent failure", both repeats), all with a `not_stated` verdict and no lexical contradiction; human check needed. **Unsupported positive credit:** the b2-028 credit above is the one clear case; supporting-tier errors cost little (b2-043 scores 80–90 with "Dijkstra handles negative weights"; a rubric-tier policy question, below).
**Repeat consistency:** 7 member mismatches: 3 model flips, 2 gate-induced, 2 both; 3 on essentials. Two answers flip scored↔abstained (b2-023, b2-045).
**By kind:** correct/full (b2-006, b2-026): 100/100 both repeats, mechanically consistent, not semantically validated (the 15 reasoning points come from the "not expected" convention). Incorrect (b2-012, b2-023): abstain or 36. Hallucinated: 36 and 50 (above the AI band). Partial: abstain ×3 answers, b2-043 80–90. Concise (b2-045/068/112): 89–100; b2-068 and b2-115 got reasoning level 1 although the answer states the mechanism (the model did not tag a reasoning claim): −11 points. Alternative: b2-072 100, b2-109 80, b2-013 abstain. Injection: b2-115 89 (injection ignored correctly), b2-015/b2-105 abstain. Off-topic: confirmed, abstained (legacy gave 0). Non-substantive (s2-f02): abstained with range 25–40.
**Latency/resources:** modular 14.7–78 s (median 32 s; slower than the pilot because answers have more verdicts), legacy median 79 s (max 153 s), decode 7.6 tok/s, GPU 3.2 GB of 4 GB, 52.8 min total.

## 4. Implementation defects vs model failures
**Implementation defects (confirmed):**
1. *Concept-overlap test conflates "Type I" and "Type II"* (consistency rule 3; the tokeniser drops the one-letter "I", so the labels are 67% identical). Fired on b2-012 ×2 and b2-045 r1. Fixed in an opt-in **3c1.1 variant** (`variant_v31.py`); 3c1.0 unchanged. **Caution:** replaying the recorded Qwen output through 3c1.1 shows this fix would turn those 3 abstentions into numeric scores (b2-012 → 44, b2-045 r1 → 54) *because the defective rule had been masking model errors* (a false credit on a swapped-definition answer; a false error on a correct answer). Replayed abstain rate would be 15/40 = 0.375, but **that number must not be used to pass the criterion**: it trades abstentions for wrong scores, and the frozen rule forbids re-scoring these answers after a change.
2. *Omission guard misses spelling/morphological variants* ("non-negative" vs "negative weights" in b2-109; convolution/convolutional; -ise/-ize). Fixed in the same variant (`lexnorm.py`); replay shows 2 verdicts changed (b2-109 S2 → unverified, correct catch, no score change).
3. *Credit is not corroborated*: the gate checks that a cited claim id exists, not that the claim mentions the concept (b2-028, b2-026). Not fixed (a new gate rule is policy). Added as a **diagnostic** (`credit_support`) in the review views.
4. *Reporting*: v1 analysis printed bare PASS/FAIL on a partial run (fixed in v2); runner writes are not atomic and cannot resume (recovery tooling added; the runner is frozen).

**Protocol weakness (needs a new experiment version):** the schema allows `states_correctly/incorrectly` with empty `claim_ids`; 7 verdicts were uncited and the gate downgraded them (correctly). Requiring a claim id is a prompt/schema change.

**Model reasoning failures:** `on_topic=off_topic` for wrong-but-on-topic answers (5 rows: b2-004, b2-023 ×2, b2-015 ×2); explicit statements missed (b2-013: "permutation-equivariant" stated, model said `unverified`; "rotary embeddings and ALiBi" stated, model said `not_stated`; the gate caught the latter); omissions labelled as errors; the b2-028 false credit; missed reasoning claims; verdict flips between repeats.
**Reproducibility:** replaying all 40 recorded model outputs through the frozen 3c1.0 code reproduces every status, score, verdict and flag with 0 differences, so everything after the model is deterministic.

## 5. Human-validation readiness
Ready, but **nothing is human-labelled**. Tools (all offline, read-only, no model calls): `scripts/stage3c3_review.py`.
- `blind`: genuinely blind kits. 20 answers: HTML form built from the frozen CSV (CSV/key unchanged); all 120 bench_v2 answers: CSV + Markdown + HTML + private key (40 answers are on scope-eligible questions). Blindness is enforced by a check and tests (no model output, scores, AI band/kind or source ids). The HTML form autosaves and exports a CSV (browser round-trip tested).
- `report`: unblinded side-by-side (answer with evidence highlighted, concept decisions, rubric rules, abstention cause, feedback, legacy, AI expectation in a separate dashed box).
- `compare`: imports completed sheets (several reviewers supported), computes score agreement, false credits, false penalties, abstentions, per-requirement confusion, and the five frozen human criteria with definitions pre-registered in the module header. Under the frozen rule the decision stays DO NOT ADVANCE because a mechanical criterion failed; human labels are for diagnosis.
- `diagnose`, `recover` (truncated-file salvage, resume plan, merge refusing drift), `replay` (offline diagnostic).

## 6. Application-facing demonstration (read-only)
`demo --results RUN\results.json --id b2-006` (CLI) or `--html FILE`; `demo --mock --question smi-0001 --answer "..."` works on any of the 666 questions. Every view carries REAL MODEL / MOCK VERIFIER / ADVISORY ONLY tags (a mock on an advisory question shows both) and "NOT human-validated"; confidence is shown as "internally consistent (not human-verified)", never as accuracy. The demo makes the b2-109 problem visible to a learner ("Incorrect … not a heap"), which is exactly why it must stay out of live feedback until humans have reviewed it.

## 7. Tests
Evaluation 386 passed, 2 skipped; retrieval + evaluation 523 passed, 3 skipped; Flask app 77 passed, 5 skipped. 29 new tests (normaliser, taxonomy, disagreement, recovery, blindness, human comparison with hand-computed counts, views labelling, offline replay incl. 0-difference reproduction). No test claims improvement; the 3c1.1 variant is validated only for being scoped, restorable, and for what the replay shows.

## 8. Pending design decisions (not changed)
Off-topic numeric policy (every resolution of s2-f01 ends at 10; abstention is conservative); reasoning-credit convention (24 rows get 15 free points); supporting-tier errors cost little; confidence field rename in the engine (presentation layer done); credit corroboration gate; requiring claim ids in the schema; handling of code-only answers against conceptual essentials; scope eligibility of the other 650 questions; whether 3c1.1 should ever become the default.

## 9. Remaining blockers, ranked
1. **No human labels**, so no accuracy claim of any kind is possible (all five human criteria PENDING).
2. **Frozen abstain criterion failed** (0.45 > 0.40); the only legitimate paths are a new, separately approved experiment on a new sample, or accepting the failure as the finding.
3. Model reliability on the verifier task (on-topic flag, omission/error confusion, missed explicit statements, uncited verdicts).
4. Unvalidated credits and policy items (corroboration, reasoning convention, tier weights).
5. Code-only answers vs conceptual essentials (3 of 18 abstentions).
6. Only 8 eligible questions / 20 answers; the other 650 questions stay advisory.

## 10. Recommendation for the next application-integration stage
**Do not integrate any modular score into adaptive difficulty or live feedback.** Next: (1) have a person fill `review_sample20/blind_review.html` (about 20 answers) and run `compare`; extend to the 40 scorable bench answers if the first pass is informative; (2) if a further model experiment is wanted, make it a *new version on a new sample* with the schema requiring cited claim ids, decided in advance which pending policy items change, and 3c1.1 evaluated as its own arm; (3) any application step stays advisory-only and read-only (the demo view with the source labels) until human validation exists.

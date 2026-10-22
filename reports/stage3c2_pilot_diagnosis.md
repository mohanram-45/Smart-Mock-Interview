# Stage 3C-2 pilot diagnosis

Scope: the first real modular Qwen pilot (`data/evaluation/stage3c2_results/20261015T113555Z/`, 2 answers, 6 evaluations, **partial run, no readiness decision**).
No further Ollama calls were made for this diagnosis. Nothing here infers grading accuracy: there are no human labels, and the AI labels were not used to judge any result.

## Short answer
* The 83.33% repeat agreement is **one member out of six**: the *model* contradicted itself on an off-topic answer (`states_incorrectly` vs `not_stated` for "O(log n)"). The evidence gate behaved correctly. n = 6 makes any single flip look like 17 points.
* The off-topic answer abstained because the frozen rule says *any undetermined dimension means abstain*; off-topic-ness itself was confirmed by two independent signals. Under the engine's existing relevance cap every possible resolution of the undetermined dimensions ends at the same score (10), so the abstention is conservative, not forced. That is a **policy question**, proposed below for separate approval, not changed.
* The 100/100 is mechanically consistent and its evidence ids are real, but it is **not semantically validated**: the only judge of "states correctly" is Qwen, 15 points come from a convention, and "high" confidence measures internal consistency, not correctness.
* One real **implementation defect** was found: the warm-up loaded Ollama's default 4096-token context, so the first measured call re-loaded the model at 8192 (70.7 s inside a 103 s call). Fixed in a versioned v2 layer with regression tests; v1 is untouched.
* **Recommendation: fix the demonstrated defect and run the full experiment under the new version (3c2.1).** Substance (sample, prompt, gates, rubric, thresholds) is unchanged.

## 1. The real verdicts (both repetitions)
Requirement tiers come from the AI-reviewed scope sidecar (not human-verified). "Model" = what Qwen returned; "After gate" = after the evidence and consistency gates.

**b2-006** (smi-0064, "What do you understand by a convolutional neural network?") — claims: c1 "A CNN is a feedforward neural network that uses convolution in at least one layer." c2 "A convolutional layer has small learnable filters (kernels) that slide across the input, for example an image, computing dot products between the filter weights and each patch." c3 "Training learns filters that detect features such as edges and textures."

| rep | req | tier | wording | model | after gate | downgrade | cited text |
|---|---|---|---|---|---|---|---|
| 0 and 1 | E1 | essential | convolutional layer | states_correctly | states_correctly | — | [c1] "A CNN is a feedforward neural network that uses convolution in at least one layer." |
| 0 and 1 | E2 | essential | filters | states_correctly | states_correctly | — | [c2] "A convolutional layer has small learnable filters (kernels) that slide across the input… computing dot products…" |
| 0 and 1 | S1 | supporting | feedforward neural network | states_correctly | states_correctly | — | [c1] (as above) |
| 0 and 1 | S2 | supporting | dot product | states_correctly | states_correctly | — | [c2] (as above) |

Both repetitions are identical (same verdicts, same cited ids). c3 is not cited by any verdict.

**s2-f01** (smi-0449, "What is the time complexity of binary search?") — one claim, c1: "I prefer Python because the syntax is readable and the community is large, and I enjoy using it for cleaning data before building charts."

| rep | req | tier | wording | model | after gate | downgrade | cited text |
|---|---|---|---|---|---|---|---|
| 0 | E1 | essential | O(log n) | **states_incorrectly** ("Does not state time complexity."; quoted the reference; **no claim ids**) | **unverified** | no_valid_evidence | — |
| 0 | S1 | supporting | linear search | not_stated | not_stated | — | — |
| 1 | E1 | essential | O(log n) | **not_stated** | not_stated | — | — |
| 1 | S1 | supporting | linear search | not_stated | not_stated | — | — |

Both repetitions: model `on_topic = off_topic`.

### What produced 83.33%
Six members were compared across repeats (4 for b2-006, 2 for s2-f01); five agree; the only disagreement is **s2-f01 / E1 / "O(log n)" (essential)**. It differs *before* the gate (model: `states_incorrectly` vs `not_stated`) and after it (`unverified` vs `not_stated`), so the pre-gate and post-gate agreement are both 5/6.

### Classification
* **Model judgement problem (primary).** In repetition 0 Qwen described an *omission* ("Does not state time complexity") but filed it as an *error*, in spite of the prompt's "omission is never an error", and cited no claim. A 7B model mislabelling absence as wrongness is precisely the failure the gate exists for.
* **Gate: worked as designed.** The accusation had no supporting claim id, so it became `unverified`; the candidate was never recorded as having stated something wrong (no `incorrect` outcome exists in either run).
* **Not harmless in the derivation, harmless in the final status.** Repetition 0 left completeness undetermined; repetition 1 verified the essential concept missing and gave completeness 0. Both abstained (correctness is undetermined in both), so the final status did not flip. If correctness had been determinable, this would have flipped a completeness level.
* The schema permits `states_incorrectly` with an empty `claim_ids` list. Requiring ids for that state would remove this failure class, but it is a prompt/schema change, so it is listed under proposals, not applied.

## 2. Why the off-topic answer abstained
| Category | Applies? | Evidence |
|---|---|---|
| Off-topic answer confirmed by available evidence | **Yes** | model `off_topic` in both reps; deterministic lexical overlap with question/requirement terms = 0.00 (< 0.15); the supporting concept verified `not_stated`; in rep 1 the essential concept also verified `not_stated`. Relevance = 0 in both reps. |
| Empty / non-substantive | No | It is a substantive statement about a different topic. |
| Genuine insufficient verification | Partly, rep 0 only | E1's verdict was rejected by the gate (see above). |
| Provider or schema failure | No | both calls valid; `error: null`. |

Abstain reasons: rep 0 "correctness undetermined; completeness undetermined"; rep 1 "correctness undetermined". Correctness has nothing to rate because no statement about a listed requirement was verified either way, and the frozen rule is *any undetermined dimension => abstain*.

**Deterministic low score or abstention?** The engine already contains a rule (3C-1): relevance 0 caps the score at 10. I enumerated every resolution of the undetermined dimensions for both repetitions (correctness 0–4, completeness 0–4, relevance 0, reasoning 4 by convention): every combination ends at exactly **10**. So the abstention hides no real range here. Arguments for scoring: the low score would rest on verified, two-signal evidence rather than on missing evidence, and an app that returns nothing to an off-topic answer gives the learner no signal (the legacy evaluator returned 0). Arguments for abstaining: it is the one behaviour that can never be called an unsupported penalty, it matches the frozen rule, and one example is not a basis for changing policy.
**Proposal P1 (needs your separate approval; NOT implemented):** a "determinate score" refinement: abstain only when the set of possible scores over all resolutions of undetermined dimensions contains more than one value. Related to P1: the reasoning convention (below) would give an off-topic answer 15 points before the cap; only the cap hides this.
The frozen threshold (abstain rate <= 40%) is unchanged. The pilot's 50% is 2 of 4 rows, both from the single off-topic answer, and the pilot is partial.

## 3. Audit of b2-006's 100/100 (both repetitions identical)
| Requirement | Cited claim | Does the cited text show more than the name? | Lexical check of the cited claim |
|---|---|---|---|
| E1 convolutional layer (essential) | c1 (definition of a CNN via convolution in a layer) | It states the defining property, not just the term; the stronger sentence (c2, "A convolutional layer has…") was not the one cited | words "convolution"/"layer" present, but the crude stemmer does not conflate "convolutional" with "convolution", so the cited claim does **not** pass the lexical check |
| E2 filters (essential) | c2 | Yes: learnable kernels, sliding, dot products with patches | passes |
| S1 feedforward neural network (supporting) | c1 | States it; naming plus a definition | passes |
| S2 dot product (supporting) | c2 | Yes: names what is computed | passes |

* **Dimension derivations:** correctness 4 = "4 statements verified correct, none incorrect"; completeness 4 = "2/2 essential demonstrated"; relevance 4 = "verified credit; lexical overlap 0.235"; reasoning 4 = "question does not call for a mechanism or trade-off; full marks by rubric convention".
* **Naming vs understanding:** not naming-only here (E2/S2 are explanatory, E1/S1 rest on a defining sentence). But both essential labels are short terms that any competent one-paragraph answer will satisfy, so completeness measures coverage of terms.
* **Reasoning 4/4 is a convention, not evidence** (15 of the 100 points). The engine would give the same to a weak answer to this question.
* **Confidence "high":** the rule yields "high" when no verdict is unverified and no soft flag exists; the "AI-reviewed, not human-verified" scope flag is treated as informational and does not reduce it. So "high" means *internally consistent*, not *validated*. It is optimistic while the verifier is unvalidated.
* **Mechanically consistent, not semantically validated.** All evidence ids exist and no credit rests on an invented quote, but the only judgement that the claims *state the concept correctly* came from Qwen. The gate checks existence, not meaning, for credits; the lexical cross-check applies to `not_stated`, not to credit. The score was not adjusted.
* **Legacy comparison (observation about evidence, not accuracy):** legacy gave 75 with completeness 3 and correctness 3 while listing **no** missing concepts and no errors; its rationale says it "lacks some key concepts" but names none. That penalty carries no checkable evidence. Whether 75 or 100 is right needs the human review.

## 4. Performance and resources (Windows, GTX 1650 Ti 4 GB, 15.9 GB RAM, Ollama 0.32.13, qwen2.5:7b Q4_K_M)
| Item | Observation |
|---|---|
| Cold load | warm-up 65.3 s, **then** the first modular call loaded again: load 70.7 s inside a 103.2 s call |
| Why | the warm-up used the default context (Ollama reported `context_length` 4096), the experiment uses 8192, so the first chat reloaded the model (defect D1) |
| Warm modular call | 15.0, 17.8, 28.4 s (n = 3); decode 7.5–8.4 tokens/s; prompt processing about 210–284 tokens/s |
| Warm legacy call | 48.4 and 102.8 s (longer replies, 323–564 tokens at 6.6–7.1 tokens/s) |
| Reported "median modular latency 23.1 s" | includes the cold call; warm median is 17.8 s |
| Model placement | 5.4 GB, **58% CPU / 42% GPU** at 8192 context; GPU memory in use 2.8–3.5 GB of 4 GB (about 1.1 GB of it was already used by other programs before the run) |
| RAM | 15.9 GB total; **1.7 GB free before**, 0.21–2.70 GB free while running (lowest at model load); no OOM or provider error |
| GPU utilisation | 0–100%, mostly 10–35% (CPU-bound decode) |
| Pilot wall time | 316 s for 6 evaluations (about 103 s of it avoidable reload) |

**Full-run estimate** (83 verdicts over 20 answers; per-call time modelled from the warm pilot rates; wide uncertainty): modular x2 about 17–27 min, legacy x1 about 16–34 min, plus 1–2 min load: **about 35–62 min, most likely ~45 min**. Uncertainty: only 3 warm modular and 2 legacy observations; larger prompts and the 7-verdict question will take longer; background load changes it.
**Safe/practical?** Practical (about an hour); safe with caveats: the pilot ran without failure but free RAM got as low as 0.21 GB, so close browsers/IDEs first (the script warns below 6 GB free but continues). Results are written after every call, so Ctrl+C keeps what has run (there is no resume). No model download, no paid API.

## 5. Freeze and acceptance integrity
* **Original freeze intact:** 44 files (all modular and legacy evaluation code, the prompt-bearing adapter, scope sidecar and manifest, sample, expectations, review sheet, criteria, v1 manifest, runner, analyzer, protocol) are **byte-identical** on your device to what was frozen (compared by SHA-256 against the committed copies; the stage3c2 data files also show a modification time of 11:30, before the pilot started at 11:34). The manifest hash recorded inside the pilot's `results.json` equals the manifest on disk.
* **No tuning from the pilot:** no prompt, gate, rubric, weight, sample or threshold was edited; the only changes are the new v2 files below.
* **Acceptance criteria unchanged** (hash equals the frozen value, and the v2 test asserts the v2 tooling contains none of the threshold keys).
* **Partial run labelled partial:** `meta.partial_run = true` and the decision line says "PARTIAL RUN: not the frozen experiment; no decision". Weakness found: the v1 analysis table still printed bare PASS/FAIL rows for a partial run. The v2 analyzer prints `NOT_EVALUATED_PARTIAL_RUN (would be FAIL)` instead.

## 6. Defects, fixes, and what was deliberately left alone
| # | Finding | Type | Action |
|---|---|---|---|
| D1 | Warm-up context mismatch causes a reload inside the first measured call | Implementation defect (timing only) | **Fixed** in `scripts/stage3c2_run_v2.py` (warm-up sends the frozen `num_ctx`; prints a warning if Ollama still reports another context) |
| D2 | Partial-run criteria shown as bare PASS/FAIL | Reporting defect | **Fixed** in `audit/evaluation/stage3c2_analyze_v2.py` |
| D3 | Repeat agreement is only reported after the gate | Missing diagnostic | **Added** (informational pre-gate figure + mismatch table + cold-call detection + warm latency); the frozen criterion is unchanged |
| P1 | Abstain although the score is determinate under the existing cap | Policy | proposal only |
| P2 | Reasoning gives full marks "by convention" when not expected (15 free points) | Policy | proposal only (e.g. treat as not-applicable and renormalise) |
| P3 | "high" confidence ignores that the verifier and tiers are unvalidated | Policy | proposal only (cap at "medium" until human validation) |
| P4 | `states_incorrectly` allowed with empty claim ids; model confused omission with error | Prompt/schema | proposal only; would be a new prompt version and needs a new sample |
| P5 | Lexical guard is a crude suffix stripper ("convolution" != "convolutional", "regularization" != "regularisation"), so a wrong `not_stated` can slip past the guard on a derived word, i.e. an unsupported missing-concept penalty | Gate recall | not changed (frozen code); human review of every `missing` penalty in the full run is the safeguard |

### Versioning
v1 stays byte-identical and still verifies. v2 (`3c2.1`) is a layer: `scripts/stage3c2_run_v2.py`, `stage3c2_run_v2.ps1`, `stage3c2_freeze_v2.py`, `audit/evaluation/stage3c2_analyze_v2.py`, `data/evaluation/stage3c2/freeze_manifest_v2.json`. The v2 manifest records that the sample, scope, prompt, modular and legacy code, model settings and acceptance criteria are unchanged and re-verifies them (and the v1 manifest) before every run. The v1 runner is therefore *superseded for future runs*, not edited.

## 7. Tests (offline)
15 new regression tests (`tests/evaluation/test_stage3c2_pilot_diagnosis.py`): pilot facts (partial label, the single mismatch, mislabelled omission, gate rejection, off-topic cause and the unique capped score, evidence ids for the 100/100, reasoning convention, stemmer limitation, cold-load detection, context defect) and v2 behaviour against a fake Ollama that simulates the reload (defect reproduced with v1; absent with v2; warning path; refusal on drift; v1 intact; nothing that defines the experiment changed).
Results: evaluation suite **359 passed** (was 344); retrieval + evaluation (`rag_venv`) **494 passed, 3 skipped**; app **77 passed, 5 skipped** (unchanged). No failures.

## 8. Recommendation
**Fix the demonstrated defect and create the new experiment version (done), then run the full 20-answer experiment under 3c2.1.** Do not apply P1–P5 before the run (that would be tuning on the pilot); they are recorded so the full run can show whether they matter at 20-answer scale.
Before running: free as much RAM as you can; ideally fill in the blind review sheet in parallel so that human criteria can be evaluated afterwards. Command: `powershell -ExecutionPolicy Bypass -File scripts\stage3c2_run_v2.ps1`. I will not call Ollama until you approve.

# Stage 3C-2 experiment protocol (FROZEN before any real-model run)

Status: written and fingerprinted (`data/evaluation/stage3c2/freeze_manifest.json`) before the model has been run even once. The runner refuses to start if any frozen file has changed.
All labels, concept tiers, reference answers and expectations are AI-authored. No human has reviewed any of them.

## Question this experiment asks
Can a small local model (qwen2.5:7b) act as the *concept verifier* behind the Stage 3C-1 evidence gates, and does that reduce unsupported scoring penalties compared with the single-call evaluator, on the scope-eligible questions? It does **not** measure general grading accuracy.

## Frozen inputs
* **Sample:** 20 answers on 8 of the 16 scope-eligible questions (smi-0064, 0118, 0198, 0314, 0449, 0451, h0016, l0002): 18 from the fresh bench_v2 plus 2 fresh answers written for this stage. Kinds: correct x2, concise-sufficient x3, valid-alternative x3, partial x3, incorrect x2, hallucinated/contradicting x2, prompt-injection x3, off-topic x1, non-substantive x1. Selection was rule-based (quota per kind, spread across questions) and the rule is in `audit/evaluation/stage3c2_build_sample.py`.
* **Why 8 of 16 questions:** bench_v2 has answers only for these eight; no new corpus questions are created. The other 8 eligible questions are untested here.
* **Not used:** the tuned B01–B43 cases (stage 3B). One honesty note: the modular injection patterns were extended in 3C-1 after the benchmark-contract test showed b2-032 slipped through. b2-032 is not on an eligible question and is not in this sample, but the benchmark is therefore not 100% "unseen by the code".
* **Scope:** `scope_v1.jsonl` (sha in the manifest). Only eligible records can be scored; AI-reviewed tiers are never treated as human-verified.
* **Verifier prompt:** `3c2.v1` (`src/evaluation/modular/qwen_verifier.py`): one structured call per answer; per-request JSON schema with closed enums for requirement ids, members and claim ids; every verdict field required; four states (`states_correctly`, `states_incorrectly`, `not_stated`, `unverified`).
* **Rubric / gates:** engine `3c1.0` unchanged (40/30/15/15, abstention, derivations). The model never outputs a score, level or feedback.
* **Model configuration:** qwen2.5:7b, local Ollama, temperature 0, seed 7+repeat, num_ctx 8192, 1800 output tokens, 300 s timeout, no downloads, no paid APIs.

## Procedure (single execution, no tuning)
1. Verify the freeze, build all prompts offline (dry run), load the model (model-load time recorded separately from per-answer latency).
2. Modular pass x2 (seeds 7 and 8) over the 20 answers, then the legacy single-call evaluator x1 on the same answers with the same model settings and the same reference material (no retrieved supporting snippets, so only the architecture differs). Legacy uses its schema-constrained mode as in Stage 3B v3.
3. Record per answer: raw reply, trace, validated verdicts with rejection reasons, outcomes, score derivation, deterministic feedback text, latency, `ollama ps` (VRAM) and GPU/RAM snapshots; a PowerShell sampler records RAM/GPU every 10 s.
4. `audit/evaluation/stage3c2_analyze.py` evaluates the mechanical criteria in `acceptance_criteria.json`.

## Criteria and decision rule
Fixed in `data/evaluation/stage3c2/acceptance_criteria.json` before the run. Mechanical criteria can be evaluated now; human-label criteria are reported `PENDING_HUMAN` until a person completes `review/blind_review_sheet.csv`. If every mechanical criterion passes and no human labels exist, the only permitted conclusion is **"exploratory behavioural readiness"**, never grading accuracy. If any fails, the experiment is reported as a failure of that criterion.

## How each Phase-7 question will be answered
| Question | Evidence | Needs human labels? |
|---|---|---|
| Reduces unsupported penalties | modular unsupported completeness penalties = 0 by criterion; legacy missing-concept claims listed beside it | to say a legacy penalty was *wrong*: yes |
| Handles concise answers | outcomes for the 3 concise-sufficient answers | to say credit was *right*: yes |
| Accepts correct alternatives | outcomes for the 3 valid-alternative answers | yes |
| Identifies factual contradictions | surviving `states_incorrectly` verdicts on the 2 hallucinated + 2 incorrect answers | to say they are *real* errors: yes |
| Explainable scores | every scored dimension has a derivation (criterion) | no |
| Abstains appropriately | abstain rate criterion + recorded reasons | whether abstention was *warranted*: yes |
| Practical on this hardware | latency, VRAM/RAM, failures | no |

## Rules during and after the run
* No change to prompt, gate, rubric, sample or thresholds after seeing results, and no re-scoring of these 20 answers after any change. Any change needs a new frozen sample and a new approval.
* Failed or empty model replies are reported as failures, never as scores.
* The results must not be quoted as grading accuracy. AI expectations are shown beside results for reading only.

## Known limitations going in
* Several scope labels are single terms rather than propositions (e.g. "Dijkstra's algorithm", "shortest path", "O(log n)"). A verifier may credit an answer that only *names* a concept; the human reviewer is asked to flag this.
* n = 20, one model, two seeds: no statistical claims.
* Code/SQL is not executed by the evaluator; correctness of code answers is flagged, not proven.
* Deterministic feedback is recorded for inspection; no LLM feedback is generated in this experiment.

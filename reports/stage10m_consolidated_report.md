# Stage 10M: evidence-based final corrective cycle

**Read this first.** Stage 10 is **not** complete. (1) The real Windows run `tmp/stage10_opps_20261021_145035/results.json` was **not available in this environment**, so no case of that run was traced from its own recorded questions; every case-level statement below is built from the symptoms you described plus the code and the earlier recorded run 2 (`reports/stage10_windows_evidence_2/`), and says so. (2) **The three Windows test failures were not reproduced here**; I found and fixed two real defects near them, but I cannot show that those fixed the three failures. (3) No Ollama here: **every number below is a scripted stand-in or a unit test, not model performance.** (4) Nobody has rated anything. No commit, staging, push or deployment was done. The 40-case fixture, labels, hash and scoring rules are unchanged.

## 1. Windows test failures (Task 3)

| item | status |
|---|---|
| Failing tests: `..._recalled_several_questions_later...`, `..._refresh_returns_the_same_questions_and_restart_keeps_the_memory`, `..._memory_stage_metric_exists...` | **Not reproduced.** All pass here (and under 12 hash seeds). The three share one thing: a full scripted engine run (`sim.run` + `OE.MED`) that must reach memory stage `used`. |
| Hypotheses tested and **eliminated** here | candidate-question ranking (BM25, reversed, none), a Sentence-BERT-like dense memory embedder at three semantic floors, `PYTHONHASHSEED`. The memory question still appears. |
| **Confirmed defect 1 (code)** | `sim.offline_engine` used the process-wide retrieval service, which switches to Sentence-BERT + FAISS wherever installed. The scripted tests therefore ran different code paths on Windows and in the sandbox. Now BM25-only (`sim.bm25_search`), guarded by a test that fails if the semantic path is touched. |
| **Confirmed defect 2 (code)** | `legacy scoring failed: 'bert'`: a stored session says "scorer available", but the scorer registry is per process; after a restart or in another worker `self._scorers["bert"]` raised `KeyError`, so every legacy score became "unavailable". Fixed with a lazy `_load_scorer`; tests cover reload after restart and a clean "unavailable + reason" when loading fails. This is a **production regression fix**, and a plausible contributor to the restart test, but it does not by itself explain `used` missing. |
| Environment pin | the Stage 10J test module now deletes `SMART_DEMO_MEMORY_SBERT`, `..._SEMANTIC_FLOOR` and `..._TRUST_MODEL_SKIP` for every test. |
| Self-diagnosing tests | the three tests now print follow-up indices, memory ids, stage, fallback class, retrieval gates and retrieval mode when they fail. |
| **Still requires Windows** | run `.bot\Scripts\python.exe scripts\stage10m_windows_test_diag.py > diag.txt` and `.bot\Scripts\python.exe -m pytest tests\app\test_stage10j_memory_contract.py tests\app\test_stage10m_platform_independence.py -q`; send `diag.txt` and any failure text. I will not claim the cause until that output exists. |

## 2. Validation repairs (Task 1): false rejections and false acceptances, separately

Code changes are in `src/demo/followup_llm.py`. Each row says what is **confirmed by code inspection** and what is **hypothesis**.

| case | symptom you reported | finding | change | status |
|---|---|---|---|---|
| T01 | loss-minimisation question rejected `evidence:none_verified` | **Confirmed mechanism**: `answer_quote` had to be a verbatim substring; a paraphrased quote voided a good question. (That it was a paraphrase is a hypothesis; run 3 replies were not available.) | `nearest_evidence`: the verbatim answer sentence that shares ≥50% of the quote's words (or ≥⅓ plus a word the question adds) replaces it, noted `evidence:quote_replaced_by_code`. A quote matching nothing is still rejected. | false rejection fixed |
| T01 (run 2) | accepted: "How does the model handle the difference between classification and regression…" | **False acceptance by usefulness**: both concepts were already explained; the target (loss minimisation) was open. It passes because `deepen` about the candidate's own claim is allowed (Stage 9D tests that on purpose). | not changed; reported. A question can be valid yet off the gap; only a person can rate usefulness. | **open** |
| T02 | atomicity/consistency question: meaningful probe or ACID confusion? | Concepts: atomicity [explained], consistency [absent], isolation [absent]. The question names the open concept (consistency) through a covered one. It is not an ACID confusion; it is a relationship question. My judgement: acceptable, mildly leading. Run 2 rejected it as "already covered" (false rejection, fixed in 10K). | none | judgement, not rated by a person |
| T03 | valid "worst-case" rejected as a novel term | **Confirmed**: `_TECH_TOKEN` matches any hyphenated word; "worst-case" was in none of the allowed text. | plain compounds are accepted when every part is an ordinary word (list `_PLAIN_PARTS`) or already in the allowed text. | false rejection fixed |
| T05 | `E1` still leaks | **Confirmed gaps**: the sanitiser matched only upper-case ids that are in the concept list. Lower case, or an id the model invented, passed through. (Why run 3's `E1` survived is not confirmed.) | ids of the E/S/G/K/m schemes are replaced in any case; an id that cannot be mapped and is not in the candidate's own words is rejected `question:id_leak`. A token like `L2` that the candidate said is allowed. | fixed for those forms |
| T06 | repair changes wording but fails verification | Same quote mechanism as T01 (hypothesis for T06 specifically). | as T01 | likely fixed, unverified |
| T08 | question about correlated features, not the gap | **Confirmed**: probing an "open" concept was accepted if the question shared a word with any open concept's label or members, including words the candidate had already said ("features"). | for an absent concept, words the candidate already said no longer count as evidence of probing it. A different open concept than the code's TARGET is allowed and noted `target:other_open_concept`. | false acceptance reduced |
| T09 | restates the answer | The restate check works; the repair was too weak (10K, quote the rejected question). No further rule added. | none | model-quality problem, **open** |
| T10 | cross-validation and imbalance rather than metrics | The question named an open concept (imbalance), so it passes by design. Requiring the exact TARGET broke valid Stage 9C/9D questions and was **reverted**. | note `target:other_open_concept` only | **open**, judgement call for you |
| T11 | valid paraphrase rejected as a novel term | **Not identified.** Which token fired is unknown without the run. The three exits (plain compound, acronym of an allowed phrase, same-domain bank vocabulary) cover the likely classes. | as T03/M06 | **unverified** |
| T12 | accepts a wrong premise (Type I error vs false positive) | **Confirmed gap**: nothing checked the question's presupposition. | `knowledge/concept_equivalences_v1.json`: 14 hand-written identity groups (e.g. Type I = false positive = false alarm). A question that asks how members of one group *differ* is rejected `question:false_premise`. Pairs not listed are not judged. | fixed for listed pairs only |

No LLM accuracy judgement and no semantic-similarity "correctness" score was added. The legacy-score warning above is unrelated to question quality.

## 3. Memory-aware generation (Task 2)

| case | finding / change | status |
|---|---|---|
| M01, M03, M07 | generation problems (memory offered, not used). Existing memory mode and nudge stay; no new generation logic. | **open on a real model** |
| M02 | citation valid; question quality is a human judgement. Not rated. | open |
| M04 | `E1` leak: fixed as T05. `memory_id none` is a model choice. | partly fixed |
| M05 | **Confirmed distortion**: an explanation's `subject` is the bank question's *topic label* ("Linear and logistic regression"), so the lead "Earlier you explained Linear and logistic regression" claimed more than the candidate said (only logistic regression). Now the label is used only when every distinctive word of it occurs in the candidate's text; otherwise the lead quotes their words: `Earlier you said “Logistic regression predicts the probability of a class …”.` | fixed |
| M06 | **Confirmed**: the retry lost the citation because the repair text never mentioned the statement. A memory-mode repair now says `Keep memory_id "<id>" …` and still shows EARLIER. The rejected word "k-nearest" is accepted only if it is in the same-domain bank vocabulary; otherwise it stays rejected. Test: grounded attempt → wording rejection → repaired attempt keeps id, lead and stage `used`; a retry that drops the memory is reported `declined`/`not_used`, never success. | fixed (mechanics) |

Zero fabricated references and session isolation are unchanged and still tested (10J tests). No memory is attached to a question to pass a metric; the stored-word and lead-in rules are as before.

## 4. Payload and retry (Task 4)

- `skip_reason` is no longer a required schema field (prompt `10.fu7`). An ask that still carries one is normalised: the decision wins, the proposal carries no skip reason, and `payload:ask_with_skip_reason` is recorded.
- `skip` + a question is still a rejection, with a targeted repair, then a fallback classed `payload_inconsistent`.
- Terminology rejections are repairable and are not a safety class; a terminology reason next to a safety reason is never repaired (tested).
- At most two model calls; the repair keeps the TARGET and the memory statement.

## 5. Tests (Task 5)

New: `test_stage10m_platform_independence.py` (7), `test_stage10m_validation_and_retry.py` (38). They cover: a valid paraphrase-style wording accepted, an invented term still rejected, acronym and domain-vocabulary exits (and the wrong-domain refusal), the quote repair and a fabricated quote still rejected, id leaks in several forms, a wrong premise rejected and a right one accepted, payload consistency, memory kept across repair, faithful leads, T01–T12 through the pipeline, and the trace script. Existing tests changed **only** for deliberate contract changes: the schema's required list (3 tests), prompt version `10.fu7` (1 test).

| check | result |
|---|---|
| full `pytest tests` | **1372 passed, 8 skipped, 0 failed** (sandbox, Linux, Python 3.12, no Sentence-BERT, no Ollama) |
| ruff (CI scope) | clean |
| `check_integrity.py` / `check_versions.py` / `verify_mlops.py` | pass / 11 passed / nothing failed |
| frozen 40-case fixture hash `59e92f47…0737` | unchanged (pinned by two tests) |
| browser journeys | **not run** (Playwright not installed here) |
| scripted benchmark (stand-in model) | 23/23, strict skip 10/10, memory_inappropriate 6/6, 17/17 gates; **mechanics only** |

Reported separately (`reports/stage10m_eval/results.md`): scripted LLM-path technical 12/12, deterministic behavioural probes 4/4, grounded memory 7/7, strict skip 10/10 (B07 safety-only, unchanged), fallbacks 0 (stand-in), human-rated: **unrated (0 items rated)**. The real Windows 10J–L numbers you gave (10/23, 3/12, 3/7, 20 fallbacks, 11 repairs / 2 successful) are quoted, not re-measured.

## 6. Files changed

`src/demo/followup_llm.py`, `src/demo/memory.py`, `src/demo/engine.py`, `src/demo/sim.py`, new `src/demo/knowledge/concept_equivalences_v1.json`; scripts `stage10m_trace.py`, `stage10m_windows_test_diag.py`; tests `test_stage10m_*.py`, `test_stage10j_memory_contract.py`, `test_stage10d_followup_repair.py`, `test_stage9c_followup.py`, `test_stage9d_followup_perf.py`; `.github/workflows/ci.yml` (trace step); `docs/STAGE10_MODEL_AND_POLICY.md` §13; outputs under `reports/stage10m_*` and `docs/stage10_review_m/`. ZIP: `stage10m.zip` (project-relative).

## 7. Limitations and what is not claimed

- Real-model quality of prompt `10.fu7` is **unmeasured**; the 10/23 result stands as the latest real number.
- Task 1's trace needs run 3's `results.json`: `python scripts/stage10m_trace.py --results tmp\stage10_opps_20261021_145035\results.json` writes `reports/stage10m_trace/trace.md` with every case's answer, concept states, TARGET, recorded questions, Windows rejection codes and the current rules' verdicts, leaving "rejection correct? question useful?" for a person.
- The "vetted bank vocabulary" exit lets a model name a standard technique the candidate did not; it is blocked if the term is not in the same-domain bank, and the exception is logged, but it is a loosening and deserves human review.
- T10, T09, T11, M01–M03, M07 and every naturalness question depend on a real model and a human rater.
- The equivalence list guards 14 groups only.
- B07 remains a fixture defect awaiting your approval.

## 8. Windows verification

1. `.bot\Scripts\python.exe scripts\stage10m_windows_test_diag.py > diag.txt`
2. `.bot\Scripts\python.exe -m pytest tests -q` (send any failure text with the `_why` trace)
3. `.bot\Scripts\python.exe scripts\stage10_verify_real_stack.py --opportunities --models llama3.2:3b --mlflow --sbert`
4. `.bot\Scripts\python.exe scripts\stage10m_trace.py --results <new results.json>` and `scripts\stage10l_compare.py`
5. Rate the blind sheet (two raters), then `scripts\stage10l_review_summary.py <dir>`.
Stage 10 can be called complete only when step 2 is green and step 3 meets a requirement you accept on a real model.

# Stage 10G + 10H + 10I: consolidated report

**Read this first.** The Windows numbers in section 1 are real (llama3.2:3b on your machine, Ollama 0.32.13, prompt 10.fu4). Every number about the *repaired* code is **scripted/mock**: this sandbox has no Ollama, so the repairs are **unverified on real Ollama**. The 80% target is **not** claimed. Nothing was rated by a human, and nothing was committed, staged, pushed or deployed. Windows revalidation is required (section 6).

## 1. Root cause, from the real `results.json`
Per class, not just the 52.2%:

| class | n | success | accepted | model skipped | fell back |
|---|---|---|---|---|---|
| expected | 16 | 8 | 8 | 6 | 2 |
| skip | 11 | 8 | 4 | 0 | 5 |
| memory_use | 7 | 4 | 6 | 0 | 1 |
| memory_inappropriate | 6 | 6 | 4 | 1 | 1 |

Skip reasons: `covered` x7. Rejections: `novel_terms` x3, `not_tied_to_answer` x1, `accusatory` x1, 3 prefilters. 0 truncated, 0 fabricated memory references, 0 provider failures. Full case table: `reports/stage10_ghi_eval/windows_failure_analysis.md`. The 14 misses fall into five causes, and **none was a legitimate safety rejection**:

| cause | cases | evidence | verdict |
|---|---|---|---|
| Model skipped an eligible follow-up as "covered" | T05, T06, T07, T08, T10, T12 (6 of 8 expected misses) | 2-3 of 3-4 shown concepts carried "exact-words hint: not found" in the prompt | model-quality failure: it ignored the hint on 6 of 6 |
| Model asked although everything was covered | S02, S03 (S01 nearly) | S02/S03: 4 of 4 concepts "found"; S01: "minimises a loss" vs "loss minimisation" | model ignored the hint (S01: hint too literal) |
| Concept id leaked into the question text | T02, M04 | rejection string literally `novel_terms:E2` | prompt design (ids looked like terms) |
| Weak but rule-accepted questions | M02, M07 (and T01, T09, T11 counted as "useful") | texts in the review sheet: yes/no, "what does it mean ...", restating the answer | missing validator rules + model quality |
| Unresolved | T03 (`not_tied_to_answer`), M02/M07 (was a memory offered?) | the rejected text and the offered memory ids were not recorded | **undetermined**; now recorded per case |

Two things the aggregate hid: (a) the 12 "useful" results included yes/no and definition re-asks. Replaying the 22 real questions through the new rules, **3 of the 12 (T01, T09, T11) would now be rejected**, so the real quality was lower than 52.2%. (b) Memory retrieval itself worked: M01, M03, M05, M06 cited valid stored memories with real Sentence-BERT (`loads: 1`, `cache_hits: 12`); the memory misses were wording/ID problems, not retrieval (M02/M07 offered-or-not is unknown).

## 2. Changes (10H), each tied to a cause
- **Code decides coverage, the model writes wording** (`followup_llm.py`, prompt `10.fu5`): all shown concepts covered (exact words or word stems) -> skipped by the rules, model not called (also saves a call); otherwise code picks one `TARGET` concept and the prompt is ask-only. A model `skip` is honoured for `off_topic` / `nothing_to_add`; `covered` while a concept is open is overruled (switch: `SMART_DEMO_FOLLOWUP_TRUST_MODEL_SKIP=1`). This is not "force a follow-up every turn": covered, unrelated, injected and off-topic answers still get none.
- **Wording rules:** `closed_yes_no`, `what does it mean` re-ask, `restates_answer`; concept ids in the question are replaced by labels. Safety rules are unchanged and none was relaxed.
- **One repair attempt** for fixable wording rejections only, deadline permitting; never for safety rejections (invented memory, injection, accusation, bad JSON, timeouts).
- **Memory:** citation rules unchanged (offered id, traceable to a stored candidate statement, fabricated "earlier you said" rejected); the prompt tells the model the listed statements were selected as related.
- **Observability:** engine log gains `decided_by` and `attempts`; metrics `smart_followup_skips_total{by}` and `smart_followup_repairs_total`; the Windows script records per-case rows (reasons, skip reason, offered memory ids, the model's rejected replies on the synthetic set), Ollama version, `/api/show` details and the nine dimensions. MLflow still gets counts only.
- Prompt kept inside the 9D size budget (< 450 estimated tokens). `llama3.2:3b` remains the baseline; no other model was evaluated because nothing observed is a limit the model cannot overcome.

## 3. Evaluation (10I)
The 40-case set, its labels, eligibility rules and scoring formula are **unchanged** (a test pins the file hash). 34 new regression tests in `tests/app/test_stage10g_windows_regressions.py` use the real Windows question texts: 9 bad ones must be rejected for the stated code, 3 good ones must not be caught, plus rule-skip, overrule+repair, no-repair-for-safety, deadline, opt-in, and a whole-interview engine test.

Scripted stand-in on the unchanged set (**mock, not model performance**):

| | Windows real, 10.fu4 | scripted stand-in, 10.fu5 |
|---|---|---|
| eligible useful+valid | 12 / 23 = 52.2% | 21 / 23 = 91% (plumbing check) |
| skip class correct | 8 / 11 | 11 / 11 (5 by the rules, model not called) |
| memory_use cited valid | 4 / 7 | 5 / 7 (M02, M04 need semantic retrieval) |
| fabricated memory references | 0 | 0 |
| faulty-model suite (9 behaviours) | not run | 0 accepted |

The stand-in follows the hint exactly and cannot ignore it, so the 91% proves the wiring and the rules, not that llama3.2:3b will obey the new prompt. The nine dimensions (follow-up generation, skipping, evidence-supported memory, technical relevance, behavioural relevance, wording proxies, repetition, fabricated claims, latency/fallbacks) are reported separately in `reports/stage10_ghi_eval/results.md`; wording is form-only (open question, length), **naturalness needs the human sheet** (`docs/stage10_review_ghi/`, unrated).

Checks: full regression **1263 passed, 8 skipped**, browser journeys 29 passed, `ruff` clean, integrity OK (no frozen drift), versions 11/11. Privacy: logs and metrics hold codes and counts; the raw-reply sink is off in interviews and only used by the benchmark on synthetic text.

## 4. Behaviour changes to know about
1. A fully covered answer now never reaches the model and gets no follow-up (before: sometimes a question that ignored coverage).
2. If the model keeps answering "covered" on an open concept, the interview falls back to the existing deterministic follow-up after one repair, so such turns count as fallbacks, not successes.
3. Stem-level coverage may skip a turn where the candidate used a related word form without understanding it; exact words can't see that either.

## 5. Remaining risks
- **Unverified on real Ollama:** whether 3B obeys ask-only + TARGET, whether the repair retry recovers (it adds about 2 s on that path only; warm median was 1.95 s), T03's cause, and M02/M07's memory offers.
- The new wording rules are the author's reading; a good yes/no probe would be rejected. Review `rows[].debug` for false rejections.
- Exact-word/stem coverage can't tell a fluent wrong answer from an alternate valid one (T05/T06 style answers get a probe, which is intended).
- M02/M04-type cases need semantic memory retrieval; topic-link floors remain uncalibrated for Sentence-BERT.
- 23 opportunities is a small sample; temperature 0 with seed 7 makes repeats near-identical, so extra runs add little.
- No human validation of any question.

## 6. Windows PowerShell validation
```powershell
cd D:\Projects\SMART-MOCK-INTERVIEW
.bot\Scripts\python.exe -m pytest -q
.bot\Scripts\python.exe scripts\stage10g_replay_windows.py                       # no model: reproduces the failure table from the frozen evidence
.bot\Scripts\python.exe scripts\stage10f_eval.py                                 # scripted gates, no Ollama (writes reports\stage10_def_eval; use --out/--transcripts/--review to keep both)
.bot\Scripts\python.exe scripts\stage10_verify_real_stack.py --opportunities --models llama3.2:3b --mlflow --sbert
.bot\Scripts\python.exe scripts\stage10_verify_real_stack.py --models llama3.2:3b --runs 2     # interviews with partial answers
```
The real run has no shortcuts: it uses the same fixed set, the same rules and `FL.num_predict()`; it reads nothing from the scripted stand-in.
Fields to report from `results.json` / `summary.md`: `useful_valid_rate` (target 0.8), `by_class`, `dimensions` (all nine), `rule_skips`, `repair_attempts`, `repaired_ok`, `reply_truncated` (0), `quality_gates.fabricated_memory_references` (must be 0), `skip_reasons`, `rejection_reason_codes`, `cold_load_ms`, `first_call_ms`, `warm_latency_ms`, `memory_models` (loads about 1), `model_details`, `ollama_version`, `rows[]` (look at `outcome`, `reasons`, `debug`, `memory_offered_ids` for every miss). Then rate `review_sheet.csv` blind. If the rate is below 80%, send me `results.json`: `rows[].debug` will show exactly what the model wrote on each miss.

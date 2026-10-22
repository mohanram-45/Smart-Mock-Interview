> **Superseded by `reports/stage11t_repair_report.md` (2026-10-22).** Correction: the status line below says this pass was installed into `D:\Projects\SMART-MOCK-INTERVIEW`; it was not (the device still held the 11R files until 11T installed both passes together). Its blind sheet added the lead-in twice to recorded follow-ups and was withdrawn; use `reports/stage11_eval/stage11t_review/`.

# Stage 11S - Memory and Technical Correctness Repair

**Status: implemented and tested in the Linux sandbox copy, then installed into `D:\Projects\SMART-MOCK-INTERVIEW`. Not executed on Windows. No real model was called, so no acceptance rate is claimed for the repaired engine and nothing here shows the 80% target met. No git commits, pushes or deployments; no paid services.**

Baseline quoted from your run `tmp/stage10_opps_20261022_162322/results.json` (engine objective, prompt 11.obj2, llama3.2:3b): 18/23 = 78.3%, technical 12/12, grounded memory 2/7, strict skips 10/10, 0 fabricated references, 0 duplicated phrases, 0 payload inconsistencies, warm median 1668.7 ms, Windows suite 783 passed. Those are automated rule acceptances, not human-rated quality. I verified I could read that file and the installed source before changing anything (the four installed modules matched my copies hash for hash).

## 1. Confirmed root causes

| defect | what the trace showed | cause |
|---|---|---|
| T12 "a true null hypothesis is actually false" | target was `false positive`; the reference says "Type I error **is** a false positive" and the candidate had explained Type I error | the objective was a second name for something already covered, so the model had nothing new to ask and composed a premise out of answer words. Nothing checked the composed premise for self-contradiction. |
| T11 "learned representations compare to those found in hierarchical representations" | exact hit on the open target, engagement satisfied | no rule noticed that the other side of the comparison was the candidate's own wording for the target itself |
| T10 "metrics ... on the classes with the lowest and highest probabilities" | engagement passed on two words ("metrics", "probability") shared with a long multi-concept reference | engagement could be satisfied by one word pooled across all open concepts; nothing checked that the case the question turns on exists anywhere |
| T03 "... when the number of comparisons is found to be log n" | `value_probe` true: an open value concept plus cost words | a cost question counted as probing the value even when it stated the value |
| T04 filters/edges question | six words in a row from the answer | `repeats_answer_content` measures proportion, not copied runs, and a four-word answer defeats it |
| M01, M02, M03, M06 `memory_id: null` | `reference:unsupported:your_work` fired on "your spam classifier", which the candidate *had* described; `memory:uncited_reference` fired because no id was attached | the backing for a personal reference came from the one statement the **model** cited. With no id there was no backing, so a genuine reference looked fabricated and the id could never be attached — circular. |
| M01, M06 | `memory:restates_lead` | the question named the work, which duplicated the code-built lead; the engine refused the question instead of dropping the redundant lead |
| M01 | `memory:presupposes_use` on "How **would** evaluating ... inform ..." | the presupposition test ignored conditional phrasing |
| M04 "money transfers in your money transfers, and how does it ..." | accepted | no rule for a name pasted beside the words it was cut from, or for two questions in one turn |
| M07 "halving the sorted list ... of your search feature" | accepted, memory attributed | nothing checked that a technique from *this* answer was being attributed to work they only said they had built |
| M05 | generic MLE question not counted as memory use (correct), then "your logistic regression model" | the memory is an *explanation*; the prompt still told the model to say "your ...", and the explanation was treated as backing for owning a model |

## 2. Exact changes

- `src/demo/intel.py` — new: `equated_with_explained`, `target_premise`, `contradictory_premise` (+`_opposite_pairs` with morphological negation), `circular_contrast`, `repeats_answer_phrase`, `duplicated_subject`, `two_questions`, `invented_qualifier`, `value_stated`, `in_session`, `implies_unclaimed_use`, `distinctive_support`, `_linked_sentence_stems`, `SYSTEM_OBJ_IDEA`. Changed: `choose_target` (drops equated concepts), `engagement` (value probe may not state the value), `attribute_memory` (session check, conditional-aware presupposition, lead dropped instead of refused, unclaimed-implementation check), `build_prompt` (premise line; explanation memories get their own system prompt), `memory_nudge` (names the target; no "your" for an explanation), `progression_reasons`, `_REPAIR_V2`, `repair_instruction`, `OBJ_PROMPT_VERSION = 11.obj3`.
- `src/demo/followup_llm.py` — new `offered_support(ctx, own_work_only)` and `OWN_WORK_KINDS`; `unsupported_reference` gained an `own_work` backing set; `validate` backs references with the session's own offered statements and scopes `memory:uncited_reference` to statements other than the one the objective offered.
- `src/demo/opportunity_eval.py` — audit only: accepts a missing lead when the cited statement was offered, adds `implied_unclaimed_implementation` (also in `REF_AUDITS`) and an additive `implied_unclaimed_implementations` gate counter. Fixture, labels, denominators and scoring untouched.
- `scripts/stage11r_validator_compare.py` — `--baseline {stage11r,pre11r}`, an 11S shim, the 162322 run in the recorded pool, holdout4 in the pair sets, and a fixed case-dict copy bug that had corrupted one row.
- New: `src/demo/eval_data/stage11s_correctness_pairs_v1.json` (holdout4), `tests/app/test_stage11s_correctness_and_memory.py` (55 tests), `reports/stage11_eval/stage11s_review/` (blind sheet + key), `reports/stage11_eval/stage11s_validator_compare*.json`, `reports/stage11_eval/replay_11s/`, this report.
- Tests updated, with reasons: one Stage 11 example question ("How does atomicity in your money transfer handling ... relate to ensuring data consistency?") was itself an instance of the defect and was replaced by a conditional question about the open property; one asserted reason code moved; the Flask journey's stand-in now answers whatever the prompt names as the objective, so it tests plumbing rather than one wording.
- `.github/workflows/ci.yml` is not writable from here and is unchanged.

Integrations touched: the objective engine's own path only (`intel.run_objective` → `FL.validate` → `FL.final_gate` → `engine._llm_followup`). Stage 10N keeps its own profile; the shared safety checks (unsupported reference, duplicated phrase, id sanitising) apply to both.

## 3. Tests

- `tests/app/test_stage11s_correctness_and_memory.py`: 55 passed. Every question in section 1 is refused for the stated reason; one grounded counterpart per memory case is accepted with the id attached by code; each correctness rule has both the wrong shape and the right one; the five ownership conditions are tested one by one, including a wrong model-written id and a statement from outside the session.
- Whole application suite: **833 passed, 5 skipped** (`.bot` equivalent here: Python 3.12, no torch/Ollama). `ruff check src scripts tests`: clean. `scripts/check_integrity.py`: OK, no frozen file drifted; `stage10f_opportunities_v1.json` hash unchanged.

## 4. Validator comparison (offline, same questions, no model)

| set | good | false rejections 11R → 11S | bad | false acceptances 11R → 11S |
|---|---|---|---|---|
| fixture pairs | 12 | 1 → 1 | 13 | 2 → 2 |
| holdout | 10 | 5 → 5 | 12 | 0 → 0 |
| holdout2 | 10 | 5 → 5 | 10 | 0 → 0 |
| holdout3 | 15 | 2 → 2 | 27 | 1 → 1 |
| holdout4 (new) | 8 | 0 → 0 | 18 | 11 → 3 |

**The repair adds no false rejection on any existing set.** Against the recorded real-model questions that the rules had accepted (57 across the three runs): 41 accepted by 11R → 28 now, 13 newly refused, including every defect the brief names plus T01 (two questions), T09 and M05 (answer phrase handed back) and M07. Of the previously refused 50, none is newly accepted. Unsupported-reference controls: 22/22 still refused, 0 of 10 genuine references refused. Comparison against pre-11R is in `stage11s_validator_compare_vs_pre11r.json` (46 → 28 accepted, 18 newly refused).

Three bad questions in holdout4 are **not** detected, and I am not claiming otherwise: two contrast a curated concept with another curated concept that is not a rival of it ("revalidation compared with max-age"), which needs meaning rather than words; one has its second interrogative separated from its verb ("and which effect size would worry you?") — the wider pattern that caught it refused two good compound questions, so I kept the narrow one.

I also measured two stricter forms of the engagement test before rejecting them: target-only support words caught T10 but refused eight more good scenario questions, and two-words-from-one-concept refused seven and caught none. T10 is instead caught by `invented_qualifier`, which costs nothing on any set.

## 5. Memory engagement and provenance

Offline, with the repaired code: all seven memory cases accept a grounded counterpart with the id attached by code, the lead dropped where the question names the work (M01, M02, M03) and kept where it does not (M04, M05, M06, M07). The recorded 11.obj2 questions for M01, M03, M04, M05, M06 and M07 are refused or not credited. This says the code will attach provenance correctly when the model writes such a question; it does **not** say the model will write one.

## 6. Still needing human review

The blind sheet is `reports/stage11_eval/stage11s_review/sheet.csv` — 27 unrated items, the 20 questions your run showed plus 7 written by me, shuffled and unlabelled, with the verdicts held in `key.json`. Nothing in this report is derived from it. From my own reading, these accepted questions remain weak: N01 repeats "the number of steps required to find" twice (deliberately released: refusing it would also refuse legitimate parallel comparisons); T02 and N02 are tautological in shape ("how does consistency keep data consistent"); T10's replacement is unmeasured; T01 and N04 use vague deictics ("these filters").

## 7. Real-model results

None. The sandbox has no Ollama, no torch and no network access to model hosts, so no number here comes from a model. The only real-model figures in this report are yours, quoted from the 162322 run of the previous prompt.

**Likely direction, stated as a risk rather than a prediction:** replaying the recorded 11.obj2 text through the repaired rules accepts 10 of 25 model-called rows where the live run accepted 20. In a live run each refusal is followed by one repair instruction, which the replay cannot simulate, so the measured rate will land somewhere between — but it may well fall below 78.3% before it rises. That would be the cost of refusing wording that was wrong, not a regression in the engine.

## 8. Windows verification: PENDING

```
.bot\Scripts\python.exe -m pytest tests\app -q
.bot\Scripts\python.exe -m ruff check src scripts tests
.bot\Scripts\python.exe scripts\check_integrity.py
.bot\Scripts\python.exe scripts\stage10_verify_real_stack.py --opportunities --engine objective
.bot\Scripts\python.exe scripts\stage11r_validator_compare.py --baseline stage11r --out tmp\stage11s_compare.json
.bot\Scripts\python.exe scripts\stage11_compare.py
```
Release gate for that run: 0 fabricated references, 0 duplicated phrases, 0 implied unclaimed implementations, 0 payload inconsistencies, strict skips 10/10. Then rate `sheet.csv` blind before trusting any acceptance number.

## 9. Remaining blockers

1. No real-model measurement of 11.obj3 (needs Windows + Ollama).
2. No human ratings at all, so "quality" is unmeasured by design.
3. `question:ignores_objective` still refuses roughly half the good scenario questions in holdout/holdout2; a semantic engagement test (Sentence-BERT) is the obvious next step and needs Windows calibration. This is the largest single source of fallbacks.
4. Two semantic defect classes undetected (section 4).
5. The prompt changes (rubric premise, explanation-aware wording, target named in the nudge) are unverified against a model.

## Recommendation

**Keep the objective engine experimental; do not change the default.** The repair makes the engine refuse what it should refuse and own memory provenance properly, and it costs no false rejection on any existing question set — but the three things adoption needs are still missing: a real-model run of 11.obj3 on Windows, a blind human rating of the review sheet, and a fallback rate low enough to be usable. Stage 11 is not complete on an automated acceptance number, and this repair deliberately lowers that number where the wording was wrong.

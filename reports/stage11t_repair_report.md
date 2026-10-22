# Stage 11 - Memory and Technical Correctness Repair (11S + 11T)

**Status: implemented and tested in a Linux sandbox copy, then installed into `D:\Projects\SMART-MOCK-INTERVIEW` (backup in `tmp\stage11t_backup_20261022\`). Not executed on Windows. No real model was called, so no acceptance rate is claimed for the repaired engine. Automatic acceptance is not human-rated quality. No git commits, pushes, deployments or paid services. Stage 10N remains the default engine.**

Baseline (your run `tmp/stage10_opps_20261022_162322/results.json`, objective engine, prompt 11.obj2, llama3.2:3b): 18/23 = 78.3% automated acceptance, technical 12/12, grounded memory 2/7, strict skips 10/10, 0 fabricated references, 0 duplicated phrases, warm median 1668.7 ms.

This repair was done in two passes. 11S was written earlier today but never reached D: (its report wrongly said it had; that report now carries a correction). 11T re-verified 11S, fixed what it missed and installed both together.

## 1. Confirmed root causes

**Technically incorrect questions passed (T03, T04, T10, T11, T12, plus N06 found in review).** None of them triggered any rule. No check existed for:
- a self-contradictory premise;
- a comparison of the target with the candidate's own words for it;
- a case nobody described ("lowest and highest");
- a cost question that states the value;
- six words copied straight from the answer;
- two concepts the rubric says are one thing (Type II error = false negative).

T12 also had a selection cause. The open target was a second name for something the answer had already explained, so there was nothing new to ask.

**`memory_id: null` (M01, M02, M03, M06).** The model never supplies the id, so the null came from code declining attribution. Whether a personal reference was backed depended on the one statement the model cited. With no id there was no backing, and with no backing the id could not be attached. A genuine "your spam classifier" therefore looked fabricated. M01 and M06 were also refused for repeating the lead, instead of having the lead dropped.

**M03.** "How do you use return_value and side_effect in your Flask API tests" assumes a practice the candidate never claimed. 11S exempted any question containing "would" or "if". That also waved through "Why would the return_value calls *in your* tests matter?", which still asserts the calls are in their tests. 11T fixed this.

**M05.** The memory is an *explanation* (the sigmoid). The prompt still told the model to say "your …", and an explanation could back "your logistic regression model" or "your confidence interval analysis". 11T added the second check.

**M04 and M07 ("successes").** M04 pasted the name beside the words it was cut from, asked two questions and revisited atomicity. M07 attributed this turn's technique (halving a sorted list) to a feature they only said they built. When the question named their work in words too generic to attribute, the check never ran at all (11T).

## 2. Changes and affected integrations

`src/demo/intel.py` (objective engine only):
- **11S:** `equated_with_explained`, `target_premise` (the rubric supplies the premise sentence; the model is told to ask from it, never to state it), `contradictory_premise`, `circular_contrast`, `repeats_answer_phrase`, `duplicated_subject`, `two_questions`, `invented_qualifier`, `value_stated`, `in_session`, `implies_unclaimed_use`, `distinctive_support`, `SYSTEM_OBJ_IDEA` (explanation memories get their own wording), and the lead dropped instead of refused.
- **11T:**
  - `asserted_in_work` places a technique inside their work by grammar ("in your", "you rely on"), regardless of modal verb.
  - The implementation check now also runs on questions the code did not attribute.
  - `names_the_work` drops the lead when a "your …" phrase carries two specific words of their statement.
  - `explained_as_owned` adds `memory:explanation_as_own_work`.
  - The "both A and B" form was added to `contradictory_premise`.
  - `equated_pairs` and `relates_equated_pair` add `question:relates_equated_pair`.
  - New repair wording; `OBJ_PROMPT_VERSION = "11.obj4"` (only retry wording differs from 11.obj3, which was never run).

`src/demo/followup_llm.py`: `offered_support` and `OWN_WORK_KINDS`. A personal reference is backed by the session's own offered statements about the candidate's work. A missing model id no longer makes a genuine reference look fabricated, and an explanation never backs "your …".

`src/demo/opportunity_eval.py` (audit only): a missing lead is accepted when the cited statement was offered; adds `implied_unclaimed_implementation`. Fixture, labels, denominators, scoring and thresholds are unchanged, and the frozen fixture sha256 is unchanged.

Scripts:
- `scripts/stage11r_validator_compare.py` gains baselines `stage11r` (as installed before today), `stage11s` and `pre11r`, plus the memory holdout.
- `scripts/stage11t_review_sheet.py` is new.

Data:
- `src/demo/eval_data/stage11s_correctness_pairs_v1.json` (holdout4)
- `src/demo/eval_data/stage11t_memory_pairs_v1.json` (holdout5: memory, four cases outside the benchmark)

Tests:
- New: `tests/app/test_stage11s_correctness_and_memory.py`, `tests/app/test_stage11t_memory_boundary.py` (42).
- Updated, with reasons:
  - One Stage 11 example and one 11R "good" example were themselves instances of the defect. "…compare with halving the list in your search feature" says their feature halves a list, so it is now a negative case.
  - The prompt-version asserts were updated.

The engine path is unchanged: `intel.run_objective` → `FL.validate` → `FL.final_gate` → `engine._llm_followup` → session persistence → evaluation → report. `engine.py` was not modified. A grounded question carries its id through the mock generator into the audit with no findings (checked for M01, M03, M05, M06, M07, with the session supplied as the scorer supplies it).

## 3. Tests (sandbox: Python 3.12, no torch or Ollama)

- Whole application suite: **875 passed, 5 skipped**.
- `ruff check src scripts tests`: clean. `check_integrity.py`: OK, no frozen file drifted.
- Your Windows suite will differ in count (783 on your last run). D: also has `tests/evaluation/fixtures/__init__.py`, which the sandbox lacks.

## 4. Good/bad validator comparison (offline, same text, no model)

Baseline is the code installed on D: before today (11R). FR = good refused; FA = bad accepted.

| set | good | FR before → now | bad | FA before → now |
|---|---|---|---|---|
| fixture pairs | 12 | 1 → 1 | 13 | 2 → 2 |
| holdout | 10 | 5 → 5 | 12 | 0 → 0 |
| holdout2 | 10 | 5 → 5 | 10 | 0 → 0 |
| holdout3 | 15 | 2 → 2 | 27 | 1 → 1 |
| holdout4 (correctness, new) | 8 | 0 → 0 | 18 | 11 → 3 |
| holdout5 (memory, new) | 7 | 2 → 1 | 11 | 4 → 0 |

**No existing set gained a false rejection.**
- Recorded real-model questions: of 57 the rules had accepted across three runs, 41 → 27 still accepted. Of 50 they had refused, none is newly accepted.
- Against the 11S pass alone, 11T changes exactly one recorded question: N06, now refused as `relates_equated_pair`.
- Unsupported-reference controls: 22/22 refused, and 0 of 10 genuine references refused.

**Still wrong, stated plainly:**
- Bad questions accepted:
  - "statelessness stateless" (doubled stem);
  - "revalidation compared with max-age" and "rebasing compared with rewritten history" (contrasting concepts that are not rivals needs meaning, not words);
  - "…and which effect size would worry you?" (second question split from its verb).
- Good questions refused: about half of holdout/holdout2 by `question:ignores_objective` when a question describes the target without naming it, plus one holdout5 question for "95%" (no invented figures).

These sets were written by the rules' author: sanity checks, not independent evidence.

## 5. Memory engagement and provenance

**Code behaviour (offline):** each memory case accepts an author-written grounded counterpart with the id attached by code.
- Lead dropped where the question already names the work in their words: M01, M02, M03, M04, M06, M07.
- Lead kept for M05, whose question refers to "that sigmoid output" and needs the lead to say which.

Every recorded 11.obj2 memory question is refused or not credited, each for its own defect. The memory holdout confirms the boundary on unseen topics:
- conditional and possessive implementations refused;
- presupposed decisions refused;
- explanations turned into ownership refused;
- genuine hypotheticals credited;
- an unrelated memory left unattributed.

**Not shown:** that llama3.2:3b will write such questions under 11.obj4. A replay of the recorded 11.obj2 text accepts some attempt on only 9 of 25 model-called rows (the live run accepted 20) and credits no memory, because every recorded memory question had a defect. The live engine retries once with a reason, which a replay cannot simulate. **Expect the measured acceptance rate to fall below 78.3% before it rises.**

## 6. Accepted questions that still need human review

These were shown in your run and are still accepted by the rules:
- **N05** "How does bubble sort handle elements that are already in order?" The open objective is the O(n²) worst case, and this asks about the best case.
- **T02** "How does atomicity impact the consistency of data…?" It revisits atomicity, which the candidate explained; a weak link to consistency.
- **M02** "How does the concept of supervised learning apply to labelled training data in general?" It is near-circular (supervised learning is defined by labelled data) and ignores the offered memory.
- **N01** "How does the number of steps required to find the exact value in the halved range relate to the number of steps required to find it in the original range?" Convoluted.
- **T05** asks about `is` on the same object while the candidate swapped `is` and `==`. Check it does not reinforce the mistake.
- **N04, T08, T01, T07**: probably fine; verify.

The blind sheet is `reports/stage11_eval/stage11t_review/sheet.csv`: 32 unrated items (the 20 follow-ups your run showed, verbatim, plus 12 author-written), shuffled, with the source and rule verdict in `key.json`. Nothing in this report is derived from ratings.

## 7. Real-model results

None. The sandbox has no Ollama, torch or model-host access. The only real-model numbers here are yours, from 11.obj2.

## 8. Windows verification: PENDING

```
.bot\Scripts\python.exe -m pytest tests\app -q
.bot\Scripts\python.exe -m ruff check src scripts tests
.bot\Scripts\python.exe scripts\check_integrity.py
.bot\Scripts\python.exe scripts\stage10_verify_real_stack.py --opportunities --engine objective
.bot\Scripts\python.exe scripts\stage11r_validator_compare.py --baseline stage11r --out tmp\stage11t_compare.json
.bot\Scripts\python.exe scripts\stage11t_review_sheet.py --results tmp\stage10_opps_<new run>\results.json --out tmp\stage11t_review_live
```

Release gate for that run:
- 0 fabricated references, 0 duplicated phrases, 0 implied unclaimed implementations, 0 payload inconsistencies;
- strict skips 10/10;
- prompt version 11.obj4 in results.json.

Then rate the sheet blind before reading any acceptance number as quality.

## 9. Remaining blockers

1. No real-model measurement of 11.obj4.
2. No human ratings, so quality is unmeasured.
3. `question:ignores_objective` is word-based. It refuses good questions that describe the target in other words, and it is the largest source of fallbacks. A Sentence-BERT engagement check is the natural fix; it needs Windows calibration and is outside this repair.
4. Four semantic false acceptances (section 4) and the weak accepted questions in section 6.
5. Rubric-anchored premises and explanation-aware wording are prompt changes, untested against a model.

## Recommendation

**Keep the objective engine experimental; do not change the default.** The repair closes every defect the brief named and one more found in review (N06). It makes memory provenance code-owned end to end and adds no false rejection on any existing set. Adoption should wait for three things:
- a Windows run of 11.obj4 that passes the release gate;
- a blind rating of the sheet showing accepted questions are technically correct and natural;
- a fallback rate that is usable in a real interview.

Stage 11 is not complete on the strength of an automated acceptance number.

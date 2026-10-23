# Stage 11: intelligence architecture integration

Status: **the objective engine is built, wired into the real interview flow behind a reversible flag, and tested offline. It is NOT the default.** The default remains the Stage 10N engine (prompt `10.fu8`) until a real
Windows run of the objective engine passes the pre-registered gates below. No model result for the new engine exists yet; nothing in this document is a measurement of a model unless it says `real_model`.

## 1. What changed, in one paragraph

Stage 10N asked the 3B model for a decision, a concept id, a memory id and a question in one JSON object, then rejected the whole reply when any field disagreed with the others (7 of the 25 real model calls had inconsistent payloads;
the model wrote questions that used an offered memory while answering `memory_id: none`). The objective engine (`src/demo/intel.py`) moves every decision the model was bad at into code. Code decides ask or skip, picks ONE target concept
from the vetted rubric, picks the candidate memory, and attaches the memory id only after checking that the question really builds on that memory. The model's schema is `{"question": "..."}`.

## 2. Flag and rollback

| setting | effect |
|---|---|
| `SMART_DEMO_FOLLOWUP_ENGINE` unset or anything except `objective` | Stage 10N engine, unchanged (prompt `10.fu8`, validator profile `stage10n`) |
| `SMART_DEMO_FOLLOWUP_ENGINE=objective` | objective engine (prompt `11.obj1`), validator profile `objective` |
| `LLMFollowUpGenerator(provider, engine="objective")` | explicit, per generator (tests, scripts) |

Both engines share the pre-filters, the circuit breaker, deadlines, fallback classes, telemetry fields and the deterministic fallback. Provenance on every follow-up now records `engine`, and `memory_ref.attributed_by`
(`code` or `model`). Rolling back is unsetting the variable. Live model follow-ups are themselves opt-in (`followup_mode` live, `SMART_DEMO_LIVE_MODULAR=1`, Ollama running); the deterministic path is the default for every user today.

## 3. Audit and integration matrix

"Connected" means a user action in the Flask journey reaches it, not that a unit test passes. Evidence column: file(s) read and tests that exercise the real path.

| component | implementation | public interface | upstream | downstream consumers | tests | connected to the user journey |
|---|---|---|---|---|---|---|
| Flask routes / UI | `src/demo/routes.py`, `templates`, `static` | `/demo/api/sessions` (POST), `/answer`, `/skip`, `/finish`, `/s/<sid>`, `/summary`, `/export.json` | `engine.DemoEngine` | browser UI | `test_stage9a/9b`, new Stage 11 journey test | yes |
| Setup (role, mode, `followup_mode`) | `engine.create` | session body | routes | engine, interview | `test_stage9b_interview` | yes. `followup_mode` is chosen in Settings, stored in the browser |
| Core question selection | `interview.py`, `catalog.py`, curated flow | `I.stage_of`, `_item` | question bank, retrieval | engine | `test_curated_*` | yes |
| Adaptive follow-ups, deterministic | `engine._maybe_follow_up`, curated key concepts | internal | answer, concepts | session items | `test_stage9b/9c` | yes, **default** |
| Adaptive follow-ups, model | `followup_llm.LLMFollowUpGenerator` (10N) and `intel.run_objective` (11) | `propose(ctx) -> Outcome` | context, memory, Ollama | `engine._llm_followup`, `build_item` | 10D/10J/10K/10N and Stage 11 tests | **only when live mode is on**; default-off |
| Technical vs behavioural modes | `behavioural.py` (scripted probes), technical path | same | stage | engine | `test_stage10b` | yes. Behavioural probes stay labelled scripted and are not credited as model intelligence |
| Question bank and rubrics | `knowledge/*.json`, `concept_equivalences_v1.json` | `engine.record`, concepts | curated data | context builder, both engines | 10K, 10N | yes. The objective engine uses the same vetted concepts; it does not invent a rubric |
| SBERT / FAISS / BM25 | `retrieval`, `memory` (SBERT optional via `SMART_DEMO_MEMORY_SBERT`) | `POL.retrieve_for_followup` | index | memory offering | `tests/retrieval`, 10A/10N | yes for question retrieval. Memory relevance uses BM25 with optional SBERT. Not run in this sandbox (no torch, HuggingFace blocked) |
| Memory extraction, retrieval, provenance | `memory.py`, `policy.py` | `M.update`, `recall_lead`, `_memory_is_current` | answers | follow-up context, session isolation check | 10A/10J/10N provenance | yes |
| Session lifecycle, budgets, restart, persistence | `engine.py`, `store.py` | `_budget_spent`, `_adapt` | settings | everything | `test_stage4b`, `test_stage9b` | yes. The objective engine runs inside `_maybe_follow_up`, so budget, refusal and restart rules apply unchanged |
| Scoring, explanations, reports | `engine` scoring, `insights.py`, `present.py`, `main/` legacy report | summary, export | answers | UI, export | `test_stage8c`, `test_stage9b` | yes. Follow-ups are excluded from scoring as before; no second scoring path was added |
| Ollama integration | `ollama_stream.StreamingOllama`, `followup_llm.make_generator` | `generate`, `warm` | local Ollama | both engines | `tests/helpers/fake_ollama` | yes. The generator cache key now includes the engine |
| MLflow / DVC | `src/mlops`, `dvc.yaml`, `params.yaml` | `--mlflow` on the runner | runner | reports | `tests/mlops` | runner only. Interview runtime does not call MLflow |
| Evaluation scripts / CI | `opportunity_eval.py`, `scripts/stage10_verify_real_stack.py` (now `--engine`), Stage 11 scripts, `.github/workflows/ci.yml` | CLI | fixture | reports | 10F/10L/10N + Stage 11 | yes |

Gaps found by the audit and what was done:

1. Model follow-ups are off by default, so the 10N work is invisible to a default user. Unchanged on purpose; adoption is a separate decision after real evidence.
2. The 10N validator's lexical rules (`ignores_target`, `not_anchored`, `memory_link_without_gap`) refused many reasonable scenario questions. The objective profile replaces them with gap-progression checks (see 5).
3. `memory_id` was model-owned. Now code-owned (see 4).
4. Runner and replay tooling had no engine switch. Added `--engine`.
5. No SBERT calibration exists for engagement. Not added: no measured benefit could be shown here.

## 4. Memory contract (the main failure)

- Code picks the candidate (`plan_objective`) from the memory the 10N retrieval already offers (immutable id, quote, turn). The model never sees the id.
- `attribute_memory` attaches the id only if the question (a) uses specific words of that stored statement, (b) frames earlier work as the candidate's own (`your ...`) for work-like kinds, (c) asks about the TARGET objective, not merely repeating the project name.
  Rejections are explicit: `memory:uncited_reference`, `memory:not_framed_as_own_work`, `memory:link_without_objective`, `memory:tautology`, `memory:double_reference`.
- A valid question that does not use the memory is kept, labelled `memory_stage: not_used`, and is **not** counted as memory use.
- Repair keeps the memory objective and fixes the wording. Stage 10N switched to standard mode and lost the memory.
- Session isolation (`_memory_is_current`) still runs after `propose`; a memory id from another session cannot be attached.
- No citation is ever added to improve a number: attribution requires the question text to build on the stored statement and to ask about the open concept.

## 5. Gap progression instead of word overlap

`engagement()` asks whether the question touches a concept the answer has NOT covered, by (1) naming the open concept, (2) using its distinctive words that were neither asked in the interview question (by stem: asking
"mocking" does not make "mock" progress), nor said by the candidate, nor supplied by the memory quote, (3) cost words for bare-value concepts (O(log n)), or (4) words of the vetted reference sentence about it.
Additional checks: `revisits_explained_concept` (T02/T10 pattern), `unanswerable_quantity` (T04 pattern), `unsupported_premise` (N02 pattern: a causal claim that joins concepts with no basis in the reference). None uses case ids.
Tests assert the five recorded weak questions are rejected for the right reason and that valid paraphrases (T03, T08 style) still pass.

## 6. Measured so far (offline; no model was run)

| evidence | what | result |
|---|---|---|
| `offline_author_judged_pairs` (`scripts/stage11_pairs_eval.py`) | 32 good / 35 bad hand-written questions, same pairs for both validators | false rejections 16/32 (10N) -> 11/32 (objective); false acceptances 2/35 -> 2/35 (the 2 are the documented known gaps) |
| `replay_of_recorded_real_replies` (`scripts/stage11_replay_recorded.py`) | the real llama3.2:3b questions from the 10N run, through the new code | the five flagged weak questions are all rejected; code attributes memory on M04 and M05 only, the same 2 cases that were grounded before; recorded "expected" questions accepted drop from 7 to 3 on the first attempt (4 on any attempt) because the stricter rules reject T02/T04/T10 and re-asks |
| schema consistency | payload-inconsistent rows | 0 by construction (`{"question"}` only). The 10N run had 7 |

How to read this. The replay is text a model wrote for the 10N prompt; it cannot show whether the 11.obj1 prompt produces better questions. The pair sets `holdout`, `holdout2` were written by the same author as the rules, so they are sanity checks, not independent evidence.
The honest reading: the engine removes a class of structural failures and rejects the weak patterns the brief named, at the price of accepting fewer of the recorded questions. Whether a real model under the new prompt reaches more grounded memory
use and more good follow-ups is **unmeasured**.

## 7. Pre-registered adoption gates (decided before any real objective-engine run)

Run on Windows, same model, same frozen fixture (`stage10f_opportunities_v1.json`, hash unchanged), baseline and objective:

G1 technical expected >= baseline (7/12). G2 grounded memory >= baseline and >= 4 of 7. G3 fabricated memory references 0. G4 strict skips 10/10. G5 inconsistent-payload rows 0. G6 fallbacks <= baseline (9).
G7 overall eligible success >= baseline (13/23). G8 median warm latency <= 1.5x baseline. G9 blinded human review not worse on technical accuracy and naturalness (unrated = not met).

`scripts/stage11_compare.py` evaluates G1-G9 and refuses to treat selftest data as evidence. The 80% target is not a gate; it is reported as measured whatever the result.

## 8. Running it on Windows

```
.bot\Scripts\python.exe scripts\stage11_inspect_ollama.py --out tmp\stage11_models.json
.bot\Scripts\python.exe scripts\stage10_verify_real_stack.py --opportunities --models llama3.2:3b --engine stage10n --mlflow --sbert
.bot\Scripts\python.exe scripts\stage10_verify_real_stack.py --opportunities --models llama3.2:3b --engine objective --mlflow --sbert
.bot\Scripts\python.exe scripts\stage11_compare.py --runs tmp\<run_a>\results.json tmp\<run_b>\results.json --out tmp\stage11_compare
```

Repeat with any other model that `stage11_inspect_ollama.py` shows as already installed and fitting in memory. Nothing is downloaded and no paid service is used. Give the sheet in `human_review_pack/` to a person; keep their ratings separate from automatic acceptance.

## 9. Source comparison (patterns only; no code, prompts or assets were copied)

| source | licence | pattern taken | pattern not taken |
|---|---|---|---|
| InterviewOS | MIT | code-owned follow-up decision (`ask`, focus, reason) separate from wording | its service layout and dependencies |
| DeepInterview | Apache-2.0 (with NOTICE) | prep / live / post split; provider protocols; gated verifier before a question is used | LangGraph-style orchestration (no measured benefit shown, so not added) |
| interview-practice-partner-039 | MIT | labelling heuristic vs deterministic scoring; scripted personas stay labelled | model-declared next action: our 3B data shows the model is poor at that decision |
| interviewOps | MIT | structured assessment fields and an explicit state per turn | the platform services |
| Yoodli (public help page only) | n/a (documented behaviour, no code or prompts) | practice-session flow and feedback after the session as a product reference | nothing proprietary was inspected |

Licence conclusion: because only ideas were used, no attribution file is required. If code from DeepInterview is ever copied, its Apache-2.0 NOTICE obligations apply.

## 10. Limitations

- No real objective-engine run exists. No Ollama, torch or SBERT in the sandbox that built this stage; HuggingFace was blocked.
- Weak-case rejection is rule-based. Rules can over-reject (11 of 32 good pair questions are still refused), which lowers acceptance. Rules can also under-reject: the 2 known-gap bad pairs pass.
- Misconception probing is a prompt hint only (benchmark records carry no `common_mistakes`).
- The model comparison across Ollama models needs the Windows machine; the inspector lists what is installed.

## Stage 11R - quality and safety repair (objective engine, still experimental)

Stage 10N stays the production default (`SMART_DEMO_FOLLOWUP_ENGINE` unset => `stage10n`). Nothing in the frozen fixture, labels, denominators or scoring changed.

Root causes and fixes
- **Fabricated reference (T09).** The live path used `_MEM_CUE`, the audit used `_EARLIER_CUE`; bare "you mentioned" was only in the audit. Both now call one detector, `followup_llm.unsupported_reference(question, ctx, mem_quote)` (kinds: speech, relative, your_work, back_reference). A reference is supported only by the candidate's answer in this turn or by the attributed stored statement; vague nouns (data, model, system...) never support one. It applies to BOTH engines as `reference:unsupported:<kind>`.
- **Marker expansion ("consistency consistency").** The prompt printed concept ids ("E2 consistency") and `sanitise_ids` replaced the id with the label, doubling it. The prompt no longer prints ids; `sanitise_ids` drops the marker when the neighbouring word already carries the label, otherwise substitutes the label. A model-written doubled phrase is refused (`question:duplicated_phrase`). `final_gate` re-checks the final text (id marker, duplicated phrase, unsupported reference) in `engine._llm_followup` before anything is stored or shown.
- **T11.** `novel_technical_terms` accepts compound parts whose stem the candidate already used; invented compounds are still refused.
- **M02/M03/M04.** The target could be the concept restating the original question, or ignore the stored work. `choose_target` skips concepts already named in the question and, with a memory, prefers the open concept that shares the most specific stems with it. The prompt gives a handle ("your spam classifier") and asks how the TARGET would matter in that work. Attribution stays code-owned and needs the question to be about the work AND the target (`memory:presupposes_use`, `memory:restates_lead`, `memory:not_framed_as_own_work`).
- **Weak wording.** Objective-profile rules: `restates_answer_in_premise`, `sidesteps_stated_value` (a wrong stated value such as O(n) must be probed on the case the candidate named), `word_list`, `too_long_for_interview` (38 words).

Limitations: the pre-existing `question:ignores_objective` rule still rejects some good scenario questions (see the report); one doubled-stem case ("statelessness stateless") is not caught; no real-model run of the repaired prompt (11.obj2) exists.

## Stage 11S - technical correctness and code-owned memory (objective engine, still experimental)

Stage 10N remains the default. The frozen fixture, labels, denominators, scoring and audit thresholds are unchanged. Prompt version `11.obj3`.

### The question's premise comes from the rubric, not from the model
`target_premise()` passes the shortest vetted reference sentence about the TARGET into the prompt ("TARGET IN CONTEXT ... ask from it, never state it"), skipping any sentence that carries a value or a figure. `equated_with_explained()` drops a concept from the objective when the reference states it is a second name for something the answer already explained ("Type I error is a false positive"), matched on the written names because 'Type I error' and 'Type II error' share their word stems.

### Correctness checks on the written question (objective profile)
| rule | refuses | leaves alone |
|---|---|---|
| `contradictory_premise` | one thing said to be both of a pair of opposites ("a true null hypothesis is actually false"); listed antonyms plus any word beside its own negated form | two different things with opposite properties ("a positive result ... when the test is negative"), X contrasted with un-X |
| `circular_contrast` | the TARGET set against the candidate's own words for the same thing, where the other side adds nothing new | a contrast that brings in a second subject ("... than linear search when the target is not in the sorted list") |
| `repeats_answer_phrase` | five or more words in a row from the answer, three of them carrying content | short technical phrases, terms reused once |
| `duplicated_subject` | the same name twice within four words ("money transfers in your money transfers"), compared on stems | parallel structure further apart, X versus un-X |
| `invented_qualifier` | a superlative no source mentions ("the classes with the lowest and highest probabilities") | "the worst case" when the candidate or the rubric uses it |
| `two_questions` | a second interrogative clause after a comma | a leading phrase before a comma, a short dependent second clause |
| `value_stated` | a "cost" question that states the value it should be asking for | a cost probe that does not |

### Memory: the application owns the identity
The model is never asked for an id and a wrong one changes nothing. Before attaching one, the code checks: the statement is in this session's offered set with the same wording (`in_session`); the question uses its distinctive words; the question does not claim the work is built the way this answer describes (`implies_unclaimed_use`, conditional phrasing exempt); it advances an open concept (`engagement`); and the wording is supported (`presupposes_use`, now blind to conditional questions, and `memory:tautology`). A question that already names the work is shown **without** the "Earlier you said ..." lead rather than refused, and the audit accepts that state. `offered_support()` backs a personal reference with the candidate's own offered statements, so a missing model id no longer makes a genuine reference look fabricated; only statements about their own work can back "your <thing>", so an explanation of a concept never implies they built one.

### Measured, and not measured
No real-model run exists for 11.obj3. A replay of the recorded 11.obj2 text shows 10 of 25 model-called rows would still be accepted (20 were), so the measured acceptance rate is likely to fall before it rises: the rules now refuse wording the previous run accepted, and only a live run can show what the model writes when told why. Known gaps: a contrast between two curated concepts that are not rivals of each other is not detected; a second interrogative separated from its verb is not detected; `question:ignores_objective` still refuses about half of the good scenario questions in the holdout sets.

## Stage 11T - the boundary between what the candidate said and what a question asserts (completes the 11S repair; still experimental)

Prompt version `11.obj4` (only the retry wording changed from 11.obj3; 11.obj3 was never run). Stage 10N remains the default; frozen fixture, labels, denominators, scoring and audit thresholds unchanged.

| rule | refuses | leaves alone |
|---|---|---|
| `asserted_in_work` (feeds `memory:implies_unclaimed_use`) | a technique the sentence places INSIDE their work, whatever modal verb surrounds it: "the return_value calls **in your** tests", "the atomicity **you rely on**" | genuine hypotheticals ("**If** your search feature scanned every record ..."), properties every such thing has ("the ROC curve **of** your classifier"), "the halving in your answer" |
| the same check on a question the code did **not** attribute | M07-type text that names their work ("your search feature") with words too generic to attribute, but still tells them how it is built | questions that do not place anything in their work |
| `names_the_work` (drop the lead, keep the id) | nothing is refused: when a "your ..." phrase carries two specific words of their statement ("your tumour detection network"), the "Earlier you said ..." sentence is not shown | one shared word ("your model") keeps the lead |
| `explained_as_owned` (`memory:explanation_as_own_work`) | an EXPLAINED concept turned into their work ("your confidence interval analysis", "your logistic regression model") | "your explanation of ...", "your answer" |
| `contradictory_premise` (3) | "is both true and false", "true and false at the same time" | "a sample with both positive and negative examples" |
| `relates_equated_pair` | relating two names the vetted reference says are one thing ("How does a false negative affect the outcome of a Type II error?") | a gloss in apposition ("a Type II error, that is, a false negative"); scenarios naming one of them |

Memory ownership, end to end: the model writes only `{"question"}`. The code offers at most one statement from this session (`plan_objective`), checks it is the live, unedited item (`in_session`), credits it only when the question uses its specific words AND advances the open TARGET (`engagement`), and refuses wording that presupposes use, places an unclaimed technique in their work, or turns an explanation into ownership. A personal reference the code does not attribute is backed only by the session's own offered statements (`FL.offered_support`). A missing model id is therefore never a reason to refuse, and a shared project name is never enough to credit one.

Blind review: `scripts/stage11t_review_sheet.py` rebuilds `sheet.csv` + `key.json` from any results.json. Recorded follow-ups are shown verbatim (their lead is already part of the text; the 11S sheet added it a second time and was withdrawn).

## Stage 11U - final quality correction (prompt `11.obj5`; still experimental)

**Claims about the candidate's work come from grammar, not from shared topics.** `claimed_about_work` collects only what a sentence *places* in their work:
- "the X in your …" or "the X you rely on" (whatever the modal verb);
- "X in your …" stated as fact (not under would/could/if);
- modifiers in front of the part of the work they named ("your **binary** search");
- "your X uses Y";
- a bare process related to their work as fact ("How does halving the list relate to … your feature?");
- an outcome stated as fact (", making it efficient").

A topic owned by someone else ("the ROC curve of **a** logistic regression model") or a possibility ("How would linear search affect your search feature?") is not a claim.

**Attribution through the handle.** The handle the code built from their statement ("your search feature") counts as using it, in the objective profile only, and only if every other check passes.

**What a question may assert** is limited to what the vetted reference (prose only: code samples and URLs removed), the question asked, the concept names and the answer support:

| rule | refuses | leaves alone |
|---|---|---|
| `narrows_collection` | computing something "for a specific/single feature" when the sources only speak of features together (T08) | "doubling a single feature's value"; a noun the sources use in the singular |
| `invented_qualifier` (extended) | "closest", "nearest", "earliest" … when no source has them (T10) | the same words when a source uses them |
| `misattributed_target` | the TARGET given to a model or algorithm the rubric never gives it to ("hierarchical representations in a decision tree", T11) | the TARGET applied to a scenario ("false negatives in a screening test") |
| `unsupported_target_event` | a when/if clause in which something happens to the TARGET that the sources never say ("when a false negative is detected", T12) | occurrence verbs ("is made", "is observed") |
| `unsupported_effect` | the TARGET said to change something it does not act on ("return_value … affect the behaviour of your API", M03) | effects on things the sources name; cost measures; "change what … sees" clauses |
| `asserts_interpretation` | the question explains what a situation means (", meaning the patient doesn't have cancer", N06) | a noun gloss ("a Type II error, that is, a false negative") |

All of these remain word-level rules. See `reports/stage11u_repair_report.md` for what they still miss.

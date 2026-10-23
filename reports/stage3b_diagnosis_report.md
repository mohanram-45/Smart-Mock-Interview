# Stage 3B — Real-LLM failure diagnosis (llama3.2:3b smoke run)

Scope: diagnose the first real smoke run (12 cases, 11 reached the model, 0 graded, 4 `invalid_response`, 7 `insufficient_evidence`), fix only what the evidence supports, add offline regression tests. No full benchmark, no Qwen, no shadow mode. Benchmark labels are AI-authored (Claude) and not human-reviewed.

Evidence: `data/evaluation/stage3b/runs_llama3.2_3b.json` (original, preserved untouched) and the raw replies copied to `tests/evaluation/fixtures/llama32_3b_smoke_raw.json`.

## 1. Root cause per case

| Case (type) | Final status | Call 0 (first attempt) | Call 1 (repair) | Root cause |
|---|---|---|---|---|
| B01 correct | invalid_response | `gradable=true`, levels 3/2/4/2 — **content usable**; `missing_concepts` etc. contained objects `{"concept","quote"}` instead of strings | `gradable=false`, reason `"missing_concepts"`, all levels 0 | **Schema strictness on optional list fields.** Repair then made it *worse* (the repair prompt omitted the previous reply, so the model lost the content) |
| B04 short-but-sufficient | invalid_response | `gradable=true`, 3/2/4/1; `supporting_evidence[0].source` = the literal template `candidate_answer\|reference_answer\|key_concepts\|supporting_knowledge` | declined: "unclear reference" | **Prompt template copied literally** by the model; one optional, malformed evidence item sank an otherwise valid grading. Repair degraded it into a decline |
| B07 valid alternative | invalid_response | `gradable=true`, 3/2/4/2; 5 errors: objects in 4 text lists + template `source` | still graded, same shape errors | Same two causes. Repair repeated the same mistakes (it was only told the error text, not shown its reply) |
| B40 weak reference | invalid_response | `gradable=true`, 3/2/4/2; template `source` | graded, same | Template copy |
| B03 incorrect | insufficient_evidence | `gradable=false` "unclear reference…" | declined: "missing reference and inability to judge from own knowledge" | **Model misread** "reference is not human-verified" (prompt rule 2/8) as "no usable reference". Reference was present. Wrong answers should be scored low, not declined |
| B13 incorrect | insufficient_evidence | declined: "incorrect answer and lack of explanation" | declined: "lack of reference" | Same misreading; declining *because the answer is wrong* |
| B22 confident-inaccurate | insufficient_evidence | declined: "not technically accurate" | declined | Same |
| B11 confident-inaccurate | insufficient_evidence | declined: "unclear or incorrect claims" | (no repair: declined is valid JSON) | Same |
| B15 off-topic | insufficient_evidence | declined: "does not address the question" | – | Same; off-topic answer should be relevance 0 / low score |
| B20 injection-only | insufficient_evidence | declined: "attempts to override instructions…" | – | Model refused to grade manipulation. Safe (no score granted) but differs from the AI-authored expectation (low graded score). **Open disagreement, not a bug** |
| B43 injection + loop | insufficient_evidence | 8.6k chars of JSON truncated at the 2000-token cap in a repetition loop (`{"concept":"value equality","quote":…}` repeated) → unparseable | declined: "untrustworthy candidate answer" | Repetition loop hit `num_predict`; then a decline. Truncation was previously not reported as such |
| B41 empty | not_gradable | – (no model call) | – | Correct pre-check, as expected |

### The 7 `insufficient_evidence` outcomes (precise)
All seven (B03, B11, B13, B15, B20, B22, B43) are `reason_code=model_declined`: the model returned valid JSON with `gradable=false`. **None** is a genuine lack of reference evidence (every item had a reference + key concepts; the evaluator's own no-reference pre-check never fired). Reasons the model gave: unverified/"unclear" reference (B03, B13, B22), the answer being wrong or off-topic (B11, B13, B15, B22), reaction to an injection attempt (B20, B43). The first two are prompt-induced behaviour; the third is defensible but deviates from the expectation.

### The 4 `invalid_response` outcomes (precise)
B01, B04, B07, B40 had a **gradable, structurally reasonable first reply** rejected for shape only: objects in `List[str]` fields (B01, B07) and the template-literal `source` (B04, B07, B40). No malformed JSON, no provider/parsing failure. Retries/repair did not rescue them and in B01/B04 turned a usable grading into a decline.

### Other findings
- Repair re-asks introduced extra failures in B01, B03, B04, B13, B22, B43 (declines after a first reply that was either graded or already a decline).
- Valid JSON ≠ correct grading. Replaying B01/B04/B07/B40 shows the 3B model flagged *correct* statements as factual errors, with explanations like "The candidate's statement is technically correct, but…". Levels (3/2/4/2) gave scores of 64–68 ("fair") even for the correct and valid-alternative answers — weak discrimination, a model-quality issue not fixed here.
- No evidence the evidence verifier, concept verification, score caps or injection checks were over-strict: on the replay they correctly dropped unverifiable items and nothing legitimate was removed. One narrow exception: quotes with inner backticks (`` `==` ``) did not match (`_norm` only stripped edge backticks).

## 2. Architecture review (what was and was not changed)
Reviewed: prompt, Pydantic schema, provider response handling, evidence validator, concept verification, unsupported-credit cap, insufficient_evidence logic, repair/retry.

Changed (each tied to a diagnosed failure):
1. `prompt.py` (version 3a.1 → 3b.1): replaced pipe-separated type templates with a concrete example + explicit "allowed values"; plain-string lists stated; rule 6 "Always grade… Set gradable=false ONLY when the text is not an attempt at all; never because the reference is unverified, the answer is wrong or off-topic"; kept "NOT human-verified / fallible" wording and the security rule.
2. `schema.py`: text lists accept one-text objects (`{"strength": "…"}`) and are coerced; objects with no single clear text are still rejected. `supporting_evidence` items with an invalid source/shape are dropped and counted (optional feedback no longer sinks a usable grading; they are never trusted). `FactualError.explanation` may be empty at parse time.
3. `evaluator.py`: repair prompt now includes the previous reply (as data) and says "fix only the format, keep the same assessment, don't decline unless not an attempt"; truncation (`done_reason=length`) reported as such; error message keeps the first-attempt error; `_norm` ignores inline backticks/`**` only (substring match still required); factual errors with an empty explanation, or whose explanation says the claim *is correct*, are dropped as unsupported and counted in `flags.dropped_unverifiable.errors`.
4. `providers/http.py`: `done_reason` added to usage diagnostics. `providers/mock.py`: can return a prepared `ProviderResponse` (test support).

Deliberately **not** changed: rubric weights/caps, unsupported-credit cap, injection detection and quote dropping, concept/evidence verification (still exact-substring), `insufficient_evidence` semantics, no auto-scoring of invalid output, legacy scoring, adaptive interview.

Caveat on the self-contradiction filter: it is a regex heuristic on the model's own explanation (`… is (technically) correct/accurate…`). It can only *remove* an accusation (never add credit or a score), so it errs on the safe side of "unsupported factual-error accusation", but it could also drop a real error whose explanation happens to contain such a phrase.

## 3. Tests
`tests/evaluation/test_stage3b_diagnosis.py` (23 cases incl. parametrised) replays the real raw replies and checks: the 4 real invalid cases now validate on the first attempt and grade; list-of-objects coerced / junk objects rejected; template `source` dropped not fatal; fabricated quotes/evidence still removed and the ≤30 cap still applies; backtick quotes verify but different words don't; empty/self-contradicting errors dropped; a verified major error still caps at ≤60; repair keeps the previous reply; invalid after repair stays unscored and reports first error; real truncated loop → invalid with a token-limit diagnosis; the real declines stay unscored; missing reference stays unscored without a model call; prompt has no pipe templates; injection answer gets no concept credit and a flag.

Results (sandbox): evaluation 124 passed (was 101); retrieval 137 passed / 1 skipped; app 77 passed / 5 skipped (all baselines intact). Windows suite not re-run by me.

## 4. What this does NOT show
- The 7 declines are model behaviour. Offline replay can't show the new prompt fixes them; only a real re-run can. The offline replay only proves the 4 shape failures are gone for those saved replies.
- Even after validation, llama3.2:3b's grading quality is weak (correct answer scored "fair", spurious error flags). No claim of readiness for shadow mode.
- Expectations are AI-authored and unreviewed; B20 expected a low graded score, the model declined.

## 5. Confirmation run (5 cases, llama3.2:3b only, original preserved)
Windows, from the project root (writes to a *new* folder; the original `runs_llama3.2_3b.json` is untouched):

```
python scripts\stage3b_run.py --model llama3.2:3b --set smoke --items B01,B03,B04,B07,B20 --repeats 1 --out-dir data\evaluation\stage3b_confirm
python audit\evaluation\stage3b_analyze.py data\evaluation\stage3b_confirm\runs_llama3.2_3b.json
python audit\evaluation\stage3b_compare.py data\evaluation\stage3b\runs_llama3.2_3b.json data\evaluation\stage3b_confirm\runs_llama3.2_3b.json
```
Why these five: B01 (correct), B04 (short sufficient), B07 (valid alternative) were the shape failures; B03 (wrong answer) was a prompt-induced decline; B20 (injection) checks safe handling. Expect ~3–5 min at the earlier ~37 s/call. If `mkdir` complains, create the folder first. Stop there; do not run the full 43.

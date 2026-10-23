# Stage 9D: why the local follow-up timed out, and what changed

**Evidence status.** The 3 real failures (two 30 s deadline hits, then circuit-open) come from your Windows run. The development session could not reach your Ollama, so **no real
timing was measured in 9D**. Everything below marked *estimate* is arithmetic, not measurement; everything marked *proven* is behaviour tested against a fake server with scripted timings.

## Root cause analysis (what the 9C code did)
| # | Candidate cause | Verdict | Basis |
|---|---|---|---|
| 1 | Cold model load | **Probably contributing to call 1** | `keep_alive` was never sent, so the model could sit unloaded and load *inside* the interview turn. A 4.7 GB `qwen2.5:7b` load alone can take 10-30 s from disk. Evidence needed: `load_duration` of a cold call (benchmark prints it). |
| 2 | CPU/GPU limits | **Likely major** | A 7B model on CPU (or partially offloaded on a 4 GB GPU) decodes a few tokens/s. Evidence needed: `generate_tok_per_s` from the benchmark. |
| 3 | Long prompt | **Confirmed in the code** | 9C prompt ≈ **1,000-1,270 tokens** *(estimate, chars/4)*: full reference answer (up to 1,600 chars), a worked example, all concepts. Prompt processing on CPU is often 20-60 tok/s ⇒ roughly 15-60 s before the first token *(estimate)*. |
| 4 | Too many generated tokens | **Confirmed in the code** | The schema demanded question + purpose + concept ids + up to 3 evidence objects with notes + five validity fields ≈ **200-250 tokens** *(estimate)*; `num_predict` was 500. At 5 tok/s that is 40-50 s. |
| 5 | Expensive reasoning/explanation | Partly | The model was asked to self-report five validity judgements and write evidence notes, i.e. a mini grading report. |
| 6 | Ollama defaults | **Contributing** | No explicit model default (the evaluator's `qwen2.5:7b` was reused), no `keep_alive`, `num_ctx` 4096 (bigger KV cache than needed). |
| 7 | Slow schema-constrained generation | Possible, small | Grammar constraint adds per-token overhead; the schema had ~1.2 KB of enums/arrays. Benchmark variant `compact_json` isolates it. |
| 8 | Deadline implementation | **Real defect** | The deadline only *abandoned* a worker thread. The HTTP call kept running and Ollama kept generating, so call 2 queued behind call 1 and also timed out. `OllamaProvider`'s own socket timeout (also 30 s) does not cover "slow but alive" streaming. Two timeouts then opened the breaker, as designed, so call 3 never ran. |
| 9 | Rejection after generation | Not the cause of these 3 failures | They were deadline errors, not validator rejections. |

**Most likely story:** call 1 = cold load + ~1,100-token prefill + ~250-token decode on CPU > 30 s; its abandoned generation kept the model busy; call 2 queued behind it; breaker opened.
This is a hypothesis consistent with the code and your result; the benchmark below turns it into measurements.

## What changed (all tested)
1. **Streaming client** (`src/demo/ollama_stream.py`): one absolute deadline over connect + prefill + decode; on expiry the connection is **closed, which makes Ollama stop generating** *(proven: fake server counts the cancellation)*; partial timings are still returned; real Ollama counters (`load_duration`, `prompt_eval_*`, `eval_*`) are kept.
2. **Compact pipeline** (`followup_llm.py`, prompt version `9d.fu2`): no reference text in the prompt, max 4 concepts (essential first), ≤3 short previous questions, answer capped at 1,200 chars, no worked example. Prompt ≈ **360-380 tokens** *(estimate; was ≈1,000-1,270)*. Output schema 7 small fields ≈ **60-80 tokens** *(estimate)*, `num_predict` 160, `num_ctx` 2048.
3. **Safety moved into code, not removed.** The validity self-report shrank to two booleans (`uses_given_facts_only`, `already_in_answer`) that can only *veto*. Everything else is checked by code: exact `answer_quote` found in the answer, concept id in the curated list, no repeat of any earlier question, no new technical terms, no link/code/instruction, one short question. **New** rules: the question must share words with what the candidate wrote (`not_tied_to_answer`), bare "explain X" requests are rejected, accusatory wording ("incorrect", "you forgot") is rejected, and an answer sharing no content word with the question/concepts/reference gets the standard follow-up without any model call.
4. **Prewarm + keep_alive.** Creating a live interview starts a background warm-up (`keep_alive` 30 m). Until the model is ready, follow-ups use the standard bank-backed question **immediately** (`model_warming`): a cold load can never block a turn.
5. **One request in flight** (`model_busy` otherwise) and a **back-off breaker**: 2 failures ⇒ 60 s pause, each failed probe doubles it (max 300 s); a success resets it. If Ollama is down/model missing, the warm-up retries only every 20 s.
6. **Explicit model and per-model deadlines:** `SMART_DEMO_FOLLOWUP_MODEL` (default **`llama3.2:3b`, provisional and unbenchmarked**), `SMART_DEMO_FOLLOWUP_TIMEOUT_S` (default 20), `SMART_DEMO_FOLLOWUP_DEADLINES="qwen2.5:7b=40,llama3.2:3b=15"`.
7. **UI:** the existing "thinking" bubble says "Preparing a follow-up…" (and, after 7 s, that a standard follow-up is used if it takes too long); nothing else changed. Sessions log every attempt (outcome, reason codes, Ollama metrics; no answer text).
Follow-up generation was already separate from grading and stays so: the model never scores or judges the answer.

## Benchmark (run it on Windows)
```
cd /d D:\Projects\SMART-MOCK-INTERVIEW
.bot\Scripts\python.exe scripts\stage9d_bench_followups.py --models llama3.2:3b qwen2.5:7b --out tmp\bench1
```
Add `llama3.1:8b gemma2:9b` only if the first two disappoint. Output: `summary.md` (cold/warm latency, load time, prompt/generated tokens, tokens/s, schema validity, rule acceptance, rejection reasons, A/B of
the old 9C-style prompt `legacy9c` and no-grammar `compact_json`), `results.json`, and a **blind** `review_sheet.csv` + `key.json`. Rate the sheet with the questions in its header; the model names are hidden.
`--selftest` runs the script against a fake server (numbers are scripted and labelled so).

## Choosing the default model
Not decided. Rule: pick the **smallest model that passes human review** (relevant / probes a real concept / does not call a correct answer wrong / no invented facts) **and** whose warm p90 is under its deadline.
Do not choose on latency alone, and do not enable the live mode by default until reviewers have rated the review sheet.

## Remaining limitations
- No real-model timing or quality number exists yet.
- The "answer unrelated" pre-check is a word-overlap heuristic: a valid answer that shares no words with the question, concepts or reference falls back to the standard follow-up (safe, but loses the model follow-up).
- Streaming cancels the HTTP request; whether a given Ollama build stops mid-prefill promptly is not verified here.
- A resumed interview after a server restart uses standard follow-ups until the model has warmed again.

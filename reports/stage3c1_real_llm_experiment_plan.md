# First controlled real-LLM experiment (plan only — not run)

Goal: find out whether a real model can act as the *concept verifier* behind the Stage 3C-1 gate, on the 16 scope-eligible questions only.

## Preconditions
1. Freeze: code hash of `src/evaluation/modular/`, `VERIFIER_PROMPT_VERSION`, scope sha (7332f65c…), model name/quantisation/settings. No edits during the run.
2. Human labels: a human (not an AI) labels, per answer, each essential member as stated correctly / stated incorrectly / not stated, plus any factual errors. Labels written before the model is run and kept separate from the prompt and from tuning.
3. Answer set: new answers for the 16 questions (≥6 each: correct, concise-correct, partial, alternative-valid, wrong, injection/adversarial ≈ 100 answers). Do not reuse bench_v2 text for tuning; bench_v2 may be reused only as a smoke test.
4. Runtime: local Ollama on the Windows machine (the sandbox cannot reach it); no paid APIs; JSON-constrained output; temperature 0; single run, then a second identical run to measure stability.

## Measurements (per member verdict, against human labels)
* Agreement on states_correctly / states_incorrectly / not_stated, with confusion matrix; unverified rate.
* False-credit rate (model says correct, human says wrong or not stated) — the critical error.
* False-error rate (model alleges error, human says correct).
* Evidence validity: fraction of verdicts with existing claim ids; fraction rejected by the gate; quote fabrication rate.
* Injection resistance on adversarial answers (no credit gained by instruction).
* Run-to-run stability of verdicts and final scores; provider failure/invalid-JSON rate.
* Abstention rate and whether abstentions were warranted.

## Acceptance criteria (set before running; no tuning after)
* False-credit rate and false-error rate each ≤ 5% of human-labelled members, with intervals reported (n is small; no claim beyond the 16 questions).
* Zero injection-induced credits.
* Invalid-response rate ≤ 5%; verdict stability ≥ 90% between runs.
* Abstention rate and reasons reported; no numeric score issued without verified evidence.
If criteria fail, record why and stop; do not adjust the gate or rubric to fit the results.

## Out of scope
Shadow mode, live scoring, the other 650 records, new interview questions, paid models, claims of general grading accuracy.

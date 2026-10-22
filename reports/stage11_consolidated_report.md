# Stage 11 consolidated report

Date: 2026-10-21. Scope: improve follow-up intelligence without rebuilding the app; compare with Stage 10N before adopting.

## Verdict

**Do not adopt yet. The Stage 10N engine stays the default.** The objective engine is built, connected to the real follow-up path behind `SMART_DEMO_FOLLOWUP_ENGINE=objective`, and tested offline, but no real-model run of it exists, so no quality gain is demonstrated. The smallest defensible next action is one Windows run of baseline vs objective with `llama3.2:3b` (commands in section 6), then human rating of the blinded sheet.

## What was delivered

| deliverable | where |
|---|---|
| Architecture audit, integration matrix, source comparison, gates | `docs/STAGE11_INTELLIGENCE_ARCHITECTURE.md` (sections 3, 9, 7) |
| Engine | `src/demo/intel.py`; flag-guarded hooks in `src/demo/followup_llm.py` and `src/demo/engine.py` (log fields) |
| Runner switch | `scripts/stage10_verify_real_stack.py --engine stage10n\|objective` |
| Comparison, gates, blinded human pack | `scripts/stage11_compare.py` |
| Model/hardware inventory (no downloads) | `scripts/stage11_inspect_ollama.py` |
| Offline pair evaluation | `scripts/stage11_pairs_eval.py` |
| Replay of the recorded real run | `scripts/stage11_replay_recorded.py`, output in `reports/stage11_eval/replay/` |
| Tests | `tests/app/test_stage11_objective_engine.py` (30 tests) |
| CI | two no-model steps in `.github/workflows/ci.yml` |

## Evidence, with kinds kept apart

**Real model, Stage 10N (given, recorded):** acceptance 13/23, technical 7/12, grounded memory 2/7, strict skips 10/10, fabricated 0, fallbacks 9, 7 of 25 model-call rows with inconsistent payloads. Human rating: not rated.

**Offline code evidence (no model):**
- Pair sets, same pairs for both validators: false rejections 16/32 -> 11/32; false acceptances 2/35 -> 2/35 (the two documented known gaps). Author-judged; holdout sets share the author with the rules.
- Replay of the recorded real replies through the new code: T02, T04, T10, M07, N02 are all rejected, each for a named rule, with no case ids in the code. Memory is attributed by code on M04 and M05 only, the same two successes as before; M01, M03, M06 questions are rejected as uncited, superficial or not about the gap. Recorded "expected" questions accepted on the first attempt fall from 7 to 3.
- Inconsistent payloads: 0 by schema construction.

**Not measured:** any real model under prompt `11.obj1`; grounded-memory rate for the new engine; latency; any other Ollama model; human naturalness or technical correctness for either engine; SBERT effects. The replay does not show that a model will write better questions. It shows the code now refuses the weak ones and attaches citations only when the question uses the memory.

## The five memory failures

M01, M03 and M06 questions repeat a project name or topic without probing the open concept; the engine rejects them rather than crediting them. M04 and M05 pass and are attributed by code. Whether the model, when prompted with a single target and the earlier work, writes a question that clears the bar for M01, M03, M06 is exactly what the Windows run must show. I did not make those cases pass by loosening attribution.

## Unmet targets

- 80% eligible success: not reached by any measured run; not claimed. Stage 10N measured 56.5%.
- Model comparison: not run (no Ollama in the build sandbox). Nothing is claimed about any model being better.
- Human review: pack generated, unrated.
- Windows verification of the new code: see section 7 (filled in after the install run).

## Risks and limits

- Stricter rules lower the number of accepted recorded questions; if a real run shows more fallbacks, the default stays.
- 11 of 32 good pair questions are still refused; some valid scenario questions will fall back to the deterministic follow-up.
- Misconception probing is a prompt hint only; the benchmark has no `common_mistakes` records.
- Frozen benchmark (`stage10f_opportunities_v1.json`), its hash and the B07 safety-only scoring were not changed.

## 6. Commands on Windows

See `docs/STAGE11_INTELLIGENCE_ARCHITECTURE.md` section 8.

## 7. Windows verification

Pending: filled in below after the files were installed.

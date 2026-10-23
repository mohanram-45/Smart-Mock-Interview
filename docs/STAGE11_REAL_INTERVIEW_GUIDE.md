# Running a real 15–20 minute interview with the objective follow-up engine

This uses the existing Flask UI, unchanged. The objective engine is experimental and switched on for this run only; the default (Stage 10N) is untouched. Nothing is uploaded, and no paid service is used.

## 1. Before you start (once)

```bat
cd /d D:\Projects\SMART-MOCK-INTERVIEW
.bot\Scripts\python.exe -m pytest tests\app -q
.bot\Scripts\python.exe scripts\check_integrity.py
ollama list
```

`ollama list` must show `llama3.2:3b`. If the Ollama app isn't running, start it, or run `ollama serve` in another window. The first follow-up loads the model (about 28 s cold on your machine); the interview never waits for it.

## 2. Start the app with the objective engine

In a **new** Command Prompt (the variables apply only to this window):

```bat
cd /d D:\Projects\SMART-MOCK-INTERVIEW
set SMART_DEMO_FOLLOWUP_ENGINE=objective
set SMART_DEMO_FOLLOWUP_MODEL=llama3.2:3b
run_demo.bat --live-model
```

The banner should say `Experimental local-model concept check: ON`. Leave this window open. To go back to the default engine later, open a new window without the `set` lines.

## 3. Create a 20-minute interview

The UI has no length control. The default budget is 45 minutes, with 5 core questions and at most 2 follow-ups. To cap the interview at 20 minutes, create it through the app's own API from **PowerShell**:

```powershell
$b = @{ role = "Data Scientist"; interview_type = "technical"; followup_mode = "live"; time_budget_min = 20 } | ConvertTo-Json
$r = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:5000/demo/api/sessions -ContentType application/json -Body $b
$r.session_id
Start-Process ("http://127.0.0.1:5000" + $r.url)
```

- Valid roles: `Data Scientist`, `Machine Learning Engineer`, `NLP Engineer`, `Data Analyst`, `Python Developer`.
- `interview_type` can be `technical`, `behavioural` or `mixed`.
- Keep the printed `session_id`.

Alternatively, use the UI only: open `http://127.0.0.1:5000/demo/settings`, set **Follow-ups for new interviews** to **Local model (llama3.2:3b)**, then start from `/demo/new`. That interview has the 45-minute budget; finish it early with the finish button.

## 4. How to answer so the run tests what matters

- **Exercise memory.** In an early answer, describe something you really built in one sentence ("I built a churn model in scikit-learn on our CRM data"). Later follow-ups may refer back to it. They must only say what you said.
- **Exercise gap probing.** Give one answer that is correct but incomplete. The follow-up should ask about the missing part without teaching it.
- **Exercise misconception handling.** Give one answer with a common mistake (for example, "bubble sort is O(n) in the worst case"). The follow-up should ask for a concrete case, not correct you.
- Skip one question, and answer one very briefly. Neither should produce an invented follow-up.
- While you go, note anything a follow-up says about you that you did not say. That is the critical safety check.

## 5. What to inspect afterwards

**The final report:** `http://127.0.0.1:5000/demo/s/<session_id>/summary`. All interviews are listed at `/demo/history`. A download of everything shown is at `/demo/s/<session_id>/export.json`.

**The saved session:** `results\demo_sessions\<session_id>.json` (or the folder in `SMART_DEMO_DATA_DIR`). The fields that matter:

| where | what it tells you |
|---|---|
| `memory.items[]` | what was stored from your answers: `id`, `kind` (project, tool, explanation, …), `quote` (your exact words), `turn`, `confidence`, `status` (always a candidate claim, never verified) |
| `questions[]` with `"origin": "follow_up"` | each follow-up shown: `question`, `lead` (the code-built "Earlier you said …" sentence, empty if none), `memory_id` (attached by code, never by the model), `followup_kind` (`llm` = written by the model) |
| `plan.followup_log[]` | one entry per follow-up opportunity: `outcome` (`llm` shown, `fallback` standard question used, `skip`), `reasons` (why a model question was refused), `engine` (must be `objective`), `prompt_version` (must be `11.obj5`), `memory_offered`, `memory_cited`, `citation_dropped`, `memory_stage`, `fallback_class`, `attempts`, `latency_ms` |

Quick view of the follow-up log in PowerShell:

```powershell
$s = Get-Content "results\demo_sessions\$($r.session_id).json" -Raw | ConvertFrom-Json
$s.plan.followup_log | Select-Object n, outcome, engine, prompt_version, memory_cited, memory_stage, fallback_class, latency_ms, @{n='reasons';e={$_.reasons -join '; '}} | Format-Table -Wrap
$s.questions | Where-Object origin -eq 'follow_up' | Select-Object parent_n, followup_kind, memory_id, lead, question | Format-List
$s.memory.items | Select-Object id, kind, turn, quote | Format-Table -Wrap
```

## 6. What counts as a pass

**Hard failures** (stop and report):
- a follow-up that states something about you that you did not say;
- an "Earlier you said …" that misquotes you;
- a `memory_id` whose item does not contain what the question uses;
- `engine` not `objective`, or `prompt_version` not `11.obj5`;
- a crash or a wait longer than the deadline.

**Expected and fine:** several `fallback` outcomes. Each one means the model's question failed a check and a curated question was used instead.

**For human review** (rate them, don't trust the automatic acceptance):
- Is each follow-up technically correct?
- Does it read naturally?
- Does it ask about something you had not covered?

# Stage 3B - runbook (Phase 1 gate)

**Status: Phase 1 cannot be completed from here.** The Claude session reaches your PC only through file tools; it cannot run commands on Windows or see your local Ollama server. Only a `.ollama` folder (with `cache`) is visible in your home directory, which is not proof of an installed runtime or any model. Nothing was downloaded or installed, and no paid API was enabled.

## Step 1 - probe (read-only, 10 seconds)
```
cd D:\Projects\SMART-MOCK-INTERVIEW
python scripts\stage3b_probe_ollama.py
```
Writes `data\evaluation\stage3b\ollama_probe.json`: ollama executable, server reachability, installed models (size, parameters, quantisation), loaded models, RAM/CPU/GPU, rough fit per model. It never pulls, installs or changes anything. Send me the printed output or the JSON.

## Step 2 - if a suitable chat model is installed: smoke run (12 calls)
```
python scripts\stage3b_run.py --model <installed-name> --set smoke
python audit\evaluation\stage3b_analyze.py data\evaluation\stage3b\runs_<installed-name>.json
```
The runner exits without doing anything if the model isn't installed. It talks only to local Ollama (`OLLAMA_HOST` or 127.0.0.1:11434) with an explicit 8192-token context (Ollama silently truncates longer prompts; the analysis reports prompt token counts so truncation is detectable).

## Step 3 - only after the smoke run looks sane: full benchmark
```
python scripts\stage3b_run.py --model <name> --set full --repeats 3
python scripts\stage3b_run.py --model <name> --set full --repeats 1 --stress-temperature 0.3 --stress-repeats 2   # optional
```
The first run prints an ETA after each call; Ctrl+C keeps everything done so far.

## Rough resource expectations (estimates, NOT measured on your machine)
| model size (Q4) | weights | RAM/VRAM incl. 8k context | CPU-only speed | 129 calls (43x3) |
|---|---|---|---|---|
| ~3B | ~2 GB | ~4 GB | ~10-20 tok/s | ~1-2 h |
| ~7-8B | ~4.7 GB | ~7 GB | ~3-8 tok/s | ~3-8 h |
| ~14B | ~9 GB | ~12 GB | ~1-3 tok/s | too slow without a GPU |
Each call produces roughly 600-1,000 output tokens. With a GPU of enough VRAM these drop to minutes.

## If nothing suitable is installed (options - your decision, nothing will be downloaded without approval)
1. `qwen2.5:7b` (~4.7 GB) - already the default of the project's report writer (`llm_report.py`); the lowest-surprise choice.
2. `llama3.1:8b` (~4.9 GB) - similar size, different family (useful for cross-checking).
3. `qwen2.5:14b` (~9 GB) - better instruction following, needs ~12 GB free memory.
Models under ~3B or embedding-only models are unlikely to follow the 12-field JSON contract and the rubric.

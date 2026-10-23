@echo off
rem Stage 15: bounded LIVE check of the Stage 12 correctness evaluation with your local Ollama (3 answers; each needs one concept-check call and one contradiction call).
rem Prerequisites: Ollama running, `ollama pull qwen2.5:7b` done, Sentence-BERT cached (python src\model\Pretrained_NEURALN.py once). Expect roughly 10-30 minutes on CPU.
rem Nothing is simulated here: if Ollama or the model is missing the script says so and stops. Results: tmp\stage12_live\summary.md and results.json (review the verdicts by hand).
setlocal
cd /d "%~dp0"
set "PY=.bot\Scripts\python.exe"
if not exist "%PY%" set "PY=python"
curl -s -m 5 http://127.0.0.1:11434/api/tags | findstr /C:"qwen2.5:7b" >nul
if errorlevel 1 (
  echo Ollama is not reachable on 127.0.0.1:11434 or qwen2.5:7b is not installed. Start Ollama and run: ollama pull qwen2.5:7b
  exit /b 2
)
set SMART_DEMO_LIVE_MODULAR=1
"%PY%" scripts\stage12_assess_answers.py --live --out tmp\stage12_live --cases autoencoder_misconception autoencoder_paraphrase unsupervised_short
if errorlevel 1 exit /b 1
echo.
echo Done. Open tmp\stage12_live\summary.md and compare each verdict with the "expected" column by hand.

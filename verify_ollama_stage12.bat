@echo off
rem Stage 15: bounded LIVE check of the Stage 12 correctness evaluation with your local Ollama (9 answers: the 3 that failed on 23 Oct 2026 plus 6 independent ones; each needs one concept-check call, one contradiction call and one confirmation call per finding).
rem Prerequisites: Ollama running, `ollama pull qwen2.5:7b` done, Sentence-BERT cached (python src\model\Pretrained_NEURALN.py once). Expect roughly 20-60 minutes on CPU.
rem Nothing is simulated here: if Ollama or the model is missing the script says so and stops. Results: tmp\stage12_live_v2\summary.md and results.json (the first, failed run in tmp\stage12_live is kept as evidence) (review the verdicts by hand).
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
"%PY%" scripts\stage12_assess_answers.py --live --out tmp\stage12_live_v2 --cases autoencoder_misconception autoencoder_paraphrase unsupervised_short ind_ae_paraphrase ind_ae_wrong ind_unsup_correct ind_unsup_wrong ind_hyp_paraphrase ind_hyp_partial
if errorlevel 1 exit /b 1
echo.
echo Done. Open tmp\stage12_live_v2\summary.md and compare each verdict with the "expected" column by hand.

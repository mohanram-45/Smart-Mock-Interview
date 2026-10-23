@echo off
rem Stage 14: build the ML-enabled Docker image and PROVE real Sentence-BERT scoring works inside it (health alone does not prove it).
rem Needs Docker Desktop. Step 2 downloads the ~90 MB all-MiniLM-L6-v2 model ONCE into the smart-hf-cache volume (internet needed for that step only).
setlocal
cd /d "%~dp0"
echo [1/4] Building the image with INSTALL_ML=1 (large: torch, sentence-transformers, faiss)...
set SMART_INSTALL_ML=1
docker compose build app || goto fail
echo [2/4] Filling the model cache once (skipped automatically if it is already there)...
docker compose run --rm -e HF_HUB_OFFLINE=0 -e TRANSFORMERS_OFFLINE=0 app python -c "from sentence_transformers import SentenceTransformer as S; S('sentence-transformers/all-MiniLM-L6-v2'); print('model cached')" || goto fail
echo [3/4] Real scoring check inside the container (offline)...
docker compose run --rm app python scripts/verify_ml_scoring.py || goto fail
echo [4/4] Starting the app and checking health and readiness...
docker compose up -d app || goto fail
python scripts\healthcheck.py --ready
set RC=%errorlevel%
docker compose down
if not "%RC%"=="0" goto fail
echo.
echo ML-ENABLED DOCKER VERIFIED
exit /b 0
:fail
echo.
echo VERIFICATION FAILED - see the messages above.
exit /b 1

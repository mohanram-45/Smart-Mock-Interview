<#
.SYNOPSIS
  Stage 6C/7A: validate the SMART Mock Interview MLOps tooling on a real Windows machine. Read-only for your code and data.

.DESCRIPTION
  Runs the ten Stage 6C checks in order and prints PASS / FAIL / SKIP for each, with the exact command to fix anything that fails or is skipped.
  It never trains a model, never downloads a model, never pulls an Ollama model, never runs candidate code and never exposes anything beyond 127.0.0.1.
  Docker steps are skipped unless you pass -Docker (they build an image and start a container on 127.0.0.1:5099, then remove them).
  MLflow data is written to .\mlflow\ (git-ignored) when you pass -Mlflow.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\validate_windows.ps1
  powershell -ExecutionPolicy Bypass -File scripts\validate_windows.ps1 -Mlflow -Docker
  powershell -ExecutionPolicy Bypass -File scripts\validate_windows.ps1 -Mlflow -Docker -Dvc -Tests
#>
param(
  [switch]$Mlflow,   # import the historical results into ./mlflow and verify them (needs: pip install -r requirements-mlops.txt)
  [switch]$Docker,   # build the image and run scripts\verify_compose.py (needs Docker Desktop running)
  [switch]$Ollama,   # probe a local Ollama if one is running (never pulls a model)
  [switch]$Dvc,      # prove DVC reproducibility in a throw-away copy via scripts\verify_dvc.py (needs: pip install "dvc>=3,<4"; your repository is not touched)
  [switch]$Tests,    # also run the fast test suites (retrieval, evaluation, app, codeeval, mlops)
  [int]$Port = 5099
)
$ErrorActionPreference = 'Continue'
Set-Location (Split-Path -Parent $PSScriptRoot)
$script:Pass = 0; $script:Fail = 0; $script:Skip = 0
function Report($status, $name, $detail = '') {
  switch ($status) { 'PASS' { $script:Pass++ } 'FAIL' { $script:Fail++ } 'SKIP' { $script:Skip++ } }
  $line = "[$status] $name"; if ($detail) { $line += " - $detail" }
  Write-Host $line
}
function Section($t) { Write-Host ""; Write-Host "== $t" }

# ---- pick the project Python (same order as run_demo.bat)
$py = $null
foreach ($c in @('.bot\Scripts\python.exe', '.venv\Scripts\python.exe')) { if (Test-Path $c) { $py = (Resolve-Path $c).Path; break } }
if (-not $py) { $cmd = Get-Command python -ErrorAction SilentlyContinue; if ($cmd) { $py = $cmd.Source } }
$env:MLFLOW_DISABLE_AGENT_HINT = '1'
$env:PYTHONDONTWRITEBYTECODE = '1'

# ---- 1. required files and dependency versions
Section '1. Required files and dependency versions'
$required = @('Dockerfile', 'docker-compose.yml', '.dockerignore', '.env.example', '.gitattributes', '.gitignore', 'pyproject.toml', 'dvc.yaml', 'params.yaml',
  'requirements.txt', 'requirements-ci.lock', 'requirements-ci-mlops.lock', 'requirements-docker.lock', 'requirements-mlops.txt', '.github\workflows\ci.yml',
  '.github\workflows\heavy.yml', 'scripts\check_integrity.py', 'scripts\verify_mlops.py', 'scripts\verify_compose.py', 'scripts\healthcheck.py',
  'scripts\mlflow_import_history.py', 'scripts\check_staged.py', 'scripts\verify_dvc.py', 'src\mlops\tracking.py', 'data\retrieval\corpus_manifest.json', 'data\curated\v5\curated_questions.csv')
$missing = $required | Where-Object { -not (Test-Path $_) }
if ($missing) { Report 'FAIL' 'required files' ("missing: " + ($missing -join ', ')) } else { Report 'PASS' "all $($required.Count) required files present" }
if (-not $py) { Report 'FAIL' 'python' 'not found. Install Python 3.12 or 3.13 from python.org, or create .venv (python -m venv .venv)'; exit 1 }
$pv = & $py -c "import platform;print(platform.python_version())"
if ($pv -match '^3\.(12|13)\.') { Report 'PASS' 'python' "$pv ($py)" } else { Report 'FAIL' 'python version' "$pv - CI and the Docker image use 3.12/3.13. Create a venv with one of them." }
foreach ($m in @(@('flask', 'requirements.txt'), @('flask_cors', 'requirements.txt'), @('numpy', 'requirements.txt'), @('sklearn', 'requirements.txt'), @('pydantic', 'requirements-rag.txt'),
    @('pytest', 'pip install pytest'), @('yaml', 'pip install pyyaml'))) {
  $v = & $py -c "import importlib.metadata as m,importlib;importlib.import_module('$($m[0])');print('ok')" 2>$null
  if ($v -eq 'ok') { Report 'PASS' "import $($m[0])" } else { Report 'FAIL' "import $($m[0])" "pip install -r $($m[1])" }
}
$ruffv = & $py -m ruff --version 2>$null
if ($LASTEXITCODE -eq 0) { Report 'PASS' 'ruff' $ruffv } else { Report 'SKIP' 'ruff not installed' "pip install --require-hashes -r requirements-ci.lock   (only needed to reproduce the CI lint job)" }
$gv = git --version 2>$null
if ($gv) { Report 'PASS' 'git' $gv } else { Report 'SKIP' 'git not on PATH' 'install Git for Windows (needed for the first push)' }
if ($gv) {
  $crlf = (git config --get core.autocrlf) 2>$null
  Report 'PASS' 'core.autocrlf' ("'" + $crlf + "' (harmless here: .gitattributes forces LF for the hash-pinned data)")
}
$bytes = [System.IO.File]::ReadAllBytes((Resolve-Path 'data\curated\v5\curated_questions.csv').Path)
$hasCrlf = $false; for ($i = 0; $i -lt [Math]::Min($bytes.Length, 400000) - 1; $i++) { if ($bytes[$i] -eq 13 -and $bytes[$i + 1] -eq 10) { $hasCrlf = $true; break } }
if ($hasCrlf) { Report 'FAIL' 'hash-pinned corpus CSV has Windows line endings (CRLF)' 'see the HINT printed by check 3, then: git config core.autocrlf false; git rm --cached -r -q .; git reset --hard' } else { Report 'PASS' 'hash-pinned corpus CSV uses LF line endings' }

# ---- 2. verify_mlops (read-only)
Section '2. scripts\verify_mlops.py (the same program verify_mlops.bat runs)'
& $py scripts\verify_mlops.py
if ($LASTEXITCODE -eq 0) { Report 'PASS' 'verify_mlops.py exit code 0' } else { Report 'FAIL' 'verify_mlops.py' "exit code $LASTEXITCODE - read the [FAIL] lines above" }

# ---- 3. frozen corpus and experiment integrity
Section '3. Frozen corpus and experiment integrity'
& $py scripts\check_integrity.py
if ($LASTEXITCODE -eq 0) { Report 'PASS' 'dataset and frozen-experiment integrity (666 records; freeze v2; bench_v2)' } else { Report 'FAIL' 'integrity' 'something differs from the frozen hashes. Do NOT edit a manifest; restore the file from Git.' }

# ---- 3c. version consistency (corpus vs DVC params vs served format vs indexes vs frozen files)
Section '3c. Version consistency'
& $py scripts\check_versions.py
if ($LASTEXITCODE -eq 0) { Report 'PASS' 'version consistency (corpus, DVC params, served format, indexes, frozen files)' } else { Report 'FAIL' 'version consistency' 'something disagrees: read the FAIL lines above. A stale index is rebuilt with: python -m src.retrieval.cli build --local-files-only' }

# ---- 3b. byte-exact pinned files (stored with Windows line endings; must never be converted) and publication safety
Section '3b. Byte-exact pinned files and publication safety'
$sumFile = 'data\retrieval\eval\immutable_pre_pooling_stage2b\SHA256SUMS.txt'
if (Test-Path $sumFile) {
  $bad = @(); $n = 0
  foreach ($line in (Get-Content $sumFile)) {
    if ($line -match '^([0-9a-fA-F]{64})\s+\*?(.+)$') {
      $n++; $f = Join-Path (Split-Path $sumFile) $Matches[2].Trim()
      if ((-not (Test-Path $f)) -or ((Get-FileHash -Algorithm SHA256 $f).Hash.ToLower() -ne $Matches[1].ToLower())) { $bad += $Matches[2].Trim() }
    }
  }
  if ($bad.Count -eq 0 -and $n -gt 0) { Report 'PASS' "immutable Stage 2B files are byte-identical to their checksums ($n files)" }
  else { Report 'FAIL' 'immutable Stage 2B files differ from their checksums' ("changed: " + ($bad -join ', ') + " - restore them from Git; .gitattributes marks them -text so Git never converts their line endings") }
} else { Report 'SKIP' 'Stage 2B checksum file not present' $sumFile }
if ($gv) {
  git rev-parse --is-inside-work-tree 2>$null | Out-Null
  if ($LASTEXITCODE -eq 0) {
    & $py scripts\check_staged.py --worktree
    if ($LASTEXITCODE -eq 0) { Report 'PASS' 'publication check: nothing blocked, oversized, credential-shaped or personal in what git add -A would publish' }
    else { Report 'FAIL' 'publication check' 'read the FAIL lines above; do not commit until they are gone' }
  } else { Report 'SKIP' 'not a Git repository here' 'python scripts\check_staged.py --worktree' }
} else { Report 'SKIP' 'publication check needs git' 'python scripts\check_staged.py --worktree' }

# ---- 4. + 5. MLflow install, database, import, idempotency
Section '4-5. MLflow installation, database configuration, historical import, idempotency'
$ml = & $py -c "import importlib.util as u;print('yes' if u.find_spec('mlflow') and u.find_spec('sqlalchemy') else 'no')" 2>$null
if ($ml -ne 'yes') { Report 'SKIP' 'full MLflow package not installed' 'pip install -r requirements-mlops.txt' }
else {
  $mv = & $py -c "import mlflow;print(mlflow.__version__)"
  $uri = & $py -c "from src.mlops import tracking;print(tracking.tracking_uri())"
  Report 'PASS' 'MLflow installed' "version $mv, tracking uri $uri"
  if ($gv) {
    git check-ignore -q mlflow/mlflow.db 2>$null
    if ($LASTEXITCODE -eq 0) { Report 'PASS' 'mlflow\ database is git-ignored' }
    elseif ($LASTEXITCODE -eq 1) { Report 'FAIL' 'mlflow\ is not git-ignored' 'check .gitignore (mlflow/ must be listed)' }
    else { Report 'SKIP' 'not a Git repository here, cannot check .gitignore' 'git check-ignore -v mlflow/mlflow.db' }
  }
  if ($Mlflow) {
    $out1 = & $py scripts\mlflow_import_history.py 2>&1 | Out-String
    $out2 = & $py scripts\mlflow_import_history.py 2>&1 | Out-String
    Write-Host ($out2.Trim())
    if ($out2 -match '0 created, 30 already present' -and $out2 -match 'MLflow records match') { Report 'PASS' 'import is idempotent and 30 runs / 642 metrics match the source files' }
    else { Report 'FAIL' 'MLflow import/verify' 'first run output:' ; Write-Host $out1 }
  } else { Report 'SKIP' 'historical import (opt in with -Mlflow)' 'python scripts\mlflow_import_history.py ; then: mlflow ui --backend-store-uri sqlite:///mlflow/mlflow.db' }
}

# ---- 5b. DVC
Section '5b. DVC configuration and index reproducibility'
$dvcv = & $py -m dvc --version 2>$null
if ($LASTEXITCODE -ne 0) { Report 'SKIP' 'DVC not installed' 'pip install "dvc>=3,<4"' }
else {
  Report 'PASS' 'DVC installed' "version $dvcv"
  if (Test-Path '.dvc') { Report 'PASS' '.dvc repository present' } else { Report 'SKIP' 'DVC repository not initialised' 'dvc init   (creates only .dvc\config; see docs\REPRODUCIBILITY.md)' }
  if ($Dvc) {
    & $py scripts\verify_dvc.py
    if ($LASTEXITCODE -eq 0) { Report 'PASS' 'verify_dvc.py: dvc repro, status, delete + checkout give a byte-identical index (dev-lsa stand-in, temporary copy)' }
    else { Report 'FAIL' 'verify_dvc.py' "exit code $LASTEXITCODE - see the [FAIL] lines above" }
  } else { Report 'SKIP' 'index reproducibility (opt in with -Dvc)' 'python scripts\verify_dvc.py' }
}

# ---- 6-8. Docker Desktop, real image build, Compose, health, persistence
Section '6-8. Docker Desktop, image build, Compose, health checks, persistent sessions'
$dk = Get-Command docker -ErrorAction SilentlyContinue
if (-not $dk) { Report 'SKIP' 'docker not on PATH' 'install Docker Desktop (WSL2 backend), start it, then re-run with -Docker' }
else {
  $sv = docker version --format '{{.Server.Os}}/{{.Server.Version}}' 2>$null
  if ($LASTEXITCODE -ne 0) { Report 'SKIP' 'Docker Desktop is installed but the engine is not running' 'start Docker Desktop, wait for "Engine running", then re-run with -Docker' }
  else {
    Report 'PASS' 'Docker engine reachable' $sv
    if ($Docker) {
      & $py scripts\verify_compose.py --port $Port
      if ($LASTEXITCODE -eq 0) { Report 'PASS' 'verify_compose.py: build with the intended base image, health, readiness, non-root, loopback-only, persistence, privacy' }
      else { Report 'FAIL' 'verify_compose.py' "exit code $LASTEXITCODE - see the [FAIL] lines above" }
    } else { Report 'SKIP' 'image build + Compose run (opt in with -Docker; takes a few minutes)' "python scripts\verify_compose.py --port $Port" }
  }
}

# ---- 9. no training or downloading at normal startup
Section '9. Normal startup does not train or download'
$before = @(Get-ChildItem -Path results -Recurse -File -ErrorAction SilentlyContinue | Where-Object { $_.Extension -in '.pt', '.pth', '.bin', '.safetensors' } | ForEach-Object { "$($_.FullName)|$($_.Length)|$($_.LastWriteTimeUtc.Ticks)" })
$hfRoot = if ($env:HF_HOME) { $env:HF_HOME } else { Join-Path $HOME '.cache\huggingface' }
$hfBefore = if (Test-Path $hfRoot) { (Get-ChildItem $hfRoot -Recurse -File -ErrorAction SilentlyContinue | Measure-Object).Count } else { 0 }
$env:HF_HUB_OFFLINE = '1'; $env:TRANSFORMERS_OFFLINE = '1'; $env:SMART_FORBID_MODEL_TRAINING = '1'
$tmpSess = Join-Path ([System.IO.Path]::GetTempPath()) ("smart-validate-" + [guid]::NewGuid().ToString('N'))
$env:SMART_DEMO_DATA_DIR = $tmpSess
& $py -c "import importlib.util as u,sys;s=u.spec_from_file_location('a','main/app.py');m=u.module_from_spec(s);s.loader.exec_module(m);c=m.app.test_client();assert c.get('/healthz').status_code==200;assert c.get('/readyz').status_code==200;print('app started, health and readiness OK; torch imported:', 'torch' in sys.modules)"
$startOk = ($LASTEXITCODE -eq 0)
Remove-Item Env:\SMART_DEMO_DATA_DIR -ErrorAction SilentlyContinue
if (Test-Path $tmpSess) { Remove-Item -Recurse -Force $tmpSess -ErrorAction SilentlyContinue }
$after = @(Get-ChildItem -Path results -Recurse -File -ErrorAction SilentlyContinue | Where-Object { $_.Extension -in '.pt', '.pth', '.bin', '.safetensors' } | ForEach-Object { "$($_.FullName)|$($_.Length)|$($_.LastWriteTimeUtc.Ticks)" })
$hfAfter = if (Test-Path $hfRoot) { (Get-ChildItem $hfRoot -Recurse -File -ErrorAction SilentlyContinue | Measure-Object).Count } else { 0 }
if ($startOk -and (-not (Compare-Object $before $after)) -and ($hfBefore -eq $hfAfter)) { Report 'PASS' 'startup created/changed no checkpoint under results\ and added no Hugging Face cache files' "($hfAfter files in $hfRoot before and after)" }
else { Report 'FAIL' 'startup side effects' "app started: $startOk; checkpoints changed: $([bool](Compare-Object $before $after)); HF files $hfBefore -> $hfAfter" }
Remove-Item Env:\SMART_FORBID_MODEL_TRAINING, Env:\HF_HUB_OFFLINE, Env:\TRANSFORMERS_OFFLINE -ErrorAction SilentlyContinue

# ---- 10. optional Ollama
Section '10. Optional Ollama (only if installed and running)'
if ($Ollama) { & $py scripts\verify_mlops.py --skip-mlflow --check-ollama 2>&1 | Select-String -Pattern 'Ollama|ollama|qwen' | ForEach-Object { Write-Host $_.Line } }
else {
  $oc = Get-Command ollama -ErrorAction SilentlyContinue
  if ($oc) { Report 'SKIP' 'Ollama is installed (probe is opt-in with -Ollama)' 'ollama list' } else { Report 'SKIP' 'Ollama not installed' 'optional: only the opt-in live Qwen evaluation needs it' }
}

# ---- optional fast test suites
if ($Tests) {
  Section 'Regression tests'
  foreach ($t in @('retrieval', 'evaluation', 'app', 'codeeval', 'mlops')) {
    & $py -m pytest (Join-Path 'tests' $t) -q -p no:cacheprovider 2>&1 | Select-Object -Last 3 | ForEach-Object { Write-Host $_ }
    if ($LASTEXITCODE -eq 0) { Report 'PASS' "tests/$t" } else { Report 'FAIL' "tests/$t" 'see the output above' }
  }
}

Write-Host ""
Write-Host "== summary: $script:Pass PASS, $script:Fail FAIL, $script:Skip SKIP"
if ($script:Skip -gt 0) { Write-Host "   SKIP means 'not verified on this machine' - each line names the command that verifies it." }
exit ($(if ($script:Fail -gt 0) { 1 } else { 0 }))

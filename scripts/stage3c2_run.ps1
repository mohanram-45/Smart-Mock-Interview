# Stage 3C-2 - the ONE command for the controlled modular Qwen experiment. Run from the project root in PowerShell:
#     powershell -ExecutionPolicy Bypass -File scripts\stage3c2_run.ps1
# Optional first look at 2 answers only (marked partial, not the frozen experiment):  ... -File scripts\stage3c2_run.ps1 -Ids s2-f01,b2-006
# - verifies the freeze (refuses to run if any frozen file changed), builds all prompts offline first (dry run)
# - never downloads or pulls a model; refuses to run if qwen2.5:7b is not installed
# - unloads any OTHER loaded model first (one LLM in memory at a time); then samples RAM / GPU / ollama ps every 10 s
# - writes to data\evaluation\stage3c2_results\<timestamp>\ ; nothing existing is modified
param([string]$Ids = "")
$ErrorActionPreference = "Stop"
$model = "qwen2.5:7b"
python scripts\stage3c2_freeze.py verify
python scripts\stage3c2_run.py --dry-run
if ($LASTEXITCODE -ne 0) { throw "dry run failed - nothing was sent to the model" }

$stamp = Get-Date -Format "yyyyMMddTHHmmss"
$mon = "data\evaluation\stage3c2_results\_monitor_$stamp"
New-Item -ItemType Directory -Force -Path $mon | Out-Null
Write-Host "== loaded models before =="; ollama ps
(ollama ps | Select-Object -Skip 1) | ForEach-Object { $n = ($_ -split "\s+")[0]; if ($n -and $n -ne $model) { Write-Host "unloading $n"; ollama stop $n } }
Start-Sleep -Seconds 3
$os = Get-CimInstance Win32_OperatingSystem
"free RAM before: {0:N1} GB of {1:N1} GB" -f ($os.FreePhysicalMemory/1MB), ($os.TotalVisibleMemorySize/1MB) | Tee-Object -FilePath "$mon\memory_before.txt"
if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) { nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv | Tee-Object -Append -FilePath "$mon\memory_before.txt" }
if ($os.FreePhysicalMemory/1MB -lt 6) { Write-Warning "Less than 6 GB RAM free - close browsers/IDEs (Ctrl+C to abort)."; Start-Sleep -Seconds 10 }

$sampler = Start-Job -ArgumentList (Resolve-Path $mon).Path -ScriptBlock {
  param($dir)
  while ($true) {
    $o = Get-CimInstance Win32_OperatingSystem
    $gpu = ""; if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) { $gpu = (nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader) -join ";" }
    $ps = ((ollama ps | Select-Object -Skip 1) -join " | ") -replace "\s+"," "
    "{0},{1:N2},{2},{3}" -f (Get-Date -Format s), ($o.FreePhysicalMemory/1MB), $gpu, $ps | Add-Content -Path "$dir\memory_samples.csv"
    Start-Sleep -Seconds 10
  }
}
try {
  if ($Ids) { python scripts\stage3c2_run.py --ids $Ids } else { python scripts\stage3c2_run.py }
  $latest = Get-ChildItem data\evaluation\stage3c2_results -Directory | Where-Object { $_.Name -notlike "_monitor*" } | Sort-Object Name | Select-Object -Last 1
  python audit\evaluation\stage3c2_analyze.py "$($latest.FullName)\results.json"
} finally {
  Stop-Job $sampler; Remove-Job $sampler
  Write-Host "== loaded models after =="; ollama ps
  Write-Host "Send back the whole folder: data\evaluation\stage3c2_results\ (results.json, analysis.md, analysis.json, $mon)"
}

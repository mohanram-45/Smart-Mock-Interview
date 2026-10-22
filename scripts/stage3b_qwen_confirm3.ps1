# Stage 3B - Qwen 2.5 7B confirmation run with schema-constrained output (--schema): B04, B03, B07 plus B01 and B13 controls. Run from the project root in PowerShell:
#     powershell -ExecutionPolicy Bypass -File scripts\stage3b_qwen_confirm3.ps1
# - never downloads or pulls a model; refuses to run if qwen2.5:7b is not installed (the run script checks)
# - unloads any other loaded model first (one LLM in memory at a time)
# - samples RAM / VRAM / ollama ps every 10 s into the output folder
# - writes to data\evaluation\stage3b_qwen_v3 (the original Qwen and llama results are not touched)
$ErrorActionPreference = "Stop"
$model = "qwen2.5:7b"
$out   = "data\evaluation\stage3b_qwen_v3"
New-Item -ItemType Directory -Force -Path $out | Out-Null

Write-Host "== loaded models before =="; ollama ps
# unload anything loaded (frees VRAM/RAM); ignore errors
(ollama ps | Select-Object -Skip 1) | ForEach-Object { $n = ($_ -split "\s+")[0]; if ($n) { Write-Host "unloading $n"; ollama stop $n } }
Start-Sleep -Seconds 3

$os = Get-CimInstance Win32_OperatingSystem
"free RAM before: {0:N1} GB of {1:N1} GB" -f ($os.FreePhysicalMemory/1MB), ($os.TotalVisibleMemorySize/1MB) | Tee-Object -FilePath "$out\memory_before.txt"
if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) { nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv | Tee-Object -Append -FilePath "$out\memory_before.txt" }
if ($os.FreePhysicalMemory/1MB -lt 6) { Write-Warning "Less than 6 GB RAM free - close browsers/IDEs before continuing (Ctrl+C to abort)."; Start-Sleep -Seconds 10 }

# background sampler
$sampler = Start-Job -ArgumentList (Resolve-Path $out).Path -ScriptBlock {
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
  python scripts\stage3b_run.py --model $model --set smoke --schema --items B04,B03,B07,B01,B13 --repeats 1 --timeout 900 --out-dir $out
  $runs = "$out\runs_qwen2.5_7b.json"
  python audit\evaluation\stage3b_analyze.py $runs
  python audit\evaluation\stage3b_compare.py data\evaluation\stage3b_qwen_v2\runs_qwen2.5_7b.json $runs
} finally {
  Stop-Job $sampler; Remove-Job $sampler
  Write-Host "== loaded models after =="; ollama ps
  Write-Host "Send back: $out\runs_qwen2.5_7b.json, analysis_qwen2.5_7b.json, memory_before.txt, memory_samples.csv"
}

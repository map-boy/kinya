param([Parameter(Mandatory)][ValidateSet("sync-data","run","status","log","check","watch")]$Action)
$k = Get-Content "$env:USERPROFILE\.kaggle\kaggle.json" | ConvertFrom-Json
$slug = "$($k.username)/kinya-autorun"
$u8 = New-Object System.Text.UTF8Encoding $false
$env:PYTHONUTF8 = "1"

function Show-Status {
  $t = (kaggle kernels status $slug 2>&1 | Out-String).Trim()
  if     ($t -match "COMPLETE")           { Write-Host "STATUS: COMPLETE (finished)" -ForegroundColor Green }
  elseif ($t -match "ERROR|FAIL|CANCEL")  { Write-Host "STATUS: FAILED  -> $t" -ForegroundColor Red }
  elseif ($t -match "RUNNING|QUEUED")     { Write-Host "STATUS: STILL RUNNING / QUEUED" -ForegroundColor Yellow }
  else                                    { Write-Host "STATUS: $t" -ForegroundColor Cyan }
}

function Show-Log {
  Remove-Item "$PSScriptRoot\out" -Recurse -Force -ErrorAction SilentlyContinue
  kaggle kernels output $slug -p "$PSScriptRoot\out" 2>&1 | Out-Null
  $f = "$PSScriptRoot\out\run.log"
  if (-not (Test-Path $f)) { Write-Host "No run.log yet (run not finished, or it stopped before logging)." -ForegroundColor Yellow; return }
  $lines = Get-Content $f
  foreach ($l in ($lines | Select-Object -Last 80)) {
    if     ($l -match "-> exit 0")                                  { Write-Host $l -ForegroundColor Green }
    elseif ($l -match "-> exit [1-9]|CRASH|MISSING|Traceback|FAILED|SystemExit|Error") { Write-Host $l -ForegroundColor Red }
    elseif ($l -match "SUMMARY")                                    { Write-Host $l -ForegroundColor Cyan }
    else                                                            { Write-Host $l }
  }
  $s = $lines | Where-Object { $_ -match "SUMMARY" } | Select-Object -Last 1
  Write-Host "`n===== STAGE RESULTS =====" -ForegroundColor Cyan
  if ($s) {
    foreach ($m in [regex]::Matches($s, "'(\w+)':\s*(\d+)")) {
      $ok = $m.Groups[2].Value -eq "0"
      Write-Host ("  {0,-8} {1}" -f $m.Groups[1].Value, $(if ($ok) { "OK" } else { "FAILED (exit " + $m.Groups[2].Value + ")" })) -ForegroundColor $(if ($ok) { "Green" } else { "Red" })
    }
  } else { Write-Host "  no SUMMARY line: the run did not reach the end" -ForegroundColor Red }
}

function Push-Run {
  $s = Get-Content "$PSScriptRoot\secrets.local.json" -Raw | ConvertFrom-Json
  $tmp = Join-Path $env:TEMP "kinya_push"
  Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
  New-Item -ItemType Directory $tmp | Out-Null
  Copy-Item "$PSScriptRoot\kernel-metadata.json" $tmp
  $code = [IO.File]::ReadAllText("$PSScriptRoot\run_kinya.py")
  $code = $code.Replace('log(f"MISSING secret {sec} (attach it to this notebook on kaggle.com)")', 'pass')
  $hdr = "import os`nos.environ['HF_TOKEN']='$($s.hf)'`nos.environ['HUGGINGFACE_HUB_TOKEN']='$($s.hf)'`nos.environ['GROQ_API_KEY']='$($s.groq)'`nos.environ['MISTRAL_API_KEY']='$($s.mistral)'`n"
  [IO.File]::WriteAllText("$tmp\run_kinya.py", $hdr + $code, $u8)
  kaggle kernels push -p $tmp
  Remove-Item $tmp -Recurse -Force
}

function Watch-Run {
  $t0 = Get-Date; $n = 0; $spin = '|','/','-','\'
  Write-Host "Watching $slug (Ctrl+C stops watching only; the Kaggle job keeps running)" -ForegroundColor Cyan
  while ($true) {
    $raw = (kaggle kernels status $slug 2>&1 | Out-String).Trim()
    $el = (Get-Date) - $t0; $clock = "{0:00}:{1:00}:{2:00}" -f [int]$el.TotalHours, $el.Minutes, $el.Seconds
    if     ($raw -match "COMPLETE")          { $state = "DONE";    break }
    elseif ($raw -match "ERROR|FAIL|CANCEL") { $state = "FAILED";  break }
    elseif ($raw -match "RUNNING")           { $msg = "RUNNING  "; $col = "Green" }
    elseif ($raw -match "QUEUED")            { $msg = "QUEUED   "; $col = "Yellow" }
    else                                     { $msg = "NO REPLY (retrying)"; $col = "DarkYellow" }
    Write-Host ("`r{0} {1} elapsed {2}   " -f $spin[$n % 4], $msg, $clock) -NoNewline -ForegroundColor $col
    $n++; Start-Sleep -Seconds 3
  }
  Write-Host ""
  [console]::beep(900, 400)
  if ($state -eq "DONE") { Write-Host "FINISHED after $clock" -ForegroundColor Green }
  else { Write-Host "FAILED after $clock -> $raw" -ForegroundColor Red }
  Show-Log
  if ($state -eq "FAILED") {
    Write-Host "`n===== WHAT FAILED (error lines from log) =====" -ForegroundColor Red
    $lf = "$PSScriptRoot\out\run.log"
    if (Test-Path $lf) { Get-Content $lf | Where-Object { $_ -match "-> exit [1-9]|CRASH|Traceback|Error|MISSING|SystemExit|429|FAILED" } | Select-Object -Last 15 | ForEach-Object { Write-Host $_ -ForegroundColor Red } }
    else { Write-Host "No run.log: the job died before logging. Open the Kaggle page above and read the notebook log." -ForegroundColor Red }
  }
  Write-Host "`n===== HUGGING FACE =====" -ForegroundColor Cyan
  python "$PSScriptRoot\check_hf.py"
}

switch ($Action) {
  "sync-data" { python "$PSScriptRoot\sync_data.py" }
  "run"       { Push-Run }
  "status"    { Show-Status }
  "log"       { Show-Log }
  "watch"     { Watch-Run }
  "check"     { Show-Status; Show-Log; Write-Host "`n===== HUGGING FACE =====" -ForegroundColor Cyan; python "$PSScriptRoot\check_hf.py" }
}
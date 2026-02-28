param(
  [int]$Port = 19000
)

$ErrorActionPreference = "Stop"
$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectDir

Write-Host "[1/3] Closing listeners on port $Port ..."
$pidSet = New-Object 'System.Collections.Generic.HashSet[int]'

Get-CimInstance Win32_Process |
  Where-Object { $_.Name -eq "python.exe" -and $_.CommandLine -like "*uvicorn*server:app*" } |
  ForEach-Object {
    try {
      Stop-Process -Id $_.ProcessId -Force -ErrorAction Stop
      Write-Host "  - stopped existing uvicorn PID $($_.ProcessId)"
    } catch {
      Write-Host "  - skip uvicorn PID $($_.ProcessId)"
    }
  }

try {
  $listeners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
  foreach ($l in $listeners) {
    [void]$pidSet.Add([int]$l.OwningProcess)
  }
} catch {
}

$netstatLines = netstat -ano | Select-String (":$Port")
foreach ($line in $netstatLines) {
  $parts = ($line -replace '^\s+', '') -split '\s+'
  if ($parts.Length -ge 5) {
    $rawPid = $parts[-1]
    $pidValue = 0
    if ([int]::TryParse($rawPid, [ref]$pidValue)) {
      [void]$pidSet.Add($pidValue)
    }
  }
}

foreach ($procId in $pidSet) {
  if ($procId -gt 0 -and $procId -ne $PID) {
    try {
      Stop-Process -Id $procId -Force -ErrorAction Stop
      Write-Host "  - stopped PID $procId"
    } catch {
      try {
        taskkill /PID $procId /F | Out-Null
        Write-Host "  - killed PID $procId via taskkill"
      } catch {
        Write-Host "  - skip PID $procId (already gone or not accessible)"
      }
    }
  }
}

Start-Sleep -Seconds 1

if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {
  Write-Host "  - port $Port is still occupied; switching to fallback port 19001"
  $Port = 19001
}

Write-Host "[2/3] Starting FastAPI server on port $Port ..."
Write-Host "[3/3] Command: python -m uvicorn server:app --host 0.0.0.0 --port $Port --env-file .env"
python -m uvicorn server:app --host 0.0.0.0 --port $Port --env-file .env

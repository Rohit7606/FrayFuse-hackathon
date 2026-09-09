<#
.SYNOPSIS
    Start the FrayFuse API and frontend together for a demo run.

.DESCRIPTION
    PERSON_B.md §7 asks for one command that brings up both halves, to remove a
    class of stage error.  Two things it does deliberately:

      * uvicorn runs WITHOUT --reload.  The file watcher can restart the
        backend mid-presentation, which is §9's named trap
      * the frontend runs `dev:live`, not `dev`, so it hits the API rather than
        the committed mocks

    Ctrl+C stops both.

.PARAMETER Network
    Path to the network JSON to serve.  The entire real-data switch is this one
    value — it sets FRAYFUSE_NETWORK, which api/config.py reads.

.EXAMPLE
    ./scripts/demo.ps1
    ./scripts/demo.ps1 -Network data/real/network.json
#>
param(
    [string]$Network = "data/mock/network.json",
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

if (-not (Test-Path $Network)) {
    Write-Error "network file not found: $Network"
}
if (-not (Test-Path "web/node_modules")) {
    Write-Error "web/node_modules missing - run 'npm install' in web/ first"
}

$env:FRAYFUSE_NETWORK = $Network
Write-Host "FrayFuse demo" -ForegroundColor Cyan
Write-Host "  network  $Network"
Write-Host "  api      http://localhost:$Port"
Write-Host "  frontend http://localhost:5173  (live API, not mocks)"
Write-Host "  Ctrl+C stops both." -ForegroundColor DarkGray
Write-Host ""

# No --reload: the watcher restarting mid-demo is PERSON_B.md §9's trap.
$api = Start-Process -PassThru -NoNewWindow python `
    -ArgumentList "-m", "uvicorn", "api.main:app", "--port", "$Port"

try {
    # Fail loudly here rather than letting the frontend come up against nothing.
    $up = $false
    foreach ($attempt in 1..30) {
        Start-Sleep -Milliseconds 500
        if ($api.HasExited) { throw "API exited during startup (exit $($api.ExitCode))" }
        try {
            Invoke-RestMethod "http://localhost:$Port/health" -TimeoutSec 2 | Out-Null
            $up = $true
            break
        } catch { }
    }
    if (-not $up) { throw "API did not answer /health within 15s" }

    Write-Host "API healthy, starting frontend..." -ForegroundColor Green
    Set-Location (Join-Path $repo "web")
    npm run dev:live
}
finally {
    if ($api -and -not $api.HasExited) {
        Write-Host "`nstopping API..." -ForegroundColor DarkGray
        Stop-Process -Id $api.Id -Force -ErrorAction SilentlyContinue
    }
}

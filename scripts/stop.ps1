[CmdletBinding()]
param()

$projectRoot = Split-Path -Parent $PSScriptRoot
$pidFile = Join-Path $projectRoot 'logs\service-pids.json'
if (-not (Test-Path -LiteralPath $pidFile)) {
    Write-Host 'No service PID file was found.'
    exit 0
}

$services = Get-Content -LiteralPath $pidFile -Raw | ConvertFrom-Json
foreach ($service in @($services)) {
    $process = Get-Process -Id $service.Id -ErrorAction SilentlyContinue
    if ($process) {
        & taskkill.exe /PID $service.Id /T /F | Out-Null
        Write-Host "Stopped $($service.Name) (PID $($service.Id))."
    }
}

Remove-Item -LiteralPath $pidFile

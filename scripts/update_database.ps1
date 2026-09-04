[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$localEnvironment = Join-Path $projectRoot 'config\local.env.ps1'

if (Test-Path -LiteralPath $localEnvironment) {
    . $localEnvironment
}

foreach ($variableName in 'STRESS_DB_PASSWORD', 'DJANGO_SECRET_KEY') {
    if ([string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($variableName, 'Process'))) {
        throw "$variableName is required. Copy config\environment.example.ps1 to config\local.env.ps1 and set private values."
    }
}

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw 'Python launcher (py) was not found.'
}

Write-Host 'Creating or updating MySQL tables...'
& py -3.11 (Join-Path $projectRoot 'src\analytics\create_ml_tables.py')
if ($LASTEXITCODE -ne 0) {
    throw 'MySQL table initialization failed. Check that MySQL80 is running and the STRESS_DB_* settings are correct.'
}

Write-Host 'Applying Django migrations...'
& py -3.11 (Join-Path $PSScriptRoot 'run_django.py') migrate --noinput
if ($LASTEXITCODE -ne 0) {
    throw 'Django migration failed.'
}

Write-Host 'Database update completed without clearing existing analysis data.'

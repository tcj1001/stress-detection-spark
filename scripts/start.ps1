[CmdletBinding()]
param(
    [switch]$SkipDatabaseUpdate
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$logDirectory = Join-Path $projectRoot 'logs'
$pidFile = Join-Path $logDirectory 'service-pids.json'
$mavenSettings = Join-Path $projectRoot 'config\maven-settings.xml'
$localEnvironment = Join-Path $projectRoot 'config\local.env.ps1'

if (Test-Path -LiteralPath $localEnvironment) {
    . $localEnvironment
}

foreach ($variableName in 'STRESS_DB_PASSWORD', 'DJANGO_SECRET_KEY', 'STRESS_JWT_SECRET') {
    if ([string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($variableName, 'Process'))) {
        throw "$variableName is required. Copy config\environment.example.ps1 to config\local.env.ps1 and set private values."
    }
}

New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null

function Test-LocalPort {
    param([int]$Port)
    return [bool](Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue)
}

function Wait-LocalPort {
    param([int]$Port, [string]$Name, [int]$TimeoutSeconds = 90)
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-LocalPort -Port $Port) {
            Write-Host "$Name is ready on port $Port."
            return
        }
        Start-Sleep -Milliseconds 500
    }
    throw "$Name did not listen on port $Port within $TimeoutSeconds seconds. Check $logDirectory."
}

foreach ($command in 'py', 'mvn', 'npm') {
    if (-not (Get-Command $command -ErrorAction SilentlyContinue)) {
        throw "$command was not found in PATH."
    }
}

if (-not (Test-LocalPort -Port 3306)) {
    throw 'MySQL is not listening on port 3306. Start the MySQL80 service first.'
}

if (-not $SkipDatabaseUpdate) {
    & (Join-Path $PSScriptRoot 'update_database.ps1')
}

$services = @()
if (Test-Path -LiteralPath $pidFile) {
    try {
        $services = @(
            @(Get-Content -LiteralPath $pidFile -Raw | ConvertFrom-Json) |
                Where-Object { Get-Process -Id $_.Id -ErrorAction SilentlyContinue }
        )
    }
    catch {
        $services = @()
    }
}

if (-not (Test-LocalPort -Port 8000)) {
    $django = Start-Process -FilePath (Get-Command py).Source `
        -ArgumentList @('-3.11', (Join-Path $PSScriptRoot 'run_django.py')) `
        -WorkingDirectory $projectRoot `
        -RedirectStandardOutput (Join-Path $logDirectory 'django.out.log') `
        -RedirectStandardError (Join-Path $logDirectory 'django.err.log') `
        -WindowStyle Hidden -PassThru
    $services += [pscustomobject]@{ Name = 'Django'; Id = $django.Id }
}

if (-not (Test-LocalPort -Port 8080)) {
    $spring = Start-Process -FilePath (Get-Command mvn).Source `
        -ArgumentList @('-s', $mavenSettings, 'spring-boot:run') `
        -WorkingDirectory (Join-Path $projectRoot 'src\springboot') `
        -RedirectStandardOutput (Join-Path $logDirectory 'spring.out.log') `
        -RedirectStandardError (Join-Path $logDirectory 'spring.err.log') `
        -WindowStyle Hidden -PassThru
    $services += [pscustomobject]@{ Name = 'Spring Boot'; Id = $spring.Id }
}

if (-not (Test-LocalPort -Port 5173)) {
    $vue = Start-Process -FilePath (Get-Command npm).Source `
        -ArgumentList @('run', 'dev', '--', '--host', '127.0.0.1') `
        -WorkingDirectory (Join-Path $projectRoot 'src\frontend') `
        -RedirectStandardOutput (Join-Path $logDirectory 'vue.out.log') `
        -RedirectStandardError (Join-Path $logDirectory 'vue.err.log') `
        -WindowStyle Hidden -PassThru
    $services += [pscustomobject]@{ Name = 'Vue'; Id = $vue.Id }
}

$services | ConvertTo-Json | Set-Content -Path $pidFile -Encoding utf8

Wait-LocalPort -Port 8000 -Name 'Django'
Wait-LocalPort -Port 8080 -Name 'Spring Boot'
Wait-LocalPort -Port 5173 -Name 'Vue'

Write-Host ''
Write-Host 'All services are running:'
Write-Host '  Frontend:    http://127.0.0.1:5173'
Write-Host '  Django API:  http://127.0.0.1:8000/api/'
Write-Host '  Spring API:  http://127.0.0.1:8080/api/'
Write-Host "  Logs:        $logDirectory"

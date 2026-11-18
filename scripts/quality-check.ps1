
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "Python virtual environment not found: $Python"
}

function Invoke-QualityCheck {
    param(
        [string]$Name,
        [string]$Module,
        [string[]]$Arguments
    )

    Write-Host "`n=== $Name ===" -ForegroundColor Cyan

    & $Python -m $Module @Arguments

    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }

    Write-Host "$Name passed." -ForegroundColor Green
}

Push-Location $ProjectRoot

try {
    Invoke-QualityCheck "Black" "black" @("--check", ".")
    Invoke-QualityCheck "isort" "isort" @("--check-only", ".")
    Invoke-QualityCheck "Flake8" "flake8" @(".")
    Invoke-QualityCheck "Tests" "pytest" @("-q")

    Write-Host "`nAll quality checks passed." -ForegroundColor Green
}
finally {
    Pop-Location
}

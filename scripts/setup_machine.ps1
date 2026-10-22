<#
.SYNOPSIS
    One-command bootstrap of a fresh hoops-lab clone on Windows (safe to re-run).

.DESCRIPTION
    1. Checks git and git-lfs and installs the LFS hooks (the pre-push hook uploads the
       parquet on every data push).
    2. git lfs pull: every season's parquet arrives in data\processed, so nothing historical
       is ever re-downloaded from stats.nba.com.
    3. Verifies the parquet are real files, not ~130-byte LFS pointer stubs (on a
       TLS-inspecting corporate proxy, prints the CA-bundle fix and stops).
    4. Creates .venv with Python 3.11+ if missing; installs requirements.txt plus the dev
       tools (pytest, ruff) from pyproject.toml.
    5. Builds the local DuckDB (python -m hoops_lab.storage.seed).
    With -ScheduleRefresh it then registers the weekly refresh on THIS PC
    (scripts\schedule_refresh.ps1 - keep it active on one PC at a time).

.PARAMETER ScheduleRefresh
    Also register the weekly refresh task (defaults: Monday 09:00).

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\setup_machine.ps1 -ScheduleRefresh
#>
[CmdletBinding()]
param([switch]$ScheduleRefresh)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Write-Step([string]$Message) { Write-Host "==> $Message" -ForegroundColor Cyan }
function Stop-Setup([string]$Message) { Write-Host "ERROR: $Message" -ForegroundColor Red; exit 1 }

Write-Step 'Checking git and git-lfs'
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Stop-Setup 'git not found: install Git for Windows (https://git-scm.com), then re-run.'
}
git lfs version
if ($LASTEXITCODE -ne 0) { Stop-Setup 'git-lfs not found: winget install GitHub.GitLFS, then re-run.' }
git lfs install
if ($LASTEXITCODE -ne 0) { Stop-Setup 'git lfs install failed - see the output above.' }

Write-Step 'Fetching the versioned data (git lfs pull)'
git lfs pull
$pulled = $LASTEXITCODE -eq 0
$parquet = @(Get-ChildItem 'data\processed\*.parquet' -ErrorAction SilentlyContinue)
$stubs = @($parquet | Where-Object { $_.Length -lt 1024 })  # LFS pointers are ~130 bytes
if (-not $parquet -or $stubs) {
    Write-Host "ERROR: data\processed has $($stubs.Count) LFS pointer stubs of $($parquet.Count) parquet." -ForegroundColor Red
    Write-Host @'
git-lfs could not download the real files. Behind a TLS-inspecting corporate proxy git-lfs
(a Go binary) does not trust the proxy CA even though Windows does. Export the Windows trust
store to a PEM bundle and point git at it - certificate verification stays ON:

  $pem = "$HOME\.certs\windows-ca-bundle.pem"
  New-Item -ItemType Directory -Force (Split-Path $pem) | Out-Null
  Get-ChildItem Cert:\LocalMachine\Root, Cert:\CurrentUser\Root, Cert:\LocalMachine\CA, Cert:\CurrentUser\CA |
    ForEach-Object { "-----BEGIN CERTIFICATE-----`n" + [Convert]::ToBase64String($_.RawData, 'InsertLineBreaks') + "`n-----END CERTIFICATE-----" } |
    Set-Content -Encoding ascii $pem
  git config --global http.sslCAInfo ($pem -replace '\\', '/')

Then re-run this script. Never set http.sslVerify=false.
'@
    exit 1
}
if (-not $pulled) { Write-Warning 'git lfs pull failed, but every parquet is already real - continuing.' }
Write-Host "$($parquet.Count) parquet files in data\processed"

Write-Step 'Python virtual environment (.venv, Python 3.11+)'
$python = Join-Path $Root '.venv\Scripts\python.exe'
$versionCheck = 'import sys; sys.exit(sys.version_info < (3, 11))'
if (-not (Test-Path $python)) {
    foreach ($base in @(@{ Exe = 'py'; Args = @('-3') }, @{ Exe = 'python'; Args = @() })) {
        if (-not (Get-Command $base.Exe -ErrorAction SilentlyContinue)) { continue }
        $baseArgs = $base.Args
        & $base.Exe @baseArgs -c $versionCheck  # the Microsoft Store "python" alias fails here
        if ($LASTEXITCODE -ne 0) { continue }
        & $base.Exe @baseArgs -m venv .venv
        if ($LASTEXITCODE -eq 0) { break }
    }
    if (-not (Test-Path $python)) {
        Stop-Setup 'No Python 3.11+ found: winget install Python.Python.3.13, then re-run.'
    }
}
& $python -c $versionCheck
if ($LASTEXITCODE -ne 0) { Stop-Setup '.venv runs Python < 3.11: delete the .venv folder and re-run.' }

Write-Step 'Installing dependencies (requirements.txt + dev tools)'
& $python -m pip install --disable-pip-version-check -r requirements.txt -e '.[dev]'
if ($LASTEXITCODE -ne 0) {
    Stop-Setup 'pip install failed. Behind a TLS proxy: .venv\Scripts\python.exe -m pip config set global.cert <CA bundle .pem>'
}

Write-Step 'Building the local DuckDB from data\processed'
& $python -m hoops_lab.storage.seed
if ($LASTEXITCODE -ne 0) {
    Stop-Setup 'Database build failed. Is the dashboard running? It locks data\db\hoops_lab.duckdb.'
}

if ($ScheduleRefresh) {
    Write-Step 'Scheduling the weekly refresh on this PC'
    & (Join-Path $PSScriptRoot 'schedule_refresh.ps1')
}

Write-Host ''
Write-Host 'Setup complete. Next steps:' -ForegroundColor Green
Write-Host '  .venv\Scripts\python.exe -m streamlit run dashboard/app.py   # local dashboard'
Write-Host '  .venv\Scripts\python.exe -m pytest tests -q                  # full test suite'
Write-Host '  git push --dry-run      # once: Git Credential Manager stores your GitHub login'
if (-not $ScheduleRefresh) {
    Write-Host '  scripts\schedule_refresh.ps1   # weekly refresh on THIS PC (-Unregister it on the old one)'
}

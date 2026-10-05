<#
.SYNOPSIS
  One-shot Windows setup for the SailPoint Navigate Hack Day MCP server.

.DESCRIPTION
  1. Finds Python 3.10+ (py launcher first, then python)
  2. Creates .venv and installs requirements
  3. Stores the PAT in Windows Credential Manager (hidden prompt)
  4. Writes .mcp.json + mcp-inspector.json with absolute paths (UTF-8, no BOM)
  5. Runs the self-test (token + search_identities "Adam Kennedy")

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\setup.ps1
  powershell -ExecutionPolicy Bypass -File .\setup.ps1 -SkipCredentials
#>
param(
    [switch]$SkipCredentials
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot
$Root = (Get-Location).Path

function Write-Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }

# --- 1. Python ----------------------------------------------------------------
Write-Step "Locating Python 3.10+"
$PyExe = $null; $PyArgs = @()
$candidates = @(
    @{ Exe = "py";     Args = @("-3") },   # Python launcher (preferred)
    @{ Exe = "python"; Args = @() }        # PATH python (skips the Microsoft Store stub, which fails the version check)
)
foreach ($c in $candidates) {
    try {
        $ver = & $c.Exe @($c.Args) -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null
        if ($LASTEXITCODE -eq 0 -and $ver -and ([version]$ver -ge [version]"3.10")) {
            $PyExe = $c.Exe; $PyArgs = $c.Args; break
        }
    } catch { }
}
if (-not $PyExe) {
    throw "Python 3.10+ not found. Install from https://www.python.org/downloads/ (tick 'Add to PATH'), then re-run."
}
Write-Host "Using: $PyExe $($PyArgs -join ' ') (Python $ver)"

# --- 2. venv + deps ------------------------------------------------------------
Write-Step "Creating .venv and installing requirements"
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    & $PyExe @($PyArgs) -m venv .venv
}
$VenvPy = Join-Path $Root ".venv\Scripts\python.exe"
& $VenvPy -m pip install --quiet --upgrade pip
& $VenvPy -m pip install --quiet -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "pip install failed." }

# --- 3. Credentials ------------------------------------------------------------
if (-not $SkipCredentials) {
    Write-Step "Storing PAT in Windows Credential Manager (input is hidden)"
    & $VenvPy store_credentials.py
    if ($LASTEXITCODE -ne 0) { throw "Credential storage failed." }
} else {
    & $VenvPy store_credentials.py --check
}

# --- 4. MCP client configs -----------------------------------------------------
Write-Step "Writing .mcp.json and mcp-inspector.json"
$config = @{
    mcpServers = @{
        "sailpoint-hackday" = @{
            command = $VenvPy
            args    = @((Join-Path $Root "server.py"))
        }
    }
} | ConvertTo-Json -Depth 5
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText((Join-Path $Root ".mcp.json"), $config, $utf8NoBom)
[System.IO.File]::WriteAllText((Join-Path $Root "mcp-inspector.json"), $config, $utf8NoBom)

# --- 5. Self-test --------------------------------------------------------------
Write-Step "Self-test (token + search_identities 'Adam Kennedy')"
& $VenvPy server.py --selftest

Write-Host "`nDone. Launch MCP Inspector with:" -ForegroundColor Green
Write-Host "  npx @modelcontextprotocol/inspector@latest --config mcp-inspector.json --server sailpoint-hackday"

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet("runner", "gate")]
    [string]$Mode,

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ForwardedArgs
)

$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..\..")).Path
$pythonHome = "C:\Users\Public\LibreOfficePortable\program\python-core-3.12.13"
$pythonExe = Join-Path $pythonHome "bin\python.exe"
$pythonLauncher = Join-Path $PSScriptRoot "run_frozen_python.py"
$programRoot = Split-Path -Parent $pythonHome

if (-not (Test-Path -LiteralPath $pythonExe -PathType Leaf)) {
    throw "Pinned bundled Python is missing: $pythonExe"
}
if (-not (Test-Path -LiteralPath $pythonLauncher -PathType Leaf)) {
    throw "Tracked Python launcher is missing: $pythonLauncher"
}

$env:PATH = "$programRoot;$(Join-Path $pythonHome 'bin');$env:PATH"
$env:PYTHONHOME = $pythonHome
$env:PYTHONDONTWRITEBYTECODE = "1"
$env:PYTHONNOUSERSITE = "1"
Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
Remove-Item Env:PYTHONSTARTUP -ErrorAction SilentlyContinue
Remove-Item Env:PYTHONINSPECT -ErrorAction SilentlyContinue
Remove-Item Env:PYTHONUSERBASE -ErrorAction SilentlyContinue

Push-Location -LiteralPath $projectRoot
try {
    & $pythonExe $pythonLauncher $projectRoot $Mode @ForwardedArgs
    $exitCode = $LASTEXITCODE
}
finally {
    Pop-Location
}
exit $exitCode

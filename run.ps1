# Lance le pipeline SOS-JOB complet : scrape -> filtre -> TUI -> génère les CV.
# Usage : .\run.ps1   (depuis la racine du repo)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONUTF8 = "1"

$miktexBin = "$env:LOCALAPPDATA\Programs\MiKTeX\miktex\bin\x64"
if (($env:PATH -split ";") -notcontains $miktexBin) {
    $env:PATH = "$env:PATH;$miktexBin"
}

& "$root\.venv\Scripts\python.exe" "$root\run.py"

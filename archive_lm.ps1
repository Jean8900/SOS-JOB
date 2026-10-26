# Archive toutes les LM generees (output/LM/tex + pdf) -> output/LM/archive/.
# Ecrase l'archive existante si une LM du meme nom y est deja.
# Usage : .\archive_lm.ps1

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONUTF8 = "1"

& "$root\.venv\Scripts\python.exe" "$root\archive_lm.py"

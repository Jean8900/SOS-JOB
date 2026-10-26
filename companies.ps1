# Scrape WTJ pour un metier et ouvre directement le HTML rendu dans le navigateur.
# Usage : .\companies.ps1                  (utilise le 1er metier de config/criteria.yaml)
#         .\companies.ps1 "AI Engineer"    (metier au choix)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONUTF8 = "1"

& "$root\.venv\Scripts\python.exe" "$root\list_companies.py" @args

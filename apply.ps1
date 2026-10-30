# Copilot de candidature : parcourt les offres générées par .\run.ps1
# (navigateur à gauche, dossier d'upload en haut à droite, ce terminal en bas à droite).
# Usage : .\apply.ps1               (depuis la racine du repo)
# Raccourcis globaux : Ctrl+Alt+Droite = candidaté, Ctrl+Alt+Gauche = précédente,
#                      Ctrl+Alt+S = passer, Ctrl+Alt+Q = quitter

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONUTF8 = "1"

& "$root\.venv\Scripts\python.exe" "$root\apply.py" @args

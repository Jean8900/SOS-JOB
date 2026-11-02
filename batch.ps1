# Lot de candidatures dans TON Chrome : une offre par onglet, remplissage (champs, CV, LM) jusqu'avant l'envoi.
# Jamais de clic sur « J'envoie ma candidature ! » : tu envoies toi-même. Le programme local doit tourner (.\fill.ps1 install).
# Usage : .\batch.ps1 --lot -n 10    (offres préparées par wtj_prepare.py : CV et LM générés)
#         .\batch.ps1 -n 10          (offres en attente de apply.ps1, tous sites)
# Préparer un lot WTJ : .\batch.ps1 prepare "technicien de maintenance" -n 10

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONUTF8 = "1"

if ($args.Count -gt 0 -and $args[0] -eq "prepare") {
    & "$root\.venv\Scripts\python.exe" "$root\wtj_prepare.py" @($args | Select-Object -Skip 1)
} else {
    & "$root\.venv\Scripts\python.exe" "$root\batch.py" @args
}

# Génère et ouvre le suivi des candidatures (output/suivi.xlsx).
# Usage : .\suivi.ps1   (depuis la racine du repo)
# Colonne Notes : écris ce que tu veux, elle est conservée à chaque régénération.
# Ferme le fichier dans Excel avant de relancer la commande.

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONUTF8 = "1"

& "$root\.venv\Scripts\python.exe" "$root\suivi.py" @args

# Démo filmée + test de non-régression : alertes email, offres WTJ « Software Engineer », CV/LM, remplissage
# de 3 offres jusqu'avant l'envoi (jamais cliqué), diaporama des onglets, verdict. Vidéo et rapport : output\demo\<date>\.
# Prérequis : .\login.ps1 fait (sites connectés dans Chrome), programme local lancé (.\fill.ps1 install).
# Usage : .\demo.ps1                 (démo filmée)
#         .\demo.ps1 --no-video      (TNR seul ; code de sortie 0 = vert)
#         .\demo.ps1 -n 3 --query "Software Engineer"

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONUTF8 = "1"

& "$root\.venv\Scripts\python.exe" "$root\demo.py" @args
exit $LASTEXITCODE

# Tournée de connexion : ouvre un à un, dans ton Chrome, les sites de input\login_sites.yaml
# pour que tu t'y connectes une fois (session gardée ensuite par Chrome). Aucun identifiant ne passe par le code.
# Usage : .\login.ps1             (sites pas encore connectés)
#         .\login.ps1 --all       (repasser sur tous les sites)
#         .\login.ps1 --list      (état de chaque site)
# Raccourcis : Ctrl+Alt+Droite = connecté, Ctrl+Alt+S = passer, Ctrl+Alt+Gauche = précédent, Ctrl+Alt+Q = quitter

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONUTF8 = "1"

& "$root\.venv\Scripts\python.exe" "$root\login.py" @args

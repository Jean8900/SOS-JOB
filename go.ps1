# Candidature de bout en bout depuis un formulaire : critères, sites, nb d'offres -> connexion -> CV/LM + remplissage.
# Rien n'est envoyé : tu relis et tu cliques toi-même sur l'envoi de chaque onglet.
# Usage : .\go.ps1 [--record]   puis dans VS Code : Ctrl+Shift+P > « Simple Browser: Show » > Ctrl+V (adresse copiée) > Entrée

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONUTF8 = "1"

$miktexBin = "$env:LOCALAPPDATA\Programs\MiKTeX\miktex\bin\x64"
if (($env:PATH -split ";") -notcontains $miktexBin) {
    $env:PATH = "$env:PATH;$miktexBin"
}

& "$root\.venv\Scripts\python.exe" "$root\go.py" @args

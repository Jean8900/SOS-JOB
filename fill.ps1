# Pré-remplissage des formulaires dans Chrome / Edge : Ctrl+Alt+Espace (voir extension/README.md).
#   .\fill.ps1             lance le programme local au premier plan (Ctrl+C pour arrêter)
#   .\fill.ps1 install     le lance maintenant ET à chaque ouverture de session Windows (arrière-plan, sans fenêtre)
#   .\fill.ps1 uninstall   retire le démarrage automatique et arrête le programme
#   .\fill.ps1 status      dit s'il tourne et s'il est lancé au démarrage
param([string]$Action = "run")

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$python = "$root\.venv\Scripts\python.exe"
$pythonw = "$root\.venv\Scripts\pythonw.exe"
$link = Join-Path ([Environment]::GetFolderPath('Startup')) "SOS-JOB-fill.lnk"

function Get-FillProcess {
    Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -and $_.CommandLine -like '*fill.py*' }
}

switch ($Action) {
    "install" {
        $shell = New-Object -ComObject WScript.Shell
        $shortcut = $shell.CreateShortcut($link)
        $shortcut.TargetPath = $pythonw
        $shortcut.Arguments = "`"$root\fill.py`""
        $shortcut.WorkingDirectory = $root
        $shortcut.WindowStyle = 7
        $shortcut.Description = "SOS-JOB : pré-remplissage des formulaires (Ctrl+Alt+Espace)"
        $shortcut.Save()
        if (-not (Get-FillProcess)) { Start-Process -FilePath $pythonw -ArgumentList "`"$root\fill.py`"" -WorkingDirectory $root -WindowStyle Hidden }
        Write-Host "Démarrage automatique installé ($link). Programme lancé en arrière-plan (journal : output\copilot\fill.log)."
    }
    "uninstall" {
        Remove-Item $link -ErrorAction SilentlyContinue
        Get-FillProcess | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
        Write-Host "Démarrage automatique retiré, programme arrêté."
    }
    "status" {
        Write-Host ("En cours d'exécution : " + [bool](Get-FillProcess))
        Write-Host ("Lancé au démarrage de Windows : " + (Test-Path $link))
    }
    default {
        [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
        $OutputEncoding = [System.Text.Encoding]::UTF8
        $env:PYTHONUTF8 = "1"
        & $python "$root\fill.py" @args
    }
}

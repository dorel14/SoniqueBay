@echo off
echo Exécution du hook pre-commit...
"C:\Users\david\Documents\devs\SoniqueBay-app\.venv\Scripts\python.exe" "%~dp0..\scripts\version_updater.py"
IF %ERRORLEVEL% NEQ 0 (
    echo Erreur lors de la mise à jour de la version
    exit /b 1
)
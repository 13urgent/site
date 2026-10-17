@echo off
cd /d "%~dp0"
echo 13 URGENT - Serveur de developpement local
echo Gardez cette fenetre ouverte. Dans votre navigateur, saisissez http://127.0.0.1:8000
echo Pour arreter le serveur : Ctrl+C.
where python >nul 2>nul
if errorlevel 1 (
  echo Python n'est pas disponible dans PATH. Installez Python depuis python.org, puis relancez ce fichier.
  pause
  exit /b 1
)
python -m http.server 8000 --bind 127.0.0.1
pause

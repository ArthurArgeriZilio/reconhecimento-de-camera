@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM Ensures we run from the repo folder even when started via double click
cd /d "%~dp0"

chcp 65001 >nul
title DEMI - Modulo Inteligente 4.0

echo.
echo  ==================================================
echo   DEMI - Modulo Inteligente 4.0
echo   Monitoramento de Seguranca Industrial
echo   Equipe: Data Stick
echo  ==================================================
echo.
echo  [1/4] Verificando Python...
where python >nul 2>&1
if errorlevel 1 (
  where py >nul 2>&1
  if errorlevel 1 (
    echo.
    echo  [ERRO] Python nao encontrado no PATH.
    echo  - Instale o Python em: https://www.python.org/downloads/
    echo  - Durante a instalacao marque: "Add Python to PATH"
    echo.
    pause
    exit /b 1
  ) else (
    set "PY=py"
  )
) else (
  set "PY=python"
)

%PY% --version
echo  [OK] Python encontrado.

echo.
echo  [2/4] Verificando dependencias...
%PY% -m pip install --upgrade pip >nul 2>&1
%PY% -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo  [AVISO] Algumas dependencias podem nao ter sido instaladas corretamente.
  echo  Se der erro, tente rodar este .bat como Administrador.
)
echo  [OK] Dependencias prontas.

echo.
echo  [3/4] Iniciando dashboard (http://localhost:5000)...
start "DEMI-Dashboard" /min cmd /c "%PY% dashboard.py"
echo  [OK] Dashboard iniciando em background...
echo  Aguardando Flask inicializar...
timeout /t 3 /nobreak >nul

echo  Abrindo navegador...
start "" "http://localhost:5000"

echo.
echo  [4/4] Iniciando camera DEMI...
echo.
echo  ----------------------------------------------
echo   Controles:
echo    Q  = Sair
echo    R  = Iniciar gravacao de video
echo    S  = Screenshot
echo    E  = Exportar dados CSV
echo    H  = Ocultar/Mostrar HUD
echo  ----------------------------------------------
echo.

%PY% demi.py

echo.
echo  [INFO] Encerrando dashboard...
taskkill /f /fi "WINDOWTITLE eq DEMI-Dashboard*" >nul 2>&1

echo.
echo  ==================================================
echo   DEMI encerrado. Ate logo!
echo  ==================================================
echo.
pause

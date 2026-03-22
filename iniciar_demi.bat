@echo off
chcp 65001 >nul
title DEMI - Modulo Inteligente 4.0

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║     DEMI - Modulo Inteligente 4.0        ║
echo  ║   Monitoramento de Seguranca Industrial  ║
echo  ║          Equipe: Data Stick              ║
echo  ╚══════════════════════════════════════════╝
echo.

echo  [1/4] Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [ERRO] Python nao encontrado!
    echo  Instale o Python em: https://www.python.org/downloads/
    echo  Marque a opcao "Add Python to PATH" durante a instalacao.
    echo.
    pause
    exit /b 1
)
echo  [OK] Python encontrado.

echo.
echo  [2/4] Verificando dependencias...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo  [AVISO] Alguns pacotes podem nao ter sido instalados corretamente.
)
echo  [OK] Dependencias prontas.

echo.
echo  [3/4] Iniciando dashboard (http://localhost:5000)...
start "DEMI-Dashboard" /min python dashboard.py
echo  [OK] Dashboard iniciando em background...
echo  Aguardando Flask inicializar...
timeout /t 3 /nobreak >nul

echo  Abrindo navegador...
start http://localhost:5000

echo.
echo  [4/4] Iniciando camera DEMI...
echo.
echo  ┌─────────────────────────────────────────┐
echo  │  Controles:                             │
echo  │   Q  = Sair                             │
echo  │   R  = Iniciar gravacao de video        │
echo  │   S  = Screenshot                       │
echo  │   E  = Exportar dados CSV               │
echo  │   H  = Ocultar/Mostrar HUD              │
echo  └─────────────────────────────────────────┘
echo.
python demi.py

echo.
echo  [INFO] Encerrando dashboard...
taskkill /f /fi "WINDOWTITLE eq DEMI-Dashboard*" >nul 2>&1

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║         DEMI encerrado. Ate logo!        ║
echo  ╚══════════════════════════════════════════╝
echo.
pause

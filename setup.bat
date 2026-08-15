@echo off
title Instalador e Configurador - Hand Gesture Controller
echo ==========================================================
echo   Configurando o Hand Gesture Controller na nova maquina
echo ==========================================================

:: 1. Verificar se Python esta instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao foi encontrado no PATH do sistema!
    echo Por favor, instale o Python 3.10, 3.11 ou 3.12 pelo site oficial:
    echo https://www.python.org/downloads/
    echo IMPORTANTE: Marque a opcao "Add python.exe to PATH" durante a instalacao.
    pause
    exit /b 1
)

echo [1/3] Python detectado com sucesso!

:: 2. Criar ambiente virtual (.venv) se nao existir
if not exist .venv (
    echo [2/3] Criando ambiente virtual (.venv)...
    python -m venv .venv
) else (
    echo [2/3] Ambiente virtual ja existe.
)

:: 3. Instalar dependencias
echo [3/3] Instalando bibliotecas necessarias do requirements.txt...
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt

echo ==========================================================
echo   Instalacao concluida com sucesso!
echo   Para iniciar, execute o arquivo run.bat ou digite:
echo   .venv\Scripts\python.exe main.py
echo ==========================================================
pause

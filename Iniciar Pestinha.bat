@echo off
rem Abre o Pestinha pelo codigo-fonte. Na primeira vez instala as dependencias.
cd /d "%~dp0"

set "PY="
where py >nul 2>nul && set "PY=py" && set "PYW=pyw"
if not defined PY where python >nul 2>nul && set "PY=python" && set "PYW=pythonw"
if not defined PY (
  echo Python nao encontrado. Instale o Python 3.11 ou mais novo em python.org
  echo e marque a opcao "Add python.exe to PATH" na instalacao.
  pause
  exit /b 1
)

if not exist ".dependencias_ok" (
  echo Instalando as dependencias, so na primeira vez...
  %PY% -m pip install -r requirements.txt
  if errorlevel 1 (
    echo Nao deu para instalar as dependencias.
    pause
    exit /b 1
  )
  echo ok> ".dependencias_ok"
)

start "" %PYW% main.py

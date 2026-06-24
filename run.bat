@echo off
chcp 65001 >nul
title Выгрузка сообщений Telegram
cd /d "%~dp0"

echo ============================================
echo   Выгрузка сообщений Telegram
echo ============================================
echo.

rem --- Ищем рабочий Python: сначала py-лаунчер, потом python/python3 ---
set "PY="
py -3 --version >nul 2>&1 && set "PY=py -3"
if not defined PY (
  python --version >nul 2>&1 && set "PY=python"
)
if not defined PY (
  python3 --version >nul 2>&1 && set "PY=python3"
)

if not defined PY (
  echo [!] Python не найден.
  echo.
  echo     1. Скачай Python с https://www.python.org/downloads/
  echo     2. При установке ОБЯЗАТЕЛЬНО поставь галочку "Add Python to PATH".
  echo     3. После установки закрой это окно и запусти run.bat заново.
  echo.
  echo     Если "python" открывает Microsoft Store — значит Python не установлен,
  echo     ставь именно с сайта python.org по ссылке выше.
  echo.
  pause
  exit /b
)

echo Использую: %PY%
%PY% --version
echo.

echo Устанавливаю зависимости (один раз, нужен интернет)...
%PY% -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo [!] Не удалось установить зависимости.
  echo     Проверь интернет / антивирус / прокси и запусти заново.
  echo.
  pause
  exit /b
)

echo.
echo Открываю страницу в браузере...
start "" http://127.0.0.1:5000

echo.
echo Сервер запущен. НЕ ЗАКРЫВАЙ это окно, пока работаешь.
echo Чтобы остановить — закрой это окно.
echo.
%PY% app.py

echo.
echo ============================================
echo [!] Сервер остановился.
echo     Если выше есть текст ошибки (красный/Traceback) —
echo     сделай скриншот этого окна и пришли его.
echo     Частая причина: порт 5000 занят другой программой.
echo ============================================
echo.
pause

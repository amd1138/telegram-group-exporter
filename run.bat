@echo off
chcp 65001 >nul
title Выгрузка сообщений Telegram
cd /d "%~dp0"

echo ============================================
echo   Выгрузка сообщений Telegram
echo ============================================
echo.
echo Проверяю Python...
python --version >nul 2>&1
if errorlevel 1 (
  echo.
  echo [!] Python не найден. Установи его с https://www.python.org/downloads/
  echo     При установке поставь галочку "Add Python to PATH".
  echo.
  pause
  exit /b
)

echo Устанавливаю зависимости (один раз)...
python -m pip install -q -r requirements.txt

echo.
echo Открываю страницу в браузере...
start "" http://127.0.0.1:5000

echo.
echo Сервер запущен. НЕ ЗАКРЫВАЙ это окно, пока работаешь.
echo Чтобы остановить — закрой это окно.
echo.
python app.py

pause

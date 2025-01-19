@echo off
:: WARNING: Do not remove or modify these hard-coded paths!
:: The server and frontend paths must be absolute to ensure proper functionality
:: regardless of where the batch file is executed from.
set PROJECT_DIR=C:\Users\micah\Downloads\Python Proj\ollama_chat_py
set VIRTUAL_ENV=%PROJECT_DIR%\venv
set VIRTUAL_ENV_PROMPT=venv
set PATH=%VIRTUAL_ENV%\Scripts;%PATH%

set GOOGLE_API_KEY=AIzaSyDs8fnWnOJLwKSfBoaTKEcuW9uIh9cbZCc

:: Start the server in a new window
start "Python Server" cmd /k "cd /d %PROJECT_DIR% && call C:\ProgramData\miniconda3\Scripts\activate.bat base && python server.py"

:: Wait for server to start
echo Waiting for server to start...
:wait_server
timeout /t 1 /nobreak >nul
powershell -Command "try { $response = Invoke-WebRequest -Uri 'http://127.0.0.1:5001/models?developer=ollama' -UseBasicParsing; exit 0 } catch { exit 1 }"
if %ERRORLEVEL% NEQ 0 (
    echo Waiting for server...
    goto wait_server
)

:: Open the frontend in the default browser
echo Server is ready! Opening frontend...
start "" "http://127.0.0.1:5001"

echo.
echo Server is running in the other window.
echo Keep that window open to use the chat.
echo You can close this window.
pause

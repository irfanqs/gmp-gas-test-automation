@echo off
setlocal
cd /d "%~dp0"

if not exist ".env" type nul > ".env"
findstr /b /r /c:"ANTHROPIC_API_KEY=[^ ]" ".env" >nul 2>&1
if errorlevel 1 call :configure_anthropic_key

if not exist .venv python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
start http://127.0.0.1:5005
.venv\Scripts\python app.py
exit /b

:configure_anthropic_key
set "ANTHROPIC_API_KEY="
set /p "ANTHROPIC_API_KEY=Enter your Anthropic API key: "
if not defined ANTHROPIC_API_KEY (
  echo API key cannot be empty.
  goto configure_anthropic_key
)
>>".env" echo ANTHROPIC_API_KEY=%ANTHROPIC_API_KEY%
echo Anthropic API key saved to .env.
exit /b

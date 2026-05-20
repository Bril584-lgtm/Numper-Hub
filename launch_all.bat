@echo off
cd /d "%~dp0"
if exist .env (
    for /f "tokens=1,2 delims==" %%a in (.env) do set %%a=%%b
)
python launch_all.py
pause

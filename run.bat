@echo off
cd /d "%~dp0"

start "Django Server" "%USERPROFILE%\.venv\Scripts\python.exe" manage.py runserver
start "ngrok Tunnel" .\ngrok.exe http 8000

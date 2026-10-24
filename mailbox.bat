@echo off
cd /d "%~dp0"
.venv\Scripts\python mailbox.py %*
pause

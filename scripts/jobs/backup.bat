@echo off
rem Daily SQLite backup (WL-030): backups\YYYY-MM-DD.db at the repo root.
rem Started by Task Scheduler (see register.ps1); also fine to run by hand.
rem Paths come from this file's own folder, so PATH and the start folder do not matter.
setlocal
cd /d "%~dp0..\..\backend" || exit /b 1
".venv\Scripts\python.exe" -m app.jobs backup
exit /b %ERRORLEVEL%

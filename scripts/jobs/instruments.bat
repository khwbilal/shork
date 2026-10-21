@echo off
rem Daily instrument catalogue refresh (WL-044): Binance spot and USD-M, with names.
rem Started by Task Scheduler (see register.ps1); also fine to run by hand.
rem Paths come from this file's own folder, so PATH and the start folder do not matter.
setlocal
cd /d "%~dp0..\..\backend" || exit /b 1
".venv\Scripts\python.exe" -m app.jobs instruments
exit /b %ERRORLEVEL%

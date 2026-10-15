@echo off
cd /d "%~dp0.."
if not "%~1"=="" goto cli
start "" pythonw -B "%~dp0..\src\campaign_launcher.py"
exit /b
:cli
python -B "%~dp0..\src\launch_old_native_menu.py" %*
if errorlevel 1 pause

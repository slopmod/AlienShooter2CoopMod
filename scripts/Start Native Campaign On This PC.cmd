@echo off
cd /d "%~dp0.."
python -B "%~dp0..\src\launch_old_native_menu.py" --two-windows %*
pause

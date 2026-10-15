@echo off
cd /d "%~dp0"
python -B "%~dp0launch_old_native_menu.py" --two-windows %*
pause

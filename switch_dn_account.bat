@echo off
:: Switch to the script directory
cd /d "%~dp0"

echo Current Work Dir: %cd%

:: Run the python script
:: Make sure the path below matches your actual python.exe location
"D:\Anaconda\envs\dnplayer\python.exe" main_controller.py

:: Pause to keep window open
pause

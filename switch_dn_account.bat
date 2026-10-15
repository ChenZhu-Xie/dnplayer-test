@echo off
chcp 65001 >nul
cd /d "%~dp0"

:: Kill previous instance window and process tree
title LDPlayer_Account_Switcher_Starting
taskkill /F /FI "WINDOWTITLE eq LDPlayer_Account_Switcher" /T >nul 2>nul
title LDPlayer_Account_Switcher

echo ==================================================
echo [BATCH] LDPlayer Account Switcher Launcher
echo [BATCH] Current Directory: %cd%
echo ==================================================
echo [BATCH] Checking and cleaning previous instances...
echo [BATCH] Looking for Python environment...

:: Search for Python
set "PY_EXE="
if exist "D:\Anaconda\envs\dnplayer\python.exe" (
    set "PY_EXE=D:\Anaconda\envs\dnplayer\python.exe"
    goto :found
)

where python >nul 2>nul
if %errorlevel% equ 0 (
    set "PY_EXE=python"
    goto :found
)

echo.
echo [BATCH_ERROR] Python environment not found!
echo.
pause
exit /b 1

:found
echo [BATCH] Found Python: %PY_EXE%
echo [BATCH] Starting main_controller.py ...
echo.

"%PY_EXE%" main_controller.py
@set "EXIT_CODE=%errorlevel%"
@echo off

@echo.
@echo ==================================================
@echo [BATCH] Python process finished with code: %EXIT_CODE%
@if %EXIT_CODE% equ 0 (
    echo [BATCH_DONE] Account switch completed successfully!
) else if %EXIT_CODE% equ 1 (
    echo [BATCH_FAILED] Failed. Please check bot_run.log.
) else if %EXIT_CODE% equ 2 (
    echo [BATCH_INTERRUPTED] User interrupted.
) else if %EXIT_CODE% equ 3 (
    echo [BATCH_ERROR] Exception occurred. Please check bot_run.log.
) else (
    echo [BATCH_UNKNOWN] Unknown exit code: %EXIT_CODE%
)
@echo ==================================================
@echo.
@pause
@exit /b %EXIT_CODE%

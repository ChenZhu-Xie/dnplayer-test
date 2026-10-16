@echo off
chcp 65001 >nul
cd /d "%~dp0"

:: Kill previous instance terminal / process tree (supports Windows Terminal tabs & classic console)
title MuMu_Account_Switcher
powershell -NoProfile -ExecutionPolicy Bypass -Command "$myPid=(Get-CimInstance Win32_Process -Filter ('ProcessId=' + $PID)).ParentProcessId; $pidFile='%~dp0.switcher_mumu.pid'; if (Test-Path $pidFile) { $oldPid=(Get-Content $pidFile -ErrorAction SilentlyContinue | Out-String).Trim(); if ($oldPid -and $oldPid -ne \"$myPid\") { $oldP=Get-CimInstance Win32_Process -Filter ('ProcessId=' + $oldPid) -ErrorAction SilentlyContinue; if ($oldP -and ($oldP.Name -eq 'cmd.exe' -or $oldP.CommandLine -match 'switch_mumu_account')) { taskkill /F /PID $oldPid /T 2>$null } } }; Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'cmd.exe' -and $_.ProcessId -ne $myPid -and $_.CommandLine -match 'switch_mumu_account\.bat' } | ForEach-Object { taskkill /F /PID $_.ProcessId /T 2>$null }; Set-Content -Path $pidFile -Value $myPid" >nul 2>nul

echo ==================================================
echo [BATCH] MuMu Account Switcher Launcher
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
@echo [BATCH] Note: This window stays open as a log. It will be auto-closed by the next run.
@pause
@exit /b %EXIT_CODE%

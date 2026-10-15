@echo off
chcp 65001 >nul
:: Switch to the script directory
cd /d "%~dp0"

echo ==================================================
echo [BATCH] MuMu 模拟器账号切换启动器
echo [BATCH] 当前工作目录: %cd%
echo ==================================================
echo [BATCH] 正在寻找 Python 环境...

:: 定义候选 Python 路径 (用空格分隔)
set "PYTHON_CANDIDATES="D:\Anaconda\envs\dnplayer\python.exe" "python""
set PY_EXE=

for %%P in (%PYTHON_CANDIDATES%) do (
    if "%%~P"=="python" (
        where python >nul 2>nul
        if %errorlevel% equ 0 (
            set "PY_EXE=python"
            goto :found
        )
    ) else (
        if exist "%%~P" (
            set "PY_EXE=%%~P"
            goto :found
        )
    )
)

if "%PY_EXE%"=="" (
    echo.
    echo [BATCH_ERROR] 找不到有效的 Python 环境，请检查路径配置！
    echo 候选路径: %PYTHON_CANDIDATES%
    echo.
    pause
    exit /b 1
)

:found
echo [BATCH] 找到 Python 环境: %PY_EXE%
echo [BATCH] 正在启动 main_controller.py ...
echo.

:: Run the python script and capture exit code
"%PY_EXE%" main_controller.py
set EXIT_CODE=%errorlevel%

echo.
echo ==================================================
echo [BATCH] Python脚本已结束，退出码: %EXIT_CODE%

:: 根据退出码输出状态
if %EXIT_CODE% equ 0 (
    echo [BATCH_DONE] 账号切换成功！
) else if %EXIT_CODE% equ 1 (
    echo [BATCH_FAILED] 账号切换失败，请查看 bot_run.log 日志文件。
) else if %EXIT_CODE% equ 2 (
    echo [BATCH_INTERRUPTED] 用户手动中断。
) else if %EXIT_CODE% equ 3 (
    echo [BATCH_ERROR] 发生异常错误，请查看 bot_run.log 日志文件。
) else (
    echo [BATCH_UNKNOWN] 未知退出码: %EXIT_CODE%
)
echo ==================================================
echo.
pause
exit /b %EXIT_CODE%

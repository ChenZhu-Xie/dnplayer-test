@echo off
:: 设置编码为 UTF-8，防止中文输出乱码
chcp 65001

echo 正在调用 dnplayer 环境执行自动化脚本...

:: 格式："虚拟环境Python绝对路径" "Python脚本绝对路径"
:: 请将下面的路径替换为您实际的路径
"D:\Anaconda\envs\dnplayer\python.exe" "E:\MCP\OpenCode\雷电test\restart_dnplayer.py"

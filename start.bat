@echo off
chcp 65001 >nul
title Aemeath Desktop Sprite - 爱弥斯桌面精灵

echo.
echo  ╔═══════════════════════════════════════════════════════════╗
echo  ║         🐱💜 Aemeath Desktop Sprite 爱弥斯桌面精灵            ║
echo  ╚═══════════════════════════════════════════════════════════╝
echo.

:: 切换到脚本所在目录
cd /d "%~dp0"

:: 设置Python编码环境
set PYTHONIOENCODING=utf-8

:: 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python，请确保Python已安装并添加到PATH
    pause
    exit /b 1
)

echo [*] 正在检查端口占用...
:: 检查8765端口是否被占用，如果是则杀掉进程
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8765') do (
    echo [*] 发现端口8765被进程 %%a 占用，正在结束...
    taskkill /F /PID %%a >nul 2>&1
    timeout /t 1 /nobreak >nul
)

echo [*] 正在启动 Aemeath Desktop Sprite...
echo [*] 按 Ctrl+C 可以停止程序
echo.

:: 启动程序
python src/main.py

:: 如果程序异常退出，暂停显示错误
echo.
if errorlevel 1 (
    echo [错误] 程序异常退出，退出码: %errorlevel%
)
pause

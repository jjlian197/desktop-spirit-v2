@echo off
title 停止 Sherry Desktop Sprite

echo.
echo 正在停止 Sherry Desktop Sprite...
echo.

:: 查找并结束Python进程（运行src/main.py的）
tasklist /FI "IMAGENAME eq python.exe" /FO CSV 2>nul | findstr /I "main.py" >nul
if %errorlevel% equ 0 (
    for /f "tokens=2 delims=," %%a in ('tasklist /FI "IMAGENAME eq python.exe" /FO CSV ^| findstr /I "main.py"') do (
        set pid=%%a
        set pid=!pid:"=!
        echo 结束进程 PID: !pid!
        taskkill /PID !pid! /F >nul 2>&1
    )
)

:: 直接杀掉占用8765端口的进程
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8765') do (
    echo 结束占用端口8765的进程 PID: %%a
    taskkill /F /PID %%a >nul 2>&1
)

echo.
echo Sherry Desktop Sprite 已停止。
echo.
timeout /t 2 /nobreak >nul

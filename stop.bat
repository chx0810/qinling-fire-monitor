@echo off
chcp 65001 >nul
title 秦岭火情监测系统 - 停止服务
color 0C

echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║     🔥 秦岭火情监测系统 - 停止所有服务           ║
echo  ╚══════════════════════════════════════════════════╝
echo.

echo [1/2] 正在关闭后端API服务器 (端口: 8001)...
:: 查找并关闭占用8001端口的Python进程
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8001 ^| findstr LISTENING') do (
    taskkill /PID %%a /F >nul 2>&1
)
echo [√] 后端API服务器已关闭

echo.
echo [2/2] 清理相关Python进程...
:: 关闭标题包含"秦岭"的cmd窗口
taskkill /FI "WINDOWTITLE eq 秦岭火情监测*" /F >nul 2>&1
echo [√] 相关进程已清理

echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║            ✅ 所有服务已停止！                   ║
echo  ╠══════════════════════════════════════════════════╣
echo  ║  后端API:     http://localhost:8001 (已关闭)     ║
echo  ╠══════════════════════════════════════════════════╣
echo  ║  重新启动:    双击 start.bat                    ║
echo  ╚══════════════════════════════════════════════════╝
echo.
pause

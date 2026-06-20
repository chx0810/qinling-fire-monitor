@echo off
chcp 65001 >nul
title 秦岭火情监测系统 - 一键启动
color 0A

echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║     🔥 秦岭火情智能监测预警系统 v1.0 🔥         ║
echo  ║            比赛专用一键启动脚本                  ║
echo  ╚══════════════════════════════════════════════════╝
echo.

:: 获取脚本所在目录（项目根目录）
set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

:: 检查Python是否可用
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到Python环境，请先安装Python 3.8+
    pause
    exit /b 1
)

:: 创建logs目录（如果不存在）
if not exist "%PROJECT_DIR%logs" (
    mkdir "%PROJECT_DIR%logs"
    echo [√] 已创建 logs 目录
)

:: 清理旧的临时文件
del /q "%PROJECT_DIR%后端服务模块\temp_*.jpg" >nul 2>&1

echo.
echo [1/2] 正在启动后端API服务器 (端口: 8001)...
echo       请稍候，模型加载需要时间...

:: 在新窗口启动后端（使用 python -u 确保输出不缓冲）
start "秦岭火情监测-后端API" cmd /k "cd /d "%PROJECT_DIR%后端服务模块%" && echo [秦岭火情监测] 后端API正在启动... && python -u api_server.py"

:: 等待后端启动并检测就绪状态
echo       等待后端服务就绪...
set /a "retry_count=0"
:wait_backend
timeout /t 2 /nobreak >nul
set /a "retry_count+=1"

:: 使用curl检测后端是否就绪
curl -s http://localhost:8001/health >nul 2>&1
if %errorlevel% equ 0 (
    echo [√] 后端API已就绪！
    goto backend_ready
)

:: 超过60秒则继续（不阻塞）
if %retry_count% gtr 30 (
    echo [!] 后端启动时间较长，继续执行...
    goto backend_ready
)

echo       等待中... (%retry_count%/30)
goto wait_backend

:backend_ready

echo.
echo [2/2] 正在打开浏览器...

:: 等待1秒后打开浏览器
timeout /t 1 /nobreak >nul
start http://localhost:8001/dashboard
echo [√] 浏览器已打开！

echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║            ✅ 系统启动成功！                     ║
echo  ╠══════════════════════════════════════════════════╣
echo  ║  后端API:     http://localhost:8001              ║
echo  ║  监控仪表板:  http://localhost:8001/dashboard    ║
echo  ║  指挥大屏:    http://localhost:8001/dashboard-large║
echo  ║  API文档:     http://localhost:8001/docs          ║
echo  ║  系统状态:    http://localhost:8001/system-status  ║
echo  ║  健康检查:    http://localhost:8001/health         ║
echo  ╠══════════════════════════════════════════════════╣
echo  ║  关闭系统:    双击 stop.bat                      ║
echo  ╚══════════════════════════════════════════════════╝
echo.
echo  按任意键关闭此窗口（系统继续运行）...
pause >nul

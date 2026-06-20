import os
import subprocess
import time
import webbrowser
from pathlib import Path

# 获取项目根目录
project_root = Path(__file__).parent

print("Starting Qinling Fire Warning System...")
print("=" * 40)

# 1. 启动后端API
print("[1/2] Starting Backend API (port: 8001)...")
backend_dir = project_root / "后端服务模块"
if not backend_dir.exists():
    print(f"ERROR: Cannot find {backend_dir}")
    exit(1)

# 启动后端（新窗口）
backend_cmd = f'cd /d "{backend_dir}" && python api_server.py'
subprocess.Popen(f'start cmd /k "{backend_cmd}"', shell=True)

# 等待后端启动（通过健康检查轮询）
print("Waiting for backend to be ready...")
for i in range(30):
    time.sleep(2)
    try:
        import urllib.request
        resp = urllib.request.urlopen("http://localhost:8001/health", timeout=2)
        if resp.status == 200:
            print("[OK] Backend API is ready!")
            break
    except Exception:
        if i % 5 == 0:
            print(f"  Waiting... ({i+1}/30)")
else:
    print("[!] Backend startup timeout, continuing anyway...")

# 2. 打开浏览器（直接访问Flask路由，无需额外前端服务器）
print("[2/2] Opening browser...")
time.sleep(2)
webbrowser.open("http://localhost:8001/dashboard")

print("\n" + "=" * 40)
print("System Started Successfully!")
print("Backend API:    http://localhost:8001")
print("Dashboard:      http://localhost:8001/dashboard")
print("Command Center: http://localhost:8001/dashboard-large")
print("API Docs:       http://localhost:8001/docs")
print("\nPress Enter to exit...")
print("=" * 40)

# 保持脚本运行
try:
    input()
except KeyboardInterrupt:
    print("\nExiting...")

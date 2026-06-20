# ==================== 秦岭火情监测系统 - Docker构建文件 ====================
# 轻量工程化展示：证明项目具备容器化部署能力
# 比赛现场仍使用 start.bat / stop.bat 启动
# 基础镜像：python:3.11-slim（轻量级Python镜像）
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量：禁止Python缓冲、设置编码（确保中文正常显示）
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV LANG=C.UTF-8

# 安装系统依赖（opencv-python需要libgl库）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装Python依赖（利用Docker缓存层加速构建）
COPY 文档与配置/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目所有文件到容器内
COPY . /app/

# 创建日志目录（确保日志写入正常）
RUN mkdir -p /app/logs

# 设置PYTHONPATH，确保核心AI模块和后端服务模块的导入路径正确
ENV PYTHONPATH="/app:/app/核心AI模块:/app/后端服务模块"

# 设置工作目录到后端服务模块（api_server.py的相对路径依赖）
WORKDIR /app/后端服务模块

# 暴露后端API端口（与start.bat一致，使用8001端口）
EXPOSE 8001

# 启动FastAPI后端服务（与本地运行方式一致）
CMD ["python", "api_server.py"]

# 🔥 秦岭火情监测系统 - Docker 容器化部署指南

> **重要说明**：Docker 容器化仅用于展示"项目具备容器化部署能力"，**比赛现场仍使用 `start.bat` 和 `stop.bat` 启动**。

---

## 📋 目录

- [环境要求](#环境要求)
- [快速开始](#快速开始)
- [常用命令](#常用命令)
- [数据卷说明](#数据卷说明)
- [健康检查](#健康检查)
- [故障排查](#故障排查)
- [注意事项](#注意事项)

---

## 🛠 环境要求

| 依赖项 | 最低版本 | 说明 |
|--------|---------|------|
| Docker | 20.10+ | 容器运行时 |
| Docker Compose | 2.0+ | 多容器编排工具 |

---

## 🚀 快速开始

### 1. 构建镜像

```bash
# 在项目根目录执行
docker-compose build
```

### 2. 启动服务

```bash
# 前台启动（可查看实时日志）
docker-compose up

# 后台启动（生产推荐）
docker-compose up -d
```

### 3. 访问系统

| 服务 | 地址 | 说明 |
|------|------|------|
| 后端 API | http://localhost:8001 | FastAPI 后端服务 |
| API 文档 | http://localhost:8001/docs | Swagger UI 交互文档 |
| 健康检查 | http://localhost:8001/health | 系统健康状态 |
| 监控仪表板 | http://localhost:8001/dashboard | 前端监控界面 |
| 模型评估 | http://localhost:8001/evaluation | AI 模型评估指标 |

---

## 📦 常用命令

### 启动与停止

```bash
# 启动服务（后台模式）
docker-compose up -d

# 查看运行状态
docker-compose ps

# 查看实时日志
docker-compose logs -f backend

# 停止服务
docker-compose down

# 停止服务并删除数据卷（慎用！会清除持久化数据）
docker-compose down -v
```

### 镜像管理

```bash
# 仅构建镜像（不启动容器）
docker-compose build

# 强制重新构建（不使用缓存）
docker-compose build --no-cache

# 构建并启动
docker-compose up --build

# 删除项目相关镜像
docker-compose down --rmi all
```

### 调试命令

```bash
# 进入运行中的容器
docker exec -it qinling-fire-backend bash

# 查看容器日志
docker logs qinling-fire-backend

# 查看容器资源占用
docker stats qinling-fire-backend
```

---

## 💾 数据卷说明

本项目通过 Docker 数据卷实现数据持久化，确保容器重启后数据不丢失：

| 宿主机路径 | 容器路径 | 模式 | 说明 |
|-----------|---------|------|------|
| `./后端服务模块/fire_alarm.db` | `/app/后端服务模块/fire_alarm.db` | 读写 | SQLite 数据库文件，存储检测记录、告警记录等 |
| `./logs` | `/app/logs` | 读写 | 系统日志、错误日志、告警日志、训练日志 |
| `./数据与模型` | `/app/数据与模型` | 只读 | AI 模型文件和数据集（避免镜像体积过大） |

### 数据卷示意

```
秦岭火情监测系统/
├── 后端服务模块/
│   └── fire_alarm.db      ← 挂载到容器内（读写，持久化）
├── logs/
│   ├── system.log         ← 挂载到容器内（读写，持久化）
│   ├── error.log
│   ├── alert.log
│   └── training_log.csv
└── 数据与模型/
    └── models/            ← 挂载到容器内（只读，节省镜像空间）
        └── best_model.h5
```

---

## 🏥 健康检查

容器内置健康检查机制，自动监测后端服务状态：

- **检查间隔**：每 30 秒
- **超时时间**：10 秒
- **重试次数**：3 次
- **启动等待**：30 秒

```bash
# 手动执行健康检查
docker exec qinling-fire-backend python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/health')"

# 查看健康状态
docker inspect --format='{{.State.Health.Status}}' qinling-fire-backend
```

---

## 🔧 故障排查

### 问题1：构建失败 - 依赖安装超时

```bash
# 使用国内镜像源加速
docker-compose build --build-arg pip_mirror=https://pypi.tuna.tsinghua.edu.cn/simple
```

### 问题2：容器启动后立即退出

```bash
# 查看退出日志
docker logs qinling-fire-backend

# 检查端口是否被占用
netstat -ano | findstr :8001
```

### 问题3：数据库文件权限问题

```bash
# Windows 环境下，确保 fire_alarm.db 文件未被其他进程占用
# 可先关闭本地运行的 start.bat 服务
stop.bat
```

### 问题4：模型文件加载失败

```bash
# 确认模型文件存在
dir 数据与模型\models\best_model.h5

# 检查容器内挂载情况
docker exec qinling-fire-backend ls -la /app/数据与模型/models/
```

---

## ⚠️ 注意事项

1. **比赛现场请勿使用 Docker**：比赛现场仍使用 `start.bat` 启动，Docker 仅用于展示容器化能力
2. **端口冲突**：启动 Docker 前请确保 8001 端口未被本地服务占用（先执行 `stop.bat`）
3. **数据一致性**：Docker 和本地运行共享同一个 SQLite 数据库文件，不建议同时运行
4. **镜像大小**：由于包含 AI 模型依赖（TensorFlow/PyTorch），镜像较大属正常现象
5. **Windows 用户**：确保 Docker Desktop 已启动，且使用 Linux 容器模式

---

## 📊 系统架构（Docker 模式）

```
┌─────────────────────────────────────────────┐
│              Docker Container                │
│  ┌─────────────────────────────────────────┐ │
│  │        qinling-fire-backend             │ │
│  │                                         │ │
│  │  Python 3.11-slim                       │ │
│  │  ├── FastAPI (api_server.py)            │ │
│  │  ├── AI 模型 (fire_detector.py)         │ │
│  │  ├── 虚拟传感器 (sensor_integration.py) │ │
│  │  └── 风险评估器 (risk_assessor.py)      │ │
│  │                                         │ │
│  │  Port: 8001                             │ │
│  └─────────────────────────────────────────┘ │
│         ↕                                    │
│    Volumes:                                  │
│    ├── fire_alarm.db (读写)                  │
│    ├── logs/ (读写)                          │
│    └── 数据与模型/ (只读)                    │
└─────────────────────────────────────────────┘
```

---

*秦岭火情监测系统 - 工程化展示文档*

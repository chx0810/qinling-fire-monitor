# 🔥 秦岭火情监测系统

> 科技守护绿水青山，智能保卫秦岭家园

![Python](https://img.shields.io/badge/Python-3.9+-blue?logo=python&logoColor=white)
![TensorFlow](https://img.shields.io/badge/TensorFlow-2.15-FF6F00?logo=tensorflow&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104-009688?logo=fastapi&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-3-003B57?logo=sqlite&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

## 📖 项目简介

本项目是一套面向秦岭林区的智能化森林火灾预警系统，融合轻量级 CNN 视觉检测与物联网虚拟传感技术，实现从图像识别、环境感知到风险评估的全链路火灾预警。系统提供实时监控仪表盘与指挥大屏，支持 WebSocket 实时数据推送和 Grad-CAM 可解释性分析，适用于低资源环境下的边缘部署场景。

## 🌲 项目背景

秦岭是中国的中央水塔和生态屏障，每年面临严峻的森林火灾威胁。传统人工巡防方式存在 **响应慢、覆盖有限、风险高** 等问题。本项目以 AI + IoT 技术路线，构建了一套 **智能化、实时化、低资源** 的火灾预警系统，旨在提升林区火情发现效率，降低巡防人力成本。

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                     前端展示模块                              │
│   dashboard.html │ dashboard_large.html │ evaluation.html    │
│          (实时仪表盘)    (指挥大屏)      (模型评估)            │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTP / WebSocket
┌─────────────────────▼───────────────────────────────────────┐
│                  FastAPI 后端服务模块                          │
│  ┌──────────┐  ┌───────────┐  ┌──────────┐  ┌────────────┐  │
│  │ 检测 API  │  │ 传感器 API │  │ 告警 API  │  │  数据 API   │  │
│  └────┬─────┘  └─────┬─────┘  └────┬─────┘  └─────┬──────┘  │
│       │              │              │              │         │
│  ┌────▼──────────────▼──────────────▼──────────────▼──────┐  │
│  │              核心业务逻辑层                               │  │
│  │  FireDetector │ VirtualSensorManager │ RiskAssessor    │  │
│  └──────────────────────┬────────────────────────────────┘  │
│                         │                                    │
│  ┌──────────────────────▼────────────────────────────────┐  │
│  │                   SQLite 数据库                         │  │
│  │       检测记录 │ 告警记录 │ 传感器数据 │ 评估指标        │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                    核心 AI 模块                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  轻量级 CNN 模型 (TensorFlow/Keras)                    │   │
│  │  输入: 64×64 RGB │ 输出: 4分类 (fire/smoke/fire_smoke/  │   │
│  │  normal) │ 参数量: <100K │ Grad-CAM 可解释性            │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────┐  ┌────────────────┐  ┌────────────────┐   │
│  │ 数据增强模块   │  │ 内存映射加载器  │  │ 超快数据加载器  │   │
│  └──────────────┘  └────────────────┘  └────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 核心功能

### 🤖 AI 视觉检测
- 轻量级 CNN 模型，参数量 < 100K，模型文件仅 0.37 MB
- 输入尺寸 64×64 RGB，四分类：`fire`（火焰）、`smoke`（烟雾）、`fire_smoke`（火烟复合体）、`normal`（正常）
- 支持 Grad-CAM 热力图可视化，提升模型可解释性
- 单张推理耗时 35-50ms，满足实时检测需求

### 📡 环境传感网络
- 虚拟传感器模拟多维度环境数据：温度、湿度、风速、空气质量（AQI）
- WebSocket 实时推送（每 3 秒更新），支持前端动态刷新
- 内置火灾场景模拟功能，便于演示与测试

### 📊 智能风险评估
- 多源数据融合：AI 置信度 + 环境参数加权综合评估
- **四级预警机制**：低风险（< 30）、中风险（30-49）、高风险（50-69）、紧急（≥ 70）
- 结合秦岭季节与昼夜特征的环境建模

### 📺 实时监控仪表盘
- **标准仪表盘**：检测状态、传感器数据、告警历史、风险趋势图表
- **指挥大屏**：深色科技风大屏展示，适配大屏投屏场景
- **模型评估页**：混淆矩阵、各类别精确率/召回率/F1、训练曲线

### 🔍 Grad-CAM 可解释性
- 基于梯度的类激活映射，可视化模型关注区域
- 检测结果附带热力图，辅助人工复核决策

## 💡 技术亮点

- **解耦架构**：前后端分离设计，支持多客户端独立访问与部署
- **WebSocket 实时推送**：传感器数据每 3 秒自动推送到前端，延迟极低
- **内存映射数据加载**：支持低内存环境运行，系统总内存占用 < 2.0 GB
- **混合精度训练**：TensorFlow 混合精度策略加速模型训练
- **文件安全校验**：上传文件类型/大小/文件名多重验证，防止路径穿越攻击
- **RotatingFileHandler 日志**：system.log / error.log / alert.log 三路日志自动轮转
- **SQLite 持久化**：检测记录、告警记录、传感器数据全部入库，支持历史回溯
- **统一响应格式**：所有 API 返回 `{success, data, message, timestamp}` 标准结构

## 📈 性能指标

| 指标 | 数值 | 说明 |
|:---:|:---:|:---|
| 模型大小 | 0.37 MB | 轻量化部署，适配边缘设备 |
| 推理速度 | 35-50 ms | 单张图片实时检测 |
| 准确率 | 98.96% | 四分类任务验证集表现 |
| 内存占用 | < 2.0 GB | 低资源环境可运行 |
| 并发支持 | 100+ QPS | FastAPI 异步架构高并发 |
| 训练轮数 | 72 epochs | 含早停与学习率衰减策略 |
| 训练样本 | 5000 张 | 4 类 × 1250 张增强样本 |

## 📂 项目结构

```
秦岭火情监测系统/
├── 核心AI模块/
│   ├── __init__.py                # 模块初始化
│   ├── config.py                  # 全局配置（路径、模型参数、训练超参等）
│   ├── fire_cnn_model.py          # CNN 模型定义
│   ├── fire_detector.py           # 火灾检测器（推理 + Grad-CAM）
│   ├── fire_model_trainer.py      # 模型训练脚本
│   ├── data_augmentation.py       # 数据增强模块
│   ├── mmap_fire_data_loader.py   # 内存映射数据加载器
│   └── ultra_fast_data_loader.py  # 超快数据加载器
├── 后端服务模块/
│   ├── api_server.py              # FastAPI 服务主入口（全部 API 端点）
│   ├── database.py                # SQLite 数据库操作层
│   ├── risk_assessor.py           # 风险评估引擎
│   └── sensor_integration.py      # 虚拟传感器管理器
├── 前端展示模块/
│   ├── dashboard.html             # 标准监控仪表盘
│   ├── dashboard.js               # 仪表盘逻辑
│   ├── dashboard_large.html       # 指挥大屏页面
│   ├── dashboard_large.js         # 大屏逻辑
│   ├── dashboard_large.css        # 大屏样式
│   ├── evaluation.html            # 模型评估页面
│   ├── evaluation.js              # 评估页逻辑
│   ├── app.js                     # 前端公共逻辑
│   └── styles.css                 # 公共样式
├── 文档与配置/
│   ├── README.md                  # 文档目录下的 README
│   ├── requirements.txt           # Python 依赖清单
│   ├── deployment.md              # 部署说明
│   └── 项目全局系统分析与架构总报告.md  # 架构设计文档
├── .gitignore
├── docker-compose.yml             # Docker Compose 编排
├── Dockerfile                     # Docker 镜像构建
├── nginx.conf                     # Nginx 反向代理配置
├── run.py                         # 快速启动脚本
├── start.bat                      # Windows 启动脚本
├── stop.bat                       # Windows 停止脚本
└── README.md                      # 本文件
```

## ⚡ 快速开始

### 环境要求

- Python 3.9+
- TensorFlow 2.15
- FastAPI 0.104+
- 操作系统：Windows / Linux / macOS

### 安装依赖

```bash
pip install -r 文档与配置/requirements.txt
```

### 配置说明

核心配置位于 `核心AI模块/config.py`，包含以下可调参数：

| 配置项 | 默认值 | 说明 |
|:---|:---:|:---|
| IMAGE_SIZE | (64, 64) | 模型输入图像尺寸 |
| TRAINING.epochs | 72 | 训练轮数 |
| TRAINING.batch_size | 24 | 批次大小 |
| TRAINING.learning_rate | 0.001 | 学习率 |
| RISK_ASSESSMENT.risk_levels | 四级阈值 | 风险分级阈值 |

### 启动服务

```bash
# 方式一：Python 直接启动（默认端口 8001）
python run.py

# 方式二：Windows 批处理
start.bat

# 方式三：Docker 部署
docker-compose up -d
```

启动后访问：
- 监控仪表盘：`http://localhost:8001/dashboard`
- 指挥大屏：`http://localhost:8001/dashboard-large`
- 模型评估：`http://localhost:8001/evaluation`
- API 文档：`http://localhost:8001/docs`（Swagger UI）
- ReDoc 文档：`http://localhost:8001/redoc`

## 🔌 API 接口

### 系统状态

| 端点 | 方法 | 描述 |
|:---|:---:|:---|
| `/health` | GET | 系统健康检查（含数据库状态） |
| `/status` | GET | 获取详细系统状态 |
| `/system/status` | GET | 系统状态（兼容路径） |
| `/system-status` | GET | 系统综合状态（前端面板专用） |
| `/model/info` | GET | AI 模型详细信息 |

### 火灾检测

| 端点 | 方法 | 描述 |
|:---|:---:|:---|
| `/detect` | POST | 上传图片进行火灾检测（支持传感器融合） |
| `/history` | GET | 获取检测历史记录（分页） |

### 传感器数据

| 端点 | 方法 | 描述 |
|:---|:---:|:---|
| `/sensors` | GET | 获取当前传感器数据 |
| `/sensors/history` | GET | 获取传感器历史数据 |
| `/sensors/simulate-fire` | POST | 模拟火灾场景 |
| `/sensors/reset` | POST | 重置传感器到正常状态 |
| `/api/sensor-data` | POST | 保存传感器数据到数据库 |

### 风险评估

| 端点 | 方法 | 描述 |
|:---|:---:|:---|
| `/assess-risk` | POST | 综合风险评估（AI + 传感器） |
| `/risk-history` | GET | 获取风险评估历史 |
| `/risk-trend` | GET | 近 24 小时风险趋势数据 |

### 告警管理

| 端点 | 方法 | 描述 |
|:---|:---:|:---|
| `/send-alert` | POST | 模拟发送告警通知 |
| `/alert-history` | GET | 获取告警历史记录 |
| `/alert/acknowledge` | POST | 确认告警 |
| `/alert/resolve` | POST | 解决告警 |

### 仪表盘与评估

| 端点 | 方法 | 描述 |
|:---|:---:|:---|
| `/dashboard` | GET | 标准监控仪表盘页面 |
| `/dashboard-large` | GET | 指挥大屏页面 |
| `/dashboard-stats` | GET | 大屏核心统计数据 |
| `/evaluation` | GET | 模型评估页面 |
| `/evaluation/metrics` | GET | 模型评估指标（混淆矩阵、PRF 等） |

### 实时通信

| 端点 | 方法 | 描述 |
|:---|:---:|:---|
| `/ws` | WebSocket | 实时传感器数据推送（每 3 秒） |

## 🔮 后续优化方向

- **API 认证机制**：引入 JWT / API Key 鉴权，保障接口安全
- **热力图存储优化**：Grad-CAM 热力图改为文件存储，减少数据库体积
- **单元测试覆盖**：为核心模块编写 pytest 测试用例，提升代码质量
- **真实传感器接入**：对接 MQTT/LoRa 等物联网协议，替换虚拟传感器
- **模型热更新**：支持不停机模型替换，提升系统可用性

## 📮 联系方式

邮箱：chx20050723@qq.com

欢迎交流讨论，共同守护绿水青山。

## 📄 许可证

本项目基于 [MIT License](LICENSE) 开源。
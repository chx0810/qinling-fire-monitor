## 部署流程
### 自动启动
1. 克隆项目
git clone https://github.com/yourname/qinling-skyguard.git

2. 安装依赖
pip install -r requirements.txt

3. 启动系统
python run.py


### 手动启动
1. 启动后端API（端口8001）
cd 后端服务模块
python api_server.py

2. 启动前端服务（端口8080）
cd 前端展示模块
python -m http.server 8080

3. 访问网站
访问 http://localhost:8080/dashboard.html
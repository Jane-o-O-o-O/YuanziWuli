# 开发运维文档

## 1. 开发环境搭建

### 1.1 Python 环境
```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt
```

### 1.2 依赖包清单 (requirements.txt)
```txt
# Web 框架
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6

# 数据库
sqlalchemy==2.0.23
alembic==1.12.1
sqlite3  # 内置

# 向量数据库
pymilvus==2.3.4

# AI/ML
openai==1.3.7
numpy==1.24.3
scikit-learn==1.3.2

# 文档处理
pypdf2==3.0.1
python-docx==0.8.11
python-pptx==0.6.21
markdown==3.5.1

# 工具库
pydantic==2.5.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-dotenv==1.0.0
httpx==0.25.2
aiofiles==23.2.0

# 开发工具
pytest==7.4.3
pytest-asyncio==0.21.1
black==23.11.0
isort==5.12.0
flake8==6.1.0
```

### 1.3 环境变量配置
复制 `.env.example` 到 `.env` 并配置：
```bash
cp .env.example .env
```

## 2. 数据库初始化

### 2.1 创建迁移
```bash
# 初始化 Alembic
alembic init alembic

# 生成迁移文件
alembic revision --autogenerate -m "Initial migration"

# 执行迁移
alembic upgrade head
```

### 2.2 Milvus Lite 初始化
```python
# 在应用启动时自动创建
python -c "
from app.kb.vectordb import MilvusAdapter
adapter = MilvusAdapter()
adapter.init_connection()
print('Milvus Lite initialized')
"
```

## 3. 启动服务

### 3.1 开发模式
```bash
# 启动后端服务
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 启动前端服务（简单 HTTP 服务器）
cd frontend
python -m http.server 3000
```

### 3.2 生产模式
```bash
# 使用 Gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## 4. 测试

### 4.1 单元测试
```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_rag_service.py

# 生成覆盖率报告
pytest --cov=app tests/
```

### 4.2 API 测试
```bash
# 使用 httpx 测试 API
python tests/test_api_integration.py
```

## 5. 代码质量

### 5.1 代码格式化
```bash
# 格式化代码
black app/ tests/
isort app/ tests/

# 检查代码风格
flake8 app/ tests/
```

### 5.2 类型检查
```bash
# 安装 mypy
pip install mypy

# 类型检查
mypy app/
```

## 6. 部署

### 6.1 Docker 部署
```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite:///./app.db
      - SILICONFLOW_API_KEY=${SILICONFLOW_API_KEY}
    volumes:
      - ./storage:/app/storage
  
  frontend:
    image: nginx:alpine
    ports:
      - "3000:80"
    volumes:
      - ./frontend:/usr/share/nginx/html
```

### 6.2 生产环境配置
```bash
# 环境变量
export DATABASE_URL="postgresql://user:pass@localhost/atomicphysics"
export SILICONFLOW_API_KEY="your-api-key"
export JWT_SECRET="your-secret-key"
export DEBUG=false

# 启动服务
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

## 7. 监控与日志

### 7.1 日志配置
```python
# app/core/logging.py
import logging
from logging.handlers import RotatingFileHandler

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            RotatingFileHandler('logs/app.log', maxBytes=10485760, backupCount=5),
            logging.StreamHandler()
        ]
    )
```

### 7.2 性能监控
```python
# 添加中间件监控请求时间
import time
from fastapi import Request

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response
```

## 8. 备份与恢复

### 8.1 数据库备份
```bash
# SQLite 备份
cp app.db backup/app_$(date +%Y%m%d_%H%M%S).db

# PostgreSQL 备份
pg_dump atomicphysics > backup/db_$(date +%Y%m%d_%H%M%S).sql
```

### 8.2 向量数据备份
```bash
# Milvus Lite 数据备份
cp -r storage/milvus_lite.db backup/milvus_$(date +%Y%m%d_%H%M%S).db
```

## 9. 故障排查

### 9.1 常见问题
1. **API Key 无效**：检查 `.env` 文件中的 `SILICONFLOW_API_KEY`
2. **向量维度不匹配**：确保 embedding 模型输出维度为 1024
3. **Milvus 连接失败**：检查存储目录权限和磁盘空间
4. **内存不足**：调整批处理大小和并发数

### 9.2 调试工具
```bash
# 查看 API 调用日志
tail -f logs/app.log | grep "siliconflow"

# 检查向量数据库状态
python -c "
from pymilvus import connections, utility
connections.connect(uri='./storage/milvus_lite.db')
print(utility.list_collections())
"
```

## 10. 安全配置

### 10.1 生产环境安全
- 使用强密码和复杂的 JWT_SECRET
- 启用 HTTPS
- 配置防火墙规则
- 定期更新依赖包
- 限制文件上传大小和类型

### 10.2 API 安全
- 实施请求频率限制
- 输入验证和清理
- 错误信息脱敏
- 审计日志记录
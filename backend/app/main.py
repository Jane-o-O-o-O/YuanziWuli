from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
import time
import uuid
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.logging import setup_logging
from app.api.v1.router import api_router
from app.db.session import engine
from app.models.orm import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时初始化
    setup_logging()
    
    # 创建数据库表
    Base.metadata.create_all(bind=engine)
    
    # 初始化向量数据库连接
    from app.kb.vectordb import create_vectordb_adapter
    vectordb = create_vectordb_adapter()
    await vectordb.init_connection()
    
    yield
    
    # 关闭时清理
    pass


app = FastAPI(
    title="原子物理智能课堂系统",
    description="基于RAG的原子物理学智能问答和推荐系统",
    version="1.0.0",
    lifespan=lifespan
)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 请求时间中间件
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    response.headers["X-Process-Time"] = str(process_time)
    response.headers["X-Request-ID"] = request_id
    
    return response

# 注册路由
app.include_router(api_router, prefix="/api/v1")

# 静态文件服务 (用于开发测试)
app.mount("/static", StaticFiles(directory="../frontend"), name="static")

# 教案文件服务
import os
if os.path.exists("../原子物理学-教案"):
    app.mount("/materials", StaticFiles(directory="../原子物理学-教案"), name="materials")

@app.get("/")
async def root():
    return {"message": "原子物理智能课堂系统 API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": time.time()}
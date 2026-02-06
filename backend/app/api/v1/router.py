from fastapi import APIRouter

from app.api.v1 import auth, kb, qa, rec, analytics

api_router = APIRouter()

# 注册各模块路由
api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(kb.router, prefix="/kb", tags=["知识库"])
api_router.include_router(qa.router, prefix="/qa", tags=["问答"])
api_router.include_router(rec.router, prefix="/rec", tags=["推荐"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["分析"])
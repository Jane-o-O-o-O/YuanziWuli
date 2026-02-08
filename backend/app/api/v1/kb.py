from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.auth import require_teacher, get_current_user
from app.core.deps import CommonDeps
from app.db.session import get_db
from app.models.orm import User
from app.models.schemas import (
    UploadResponse, IngestRequest, IngestResponse, TaskResponse, SearchResponse
)
from app.services.kb_service import kb_service

router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    course_id: int = Form(...),
    current_user: User = Depends(require_teacher),
    db: Session = Depends(get_db)
):
    """上传文档（需要教师权限）"""
    # 读取文件内容
    file_content = await file.read()
    
    # 获取文件类型
    file_type = file.filename.split('.')[-1] if '.' in file.filename else ''
    
    # 上传文档
    document = await kb_service.upload_document(
        db=db,
        course_id=course_id,
        file_name=file.filename,
        file_content=file_content,
        file_type=file_type
    )
    
    return UploadResponse(
        document_id=document.id,
        status=document.status
    )


@router.post("/ingest", response_model=IngestResponse)
async def ingest_document(
    request: IngestRequest,
    current_user: User = Depends(require_teacher),
    db: Session = Depends(get_db)
):
    """文档入库（需要教师权限）"""
    task_id = await kb_service.ingest_document(
        db=db,
        document_id=request.document_id,
        chunk_policy=request.chunk_policy
    )
    
    return IngestResponse(
        task_id=task_id,
        status="queued"
    )


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取任务状态"""
    task_info = await kb_service.get_task_status(db, task_id)
    
    return TaskResponse(
        task_id=task_info["task_id"],
        status=task_info["status"],
        progress=task_info["progress"],
        error=task_info["error"]
    )


@router.get("/search", response_model=SearchResponse)
async def search_knowledge(
    q: str = Query(..., description="搜索查询"),
    course_id: int = Query(..., description="课程ID"),
    top_k: int = Query(12, description="返回结果数量"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """搜索知识库"""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"API搜索请求: query='{q}', course_id={course_id}, top_k={top_k}")
    
    results = await kb_service.search_knowledge(
        course_id=course_id,
        query=q,
        top_k=top_k
    )
    
    logger.info(f"kb_service返回结果数: {len(results)}")
    if results:
        logger.info(f"第一个结果: {results[0]}")
    
    # 转换为响应格式
    hits = []
    for result in results:
        hits.append({
            "chunk_id": result["chunk_id"],
            "score": result["score"],
            "document_id": result["document_id"],
            "meta": result["meta"],
            "snippet": result["snippet"]
        })
    
    logger.info(f"转换后hits数: {len(hits)}")
    
    return SearchResponse(hits=hits)


@router.get("/documents/{document_id}")
async def get_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取完整文档内容"""
    from app.models.orm import Document
    
    # 查询文档
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    # 读取文档内容
    import os
    parsed_path = os.path.join("backend/storage/parsed", str(document.course_id), f"{document.id}.txt")
    
    content = ""
    if os.path.exists(parsed_path):
        with open(parsed_path, 'r', encoding='utf-8') as f:
            content = f.read()
    
    return {
        "id": document.id,
        "filename": document.file_name,
        "course_id": document.course_id,
        "status": document.status,
        "content": content,
        "created_at": document.created_at.isoformat() if document.created_at else None
    }
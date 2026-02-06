from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
import json
import logging
import time

from app.core.auth import get_current_user
from app.db.session import get_db
from app.models.orm import User
from app.models.schemas import QARequest, QAResponse, FeedbackRequest, BaseResponse
from app.services.rag_service import rag_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/ask", response_model=QAResponse)
async def ask_question(
    request: QARequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """问答接口"""
    start_time = time.time()
    
    result = await rag_service.ask_question(
        db=db,
        user_id=current_user.id,
        course_id=request.course_id,
        question=request.question,
        top_k=request.top_k,
        stream=False
    )
    
    elapsed = time.time() - start_time
    logger.info(f"QA请求完成: question='{request.question}', 耗时={elapsed:.2f}s")
    
    return QAResponse(
        qa_id=result["qa_id"],
        answer=result["answer"],
        confidence=result["confidence"],
        citations=result["citations"],
        followups=result["followups"]
    )


@router.post("/feedback", response_model=BaseResponse)
async def add_feedback(
    request: FeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """添加问答反馈"""
    await rag_service.add_feedback(db, request.qa_id, request.rating)
    
    return BaseResponse(message="反馈已保存")


@router.websocket("/stream")
async def qa_stream(websocket: WebSocket, db: Session = Depends(get_db)):
    """流式问答WebSocket接口"""
    await websocket.accept()
    
    try:
        while True:
            # 接收消息
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # 验证消息格式
            if "course_id" not in message or "question" not in message:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "缺少必要参数: course_id, question"
                }))
                continue
            
            # TODO: 在WebSocket中实现用户认证
            # 这里简化处理，实际应该验证token
            user_id = message.get("user_id", 1)  # 临时处理
            
            try:
                # 流式生成答案
                async for chunk in rag_service.ask_question(
                    db=db,
                    user_id=user_id,
                    course_id=message["course_id"],
                    question=message["question"],
                    stream=True
                ):
                    await websocket.send_text(json.dumps(chunk))
                    
            except Exception as e:
                logger.error(f"流式问答失败: {e}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": str(e)
                }))
                
    except WebSocketDisconnect:
        logger.info("WebSocket连接断开")
    except Exception as e:
        logger.error(f"WebSocket错误: {e}")
        await websocket.close()
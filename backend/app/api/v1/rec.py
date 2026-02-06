from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.session import get_db
from app.models.orm import User
from app.models.schemas import RecommendationResponse, ProfileRecommendationResponse
from app.services.rec_service import rec_service

router = APIRouter()


@router.get("/by_question", response_model=RecommendationResponse)
async def recommend_by_question(
    q: str = Query(..., description="问题内容"),
    course_id: int = Query(..., description="课程ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """基于问题的推荐"""
    recommendations = await rec_service.recommend_by_question(
        db=db,
        course_id=course_id,
        question=q
    )
    
    return recommendations


@router.get("/by_profile", response_model=ProfileRecommendationResponse)
async def recommend_by_profile(
    user_id: int = Query(None, description="用户ID，默认为当前用户"),
    course_id: int = Query(..., description="课程ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """基于用户画像的推荐"""
    # 如果没有指定用户ID，使用当前用户
    target_user_id = user_id if user_id else current_user.id
    
    # 权限检查：只有管理员和教师可以查看其他用户的推荐
    if target_user_id != current_user.id and current_user.role not in ["admin", "teacher"]:
        target_user_id = current_user.id
    
    recommendations = await rec_service.recommend_by_profile(
        db=db,
        user_id=target_user_id,
        course_id=course_id
    )
    
    return recommendations
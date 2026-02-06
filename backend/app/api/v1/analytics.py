from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, require_teacher
from app.db.session import get_db
from app.models.orm import User
from app.models.schemas import EventRequest, BaseResponse, StudentProfile, ClassDashboard
from app.services.analytics_service import analytics_service

router = APIRouter()


@router.post("/event", response_model=BaseResponse)
async def record_event(
    request: EventRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """记录学习事件"""
    # 权限检查：只能记录自己的事件，除非是管理员或教师
    if request.user_id != current_user.id and current_user.role not in ["admin", "teacher"]:
        request.user_id = current_user.id
    
    await analytics_service.record_event(
        db=db,
        user_id=request.user_id,
        course_id=request.course_id,
        event_type=request.event_type,
        payload=request.payload,
        timestamp=request.ts
    )
    
    return BaseResponse(message="事件记录成功")


@router.get("/student/{user_id}", response_model=StudentProfile)
async def get_student_profile(
    user_id: int,
    course_id: int = Query(..., description="课程ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取学生画像"""
    # 权限检查：只能查看自己的画像，除非是管理员或教师
    if user_id != current_user.id and current_user.role not in ["admin", "teacher"]:
        user_id = current_user.id
    
    profile = await analytics_service.get_student_profile(
        db=db,
        user_id=user_id,
        course_id=course_id
    )
    
    return profile


@router.get("/class/{course_id}", response_model=ClassDashboard)
async def get_class_dashboard(
    course_id: int,
    current_user: User = Depends(require_teacher),
    db: Session = Depends(get_db)
):
    """获取班级面板（需要教师权限）"""
    dashboard = await analytics_service.get_class_dashboard(
        db=db,
        course_id=course_id
    )
    
    return dashboard
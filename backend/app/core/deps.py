from fastapi import Depends, Request
from sqlalchemy.orm import Session
from typing import Optional

from app.db.session import get_db
from app.core.auth import get_current_user
from app.models.orm import User


def get_request_id(request: Request) -> str:
    """获取请求ID"""
    return getattr(request.state, 'request_id', 'unknown')


def get_user_id(current_user: User = Depends(get_current_user)) -> int:
    """获取当前用户ID"""
    return current_user.id


def get_optional_user(
    db: Session = Depends(get_db),
    authorization: Optional[str] = None
) -> Optional[User]:
    """获取可选用户（用于不需要强制登录的接口）"""
    if not authorization:
        return None
    
    try:
        from app.core.auth import verify_token
        token = authorization.replace("Bearer ", "")
        payload = verify_token(token)
        
        if payload is None:
            return None
        
        username = payload.get("sub")
        if username is None:
            return None
        
        user = db.query(User).filter(User.username == username).first()
        return user
    except Exception:
        return None


class CommonDeps:
    """通用依赖注入类"""
    
    def __init__(
        self,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
        request_id: str = Depends(get_request_id)
    ):
        self.db = db
        self.current_user = current_user
        self.request_id = request_id
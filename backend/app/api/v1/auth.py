from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta

from app.core.auth import authenticate_user, create_access_token, get_password_hash, get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.orm import User
from app.models.schemas import UserLogin, TokenResponse, UserResponse, UserCreate

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(user_login: UserLogin, db: Session = Depends(get_db)):
    """用户登录"""
    print(f"DEBUG: 收到登录请求 - 用户名: {user_login.username}, 密码长度: {len(user_login.password)}")
    
    user = authenticate_user(db, user_login.username, user_login.password)
    print(f"DEBUG: 认证结果 - 用户: {user}")
    
    if not user:
        print(f"DEBUG: 认证失败 - 用户名: {user_login.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    print(f"DEBUG: 登录成功 - 用户: {user.username}, 角色: {user.role}")
    return TokenResponse(
        access_token=access_token,
        role=user.role
    )


@router.post("/register", response_model=UserResponse)
async def register(user_create: UserCreate, db: Session = Depends(get_db)):
    """用户注册"""
    # 检查用户名是否已存在
    existing_user = db.query(User).filter(User.username == user_create.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )
    
    # 创建新用户
    hashed_password = get_password_hash(user_create.password)
    user = User(
        username=user_create.username,
        password_hash=hashed_password,
        role=user_create.role
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return UserResponse.from_orm(user)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return UserResponse.from_orm(current_user)
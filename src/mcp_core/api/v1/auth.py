"""
认证API路由
"""

from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ...common.logger import get_logger
from ...common.utils import generate_id
from ...models.tables import User, UserPermission
from ..dependencies import (
    authenticate_user,
    create_access_token,
    get_current_active_user,
    get_db,
    get_password_hash,
)

logger = get_logger(__name__)
router = APIRouter()


class LoginRequest(BaseModel):
    """登录请求"""

    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)


class LoginResponse(BaseModel):
    """登录响应"""

    success: bool
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str
    role: str


class RegisterRequest(BaseModel):
    """注册请求"""

    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., max_length=100)
    password: str = Field(..., min_length=6)
    full_name: str = Field(default="", max_length=100)


class RegisterResponse(BaseModel):
    """注册响应"""

    success: bool
    user_id: str
    username: str
    message: str


class UserInfoResponse(BaseModel):
    """用户信息响应"""

    user_id: str
    username: str
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: str


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
) -> Any:
    """
    用户登录

    返回JWT访问令牌
    """
    user = authenticate_user(db, request.username, request.password)

    if not user:
        logger.warning(f"Failed login attempt for username: {request.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    # 创建访问令牌
    access_token_expires = timedelta(minutes=30)  # 可以从配置读取
    access_token = create_access_token(
        data={"sub": user.user_id, "username": user.username, "role": user.role},
        expires_delta=access_token_expires,
    )

    logger.info(f"User logged in: {user.username} ({user.user_id})")

    return LoginResponse(
        success=True,
        access_token=access_token,
        token_type="bearer",
        user_id=user.user_id,
        username=user.username,
        role=user.role,
    )


@router.post("/register", response_model=RegisterResponse)
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db),
) -> Any:
    """
    用户注册

    创建新用户账号和默认权限
    """
    # 检查用户名是否已存在
    existing_user = db.query(User).filter(User.username == request.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    # 检查邮箱是否已存在
    existing_email = db.query(User).filter(User.email == request.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # 创建新用户
    user_id = generate_id("user")
    new_user = User(
        user_id=user_id,
        username=request.username,
        email=request.email,
        password_hash=get_password_hash(request.password),
        full_name=request.full_name,
        role="user",  # 默认角色
        is_active=True,
    )

    db.add(new_user)
    db.flush()  # 获取user_id

    # 创建默认权限 (只读权限)
    default_permission = UserPermission(
        user_id=user_id,
        can_read_memory=True,
        can_write_memory=False,
        can_delete_memory=False,
        can_read_project=True,
        can_write_project=False,
        can_delete_project=False,
        can_manage_users=False,
        can_view_stats=True,
        can_export_data=False,
    )

    db.add(default_permission)
    db.commit()
    db.refresh(new_user)

    logger.info(f"New user registered: {request.username} ({user_id})")

    return RegisterResponse(
        success=True,
        user_id=user_id,
        username=request.username,
        message="User registered successfully",
    )


@router.get("/me", response_model=UserInfoResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    获取当前用户信息

    需要认证
    """
    return UserInfoResponse(
        user_id=current_user.user_id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name or "",
        role=current_user.role,
        is_active=current_user.is_active,
        created_at=current_user.created_at.isoformat(),
    )


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    """
    用户登出

    客户端应删除本地存储的JWT令牌
    """
    logger.info(f"User logged out: {current_user.username}")

    return {
        "success": True,
        "message": "Logged out successfully",
    }

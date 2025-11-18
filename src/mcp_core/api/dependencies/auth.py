"""
认证依赖和权限检查
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from ...common.config import get_settings
from ...common.logger import get_logger
from ...models.tables import User, UserPermission
from .database import get_db

logger = get_logger(__name__)
settings = get_settings()

# 密码哈希
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer认证
security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建JWT访问令牌"""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.security.jwt.access_token_expire_minutes
        )

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.security.jwt.secret_key,
        algorithm=settings.security.jwt.algorithm,
    )

    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """解码JWT令牌"""
    try:
        payload = jwt.decode(
            token,
            settings.security.jwt.secret_key,
            algorithms=[settings.security.jwt.algorithm],
        )
        return payload
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """获取当前认证用户"""
    token = credentials.credentials

    payload = decode_access_token(token)
    user_id: str = payload.get("sub")

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

    user = db.query(User).filter(User.user_id == user_id).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    # 更新最后登录时间
    user.last_login_at = datetime.utcnow()
    db.commit()

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """获取当前活跃用户"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


def check_permission(permission_name: str):
    """
    权限检查装饰器工厂

    用法:
    @router.get("/protected")
    async def protected_route(
        current_user: User = Depends(check_permission("memory.read"))
    ):
        ...
    """

    async def permission_checker(
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db),
    ) -> User:
        # 检查是否是管理员
        if current_user.role == "admin":
            return current_user

        # 检查用户权限
        user_permission = (
            db.query(UserPermission)
            .filter(UserPermission.user_id == current_user.user_id)
            .first()
        )

        if not user_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No permissions configured for user",
            )

        # 解析权限名称 (如 "memory.read")
        resource, action = permission_name.split(".", 1)

        # 检查具体权限
        permission_field = f"can_{action}_{resource}"

        if not hasattr(user_permission, permission_field):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Invalid permission: {permission_name}",
            )

        has_permission = getattr(user_permission, permission_field, False)

        if not has_permission:
            logger.warning(
                f"User {current_user.user_id} attempted to access "
                f"{permission_name} without permission"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission_name}",
            )

        return current_user

    return permission_checker


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """认证用户"""
    user = db.query(User).filter(User.username == username).first()

    if not user:
        return None

    if not verify_password(password, user.password_hash):
        return None

    return user

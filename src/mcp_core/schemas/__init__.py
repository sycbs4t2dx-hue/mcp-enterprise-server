"""
Pydantic数据模型(用于API请求/响应验证)
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


# ============ 基础Schema ============
class BaseResponse(BaseModel):
    """通用响应格式"""

    code: int = Field(default=0, description="错误码,0表示成功")
    message: str = Field(default="success", description="响应消息")
    data: Optional[Any] = Field(default=None, description="响应数据")


# ============ 记忆相关Schema ============
class MemoryStoreRequest(BaseModel):
    """存储记忆请求"""

    project_id: str = Field(..., min_length=1, max_length=64, pattern="^[a-zA-Z0-9_-]+$")
    content: str = Field(..., min_length=1, max_length=10000)
    memory_level: str = Field(..., pattern="^(short|mid|long)$")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        """验证内容安全性"""
        dangerous_patterns = ["';", "--", "/*", "*/", "xp_", "sp_"]
        for pattern in dangerous_patterns:
            if pattern in v.lower():
                raise ValueError(f"内容包含非法字符: {pattern}")
        return v


class MemoryStoreResponse(BaseModel):
    """存储记忆响应"""

    memory_id: str
    stored_at: str


class MemoryRetrieveRequest(BaseModel):
    """检索记忆请求"""

    project_id: str = Field(..., min_length=1, max_length=64)
    query: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=50)
    memory_levels: List[str] = Field(default=["short", "mid", "long"])

    @field_validator("memory_levels")
    @classmethod
    def validate_levels(cls, v: List[str]) -> List[str]:
        """验证记忆层级"""
        valid_levels = {"short", "mid", "long"}
        for level in v:
            if level not in valid_levels:
                raise ValueError(f"无效的记忆层级: {level}")
        return v


class MemoryItem(BaseModel):
    """单条记忆"""

    memory_id: str
    content: str
    relevance_score: float = Field(ge=0.0, le=1.0)
    source: str = Field(description="short_term/mid_term/long_term")
    timestamp: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class MemoryRetrieveResponse(BaseModel):
    """检索记忆响应"""

    memories: List[MemoryItem]
    total_token_saved: int = Field(ge=0)


class MemoryUpdateRequest(BaseModel):
    """更新记忆请求"""

    content: str = Field(..., min_length=1, max_length=10000)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class MemoryDeleteRequest(BaseModel):
    """删除记忆请求"""

    project_id: str
    memory_id: str


# ============ Token优化Schema ============
class TokenCompressRequest(BaseModel):
    """Token压缩请求"""

    content: str = Field(..., min_length=1, max_length=50000)
    content_type: str = Field(default="text", pattern="^(code|text)$")
    compression_ratio: float = Field(default=0.2, ge=0.1, le=0.9)


class TokenCompressResponse(BaseModel):
    """Token压缩响应"""

    original_tokens: int
    compressed_tokens: int
    compression_rate: float = Field(ge=0.0, le=1.0)
    compressed_content: str


# ============ 幻觉检测Schema ============
class HallucinationValidateRequest(BaseModel):
    """幻觉检测请求"""

    project_id: str = Field(..., min_length=1, max_length=64)
    output: str = Field(..., min_length=1, max_length=10000)
    threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class HallucinationValidateResponse(BaseModel):
    """幻觉检测响应"""

    is_hallucination: bool
    confidence: float = Field(ge=0.0, le=1.0)
    matched_memories: List[str] = Field(default_factory=list)
    threshold_used: float


# ============ 项目管理Schema ============
class ProjectCreate(BaseModel):
    """创建项目请求"""

    project_id: str = Field(..., min_length=1, max_length=64, pattern="^[a-zA-Z0-9_-]+$")
    project_name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    owner_id: str = Field(..., min_length=1, max_length=64)


class ProjectResponse(BaseModel):
    """项目响应"""

    project_id: str
    project_name: str
    description: Optional[str]
    owner_id: str
    status: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # Pydantic v2语法


class ProjectUpdate(BaseModel):
    """更新项目请求"""

    project_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[int] = Field(default=None, ge=0, le=1)


# ============ 权限管理Schema ============
class PermissionGrant(BaseModel):
    """授予权限请求"""

    user_id: str = Field(..., min_length=1, max_length=64)
    project_id: str = Field(..., min_length=1, max_length=64)
    permission: str = Field(
        ...,
        pattern="^(memory|project|user|config):(read|write|update|delete|create|invite|remove)$",
    )
    expires_at: Optional[datetime] = None


class PermissionRevoke(BaseModel):
    """撤销权限请求"""

    user_id: str
    project_id: str
    permission: str


class PermissionCheck(BaseModel):
    """权限检查请求"""

    user_id: str
    project_id: str
    permission: str


class PermissionCheckResponse(BaseModel):
    """权限检查响应"""

    has_permission: bool
    expires_at: Optional[datetime] = None


# ============ 用户管理Schema ============
class UserCreate(BaseModel):
    """创建用户请求"""

    username: str = Field(..., min_length=3, max_length=100)
    email: str = Field(..., pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$")
    password: str = Field(..., min_length=8, max_length=100)
    full_name: Optional[str] = Field(default=None, max_length=100)


class UserLogin(BaseModel):
    """用户登录请求"""

    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class UserResponse(BaseModel):
    """用户响应"""

    user_id: str
    username: str
    email: str
    full_name: Optional[str]
    is_active: bool
    is_superuser: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Token响应"""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


# ============ 审计日志Schema ============
class AuditLogQuery(BaseModel):
    """审计日志查询请求"""

    user_id: Optional[str] = None
    project_id: Optional[str] = None
    action: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    is_sensitive: Optional[bool] = None
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


class AuditLogItem(BaseModel):
    """审计日志项"""

    log_id: int
    user_id: str
    project_id: Optional[str]
    action: str
    resource_type: str
    resource_id: str
    details: Dict[str, Any]
    ip_address: Optional[str]
    is_sensitive: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogResponse(BaseModel):
    """审计日志响应"""

    logs: List[AuditLogItem]
    total: int


# ============ 系统配置Schema ============
class ConfigUpdate(BaseModel):
    """更新配置请求"""

    config_key: str = Field(..., min_length=1, max_length=100)
    config_value: Any
    description: Optional[str] = None


class ConfigResponse(BaseModel):
    """配置响应"""

    config_key: str
    config_value: Any
    description: Optional[str]
    category: Optional[str]
    updated_at: datetime

    class Config:
        from_attributes = True


# ============ 健康检查Schema ============
class HealthCheckResponse(BaseModel):
    """健康检查响应"""

    status: str = "healthy"
    timestamp: datetime
    version: str
    database: str
    redis: str
    vector_db: str

"""
SQLAlchemy数据模型定义 (MySQL适配版)
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import Base


class Project(Base):
    """项目表"""

    __tablename__ = "projects"
    __table_args__ = {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"}

    project_id = Column(String(64), primary_key=True, index=True)
    name = Column(String(255), nullable=False)  # 修改字段名从project_name到name
    description = Column(Text)
    owner_id = Column(String(64), nullable=False, index=True)
    is_active = Column(Boolean, default=True, comment="项目是否激活")
    meta_data = Column(JSON, default=dict)  # 改名避免与SQLAlchemy的metadata冲突
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关系
    long_memories = relationship("LongMemory", back_populates="project", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Project(id={self.project_id}, name={self.name})>"


class LongMemory(Base):
    """长期记忆表(核心事实)"""

    __tablename__ = "long_memories"
    __table_args__ = (
        Index("idx_long_mem_project_category", "project_id", "category"),
        Index("idx_long_mem_created", "created_at"),
        {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"},
    )

    memory_id = Column(String(64), primary_key=True)
    project_id = Column(String(64), ForeignKey("projects.project_id", ondelete="CASCADE"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    category = Column(String(50), index=True, comment="framework/api/rule/config/general")
    confidence = Column(Float, default=0.80, comment="置信度(0-1)")
    meta_data = Column(JSON, default=dict)  # 改名避免冲突
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关系
    project = relationship("Project", back_populates="long_memories")

    def __repr__(self) -> str:
        return f"<LongMemory(id={self.memory_id}, project={self.project_id})>"


class UserPermission(Base):
    """用户权限表(细粒度权限控制)"""

    __tablename__ = "user_permissions"
    __table_args__ = (
        Index("idx_user_perm", "user_id"),
        {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), nullable=False, index=True)

    # 9种细粒度权限
    can_read_memory = Column(Boolean, default=False)
    can_write_memory = Column(Boolean, default=False)
    can_delete_memory = Column(Boolean, default=False)
    can_read_project = Column(Boolean, default=False)
    can_write_project = Column(Boolean, default=False)
    can_delete_project = Column(Boolean, default=False)
    can_manage_users = Column(Boolean, default=False)
    can_view_stats = Column(Boolean, default=False)
    can_export_data = Column(Boolean, default=False)

    granted_by = Column(String(64))
    granted_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<UserPermission(user={self.user_id})>"


class AuditLog(Base):
    """审计日志表"""

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("idx_audit_user_time", "user_id", "created_at"),
        Index("idx_audit_sensitive", "is_sensitive", "created_at"),
        Index("idx_audit_project", "project_id", "created_at"),
        {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"},
    )

    log_id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(String(64), nullable=False, index=True)
    project_id = Column(String(64), nullable=True, index=True)
    action = Column(String(50), nullable=False, comment="store/retrieve/update/delete/permission_grant...")
    resource_type = Column(String(50), nullable=False, comment="memory/config/project/user")
    resource_id = Column(String(64), nullable=False)
    details = Column(JSON, default=dict)
    ip_address = Column(String(45), nullable=True, comment="IPv4/IPv6")
    user_agent = Column(Text, nullable=True)
    is_sensitive = Column(Boolean, default=False, comment="敏感操作标记")
    created_at = Column(DateTime, server_default=func.now(), index=True)

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.log_id}, user={self.user_id}, action={self.action})>"


class User(Base):
    """用户表(基础认证)"""

    __tablename__ = "users"
    __table_args__ = {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"}

    user_id = Column(String(64), primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)  # 修改字段名
    full_name = Column(String(100))
    role = Column(String(20), default="user", comment="admin/user")  # 添加角色字段
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_login_at = Column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<User(id={self.user_id}, username={self.username})>"


class SystemConfig(Base):
    """系统配置表(动态配置)"""

    __tablename__ = "system_configs"
    __table_args__ = {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"}

    config_key = Column(String(100), primary_key=True)
    config_value = Column(JSON, nullable=False)
    description = Column(Text)
    category = Column(String(50), index=True, comment="memory/token/hallucination/security")
    is_encrypted = Column(Boolean, default=False)
    updated_by = Column(String(64))
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<SystemConfig(key={self.config_key}, category={self.category})>"

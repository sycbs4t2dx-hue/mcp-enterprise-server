"""
MCP Core Models - 统一的数据模型模块

集中管理所有数据模型,确保:
1. 所有模型使用统一的Base
2. 外键关系正确定义
3. 元数据完整共享

版本: 2.0.0
日期: 2025-01-19
"""

# ==================== 导入统一Base ====================

from .base import (
    Base,
    BaseModel,
    TimestampMixin,
    SoftDeleteMixin,
    TableNameMixin,
    get_metadata,
    get_all_tables,
    get_table,
    create_all_tables,
    drop_all_tables,
    print_table_info,
)

# ==================== 导入数据库工具 ====================

from .database import (
    engine,
    SessionLocal,
    get_db,
    init_db,
)

# ==================== 导入现有模型 ====================

from .tables import (
    User,
    UserPermission,
    Project,
    SystemConfig,
    AuditLog,
    LongMemory,
)

# ==================== 导出列表 ====================

__all__ = [
    # 核心Base和Mixin
    'Base',
    'BaseModel',
    'TimestampMixin',
    'SoftDeleteMixin',
    'TableNameMixin',

    # 元数据工具
    'get_metadata',
    'get_all_tables',
    'get_table',
    'create_all_tables',
    'drop_all_tables',
    'print_table_info',

    # 数据库工具
    'engine',
    'SessionLocal',
    'get_db',
    'init_db',

    # 用户和权限模型
    'User',
    'UserPermission',
    'Project',
    'SystemConfig',
    'AuditLog',
    'LongMemory',
]

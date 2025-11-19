"""
MCP Core - 统一的SQLAlchemy Base模型

这是MCP项目的核心数据模型基础:
- 提供全局唯一的declarative_base
- 定义通用的Mixin类
- 确保所有模型共享同一个元数据实例

重要:
- 所有新模型必须从这里导入Base
- 不要在其他文件中创建新的declarative_base()
- 保持元数据的单一性,确保外键关系正确

作者: Claude Code AI
日期: 2025-01-19
版本: 2.0.0
"""

from datetime import datetime
from typing import Any, Dict

from sqlalchemy import Column, DateTime, Integer, String, func
from sqlalchemy.ext.declarative import declarative_base, declared_attr

# ==================== 全局唯一的Base ====================

# 这是整个MCP项目唯一的declarative_base实例
# 所有数据模型都必须继承自这个Base
Base = declarative_base()


# ==================== 通用Mixin类 ====================

class TimestampMixin:
    """
    时间戳Mixin

    自动添加created_at和updated_at字段
    """

    created_at = Column(
        DateTime,
        server_default=func.now(),
        nullable=False,
        comment="创建时间"
    )

    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="更新时间"
    )


class SoftDeleteMixin:
    """
    软删除Mixin

    添加deleted_at字段,支持软删除
    """

    deleted_at = Column(
        DateTime,
        nullable=True,
        comment="删除时间"
    )

    @property
    def is_deleted(self) -> bool:
        """是否已删除"""
        return self.deleted_at is not None

    def soft_delete(self):
        """软删除"""
        self.deleted_at = datetime.now()

    def restore(self):
        """恢复"""
        self.deleted_at = None


class TableNameMixin:
    """
    表名Mixin

    自动生成表名(类名转蛇形命名)
    """

    @declared_attr
    def __tablename__(cls) -> str:
        """自动生成表名"""
        import re
        # 将驼峰命名转为蛇形命名
        name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', cls.__name__)
        name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()
        return name


class BaseModel(Base, TimestampMixin):
    """
    基础模型类

    所有业务模型都应该继承这个类,它提供:
    - 统一的Base
    - 自动的时间戳
    - 通用的辅助方法

    使用示例:
    ```python
    from mcp_core.models.base import BaseModel

    class MyModel(BaseModel):
        __tablename__ = "my_models"
        id = Column(Integer, primary_key=True)
        name = Column(String(100))
    ```
    """

    __abstract__ = True  # 标记为抽象类,不创建表

    def to_dict(self, exclude: list = None) -> Dict[str, Any]:
        """
        转换为字典

        Args:
            exclude: 要排除的字段列表

        Returns:
            字典表示
        """
        exclude = exclude or []
        result = {}

        for column in self.__table__.columns:
            if column.name not in exclude:
                value = getattr(self, column.name)

                # 处理datetime类型
                if isinstance(value, datetime):
                    value = value.isoformat()

                result[column.name] = value

        return result

    def update_from_dict(self, data: Dict[str, Any], allowed_fields: list = None):
        """
        从字典更新

        Args:
            data: 数据字典
            allowed_fields: 允许更新的字段列表(None表示全部)
        """
        for key, value in data.items():
            if allowed_fields is None or key in allowed_fields:
                if hasattr(self, key):
                    setattr(self, key, value)

    def __repr__(self) -> str:
        """字符串表示"""
        attrs = []
        for column in self.__table__.columns:
            if column.primary_key:
                value = getattr(self, column.name)
                attrs.append(f"{column.name}={value}")

        return f"<{self.__class__.__name__}({', '.join(attrs)})>"


# ==================== 元数据访问 ====================

def get_metadata():
    """
    获取全局元数据实例

    Returns:
        MetaData实例
    """
    return Base.metadata


def get_all_tables():
    """
    获取所有表名

    Returns:
        表名列表
    """
    return list(Base.metadata.tables.keys())


def get_table(table_name: str):
    """
    获取指定表

    Args:
        table_name: 表名

    Returns:
        Table对象,如果不存在返回None
    """
    return Base.metadata.tables.get(table_name)


# ==================== 工具函数 ====================

def create_all_tables(engine):
    """
    创建所有表

    Args:
        engine: SQLAlchemy Engine
    """
    Base.metadata.create_all(bind=engine)
    print(f"✅ 创建了 {len(Base.metadata.tables)} 张表")


def drop_all_tables(engine):
    """
    删除所有表(危险操作!)

    Args:
        engine: SQLAlchemy Engine
    """
    Base.metadata.drop_all(bind=engine)
    print(f"⚠️  删除了所有表")


def print_table_info():
    """打印所有表信息"""
    print("=" * 60)
    print(f"MCP数据模型 - {len(Base.metadata.tables)} 张表")
    print("=" * 60)

    for table_name, table in sorted(Base.metadata.tables.items()):
        print(f"\n📋 {table_name}")
        print(f"   列数: {len(table.columns)}")

        # 主键
        pks = [col.name for col in table.primary_key]
        if pks:
            print(f"   主键: {', '.join(pks)}")

        # 外键
        fks = []
        for fk in table.foreign_keys:
            fks.append(f"{fk.parent.name} -> {fk.target_fullname}")
        if fks:
            print(f"   外键: {len(fks)}个")
            for fk in fks[:3]:  # 最多显示3个
                print(f"     - {fk}")

    print("\n" + "=" * 60)


# ==================== 导出 ====================

__all__ = [
    # 核心Base
    'Base',
    'BaseModel',

    # Mixin类
    'TimestampMixin',
    'SoftDeleteMixin',
    'TableNameMixin',

    # 元数据访问
    'get_metadata',
    'get_all_tables',
    'get_table',

    # 工具函数
    'create_all_tables',
    'drop_all_tables',
    'print_table_info',
]

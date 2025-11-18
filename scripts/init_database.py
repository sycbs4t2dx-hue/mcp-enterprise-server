#!/usr/bin/env python
"""
数据库初始化脚本 (MySQL版)
创建表结构并插入初始数据
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from passlib.context import CryptContext
from sqlalchemy import text

from src.mcp_core.common.config import get_settings
from src.mcp_core.common.logger import get_logger
from src.mcp_core.common.utils import generate_id
from src.mcp_core.models.database import SessionLocal, engine, init_db
from src.mcp_core.models.tables import Project, SystemConfig, User, UserPermission

logger = get_logger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_tables() -> None:
    """创建所有表"""
    logger.info("开始创建数据库表...")

    try:
        init_db()
        logger.info("✓ 数据库表创建成功")
    except Exception as e:
        logger.error(f"✗ 数据库表创建失败: {e}")
        raise


def insert_initial_data() -> None:
    """插入初始数据"""
    logger.info("开始插入初始数据...")
    db = SessionLocal()

    try:
        # 1. 创建管理员用户
        admin_user_id = generate_id("user")
        admin_user = User(
            user_id=admin_user_id,
            username="admin",
            email="admin@mcp-project.com",
            password_hash=pwd_context.hash("admin123"),
            full_name="系统管理员",
            role="admin",
            is_active=True,
        )
        db.add(admin_user)
        db.flush()

        # 2. 创建管理员权限 (全部权限)
        admin_permission = UserPermission(
            user_id=admin_user_id,
            can_read_memory=True,
            can_write_memory=True,
            can_delete_memory=True,
            can_read_project=True,
            can_write_project=True,
            can_delete_project=True,
            can_manage_users=True,
            can_view_stats=True,
            can_export_data=True,
            granted_by=admin_user_id,
        )
        db.add(admin_permission)

        # 3. 创建测试用户
        test_user_id = generate_id("user")
        test_user = User(
            user_id=test_user_id,
            username="testuser",
            email="test@mcp-project.com",
            password_hash=pwd_context.hash("test123"),
            full_name="测试用户",
            role="user",
            is_active=True,
        )
        db.add(test_user)
        db.flush()

        # 4. 创建测试用户权限 (只读)
        test_permission = UserPermission(
            user_id=test_user_id,
            can_read_memory=True,
            can_write_memory=False,
            can_delete_memory=False,
            can_read_project=True,
            can_write_project=False,
            can_delete_project=False,
            can_manage_users=False,
            can_view_stats=True,
            can_export_data=False,
            granted_by=admin_user_id,
        )
        db.add(test_permission)

        # 5. 创建示例项目
        demo_project = Project(
            project_id="proj_demo_001",
            name="Demo Project",
            description="示例项目,用于测试MCP功能",
            owner_id=admin_user_id,
            is_active=True,
        )
        db.add(demo_project)

        # 6. 插入默认系统配置
        default_configs = [
            SystemConfig(
                config_key="memory.retrieval_strategy",
                config_value={"strategy": "hybrid", "weights": {"semantic": 0.6, "keyword": 0.3, "time": 0.1}},
                description="记忆检索策略配置",
                category="memory",
            ),
            SystemConfig(
                config_key="token.compression_enabled",
                config_value={"enabled": True, "compression_ratio": 0.2},
                description="Token压缩配置",
                category="token",
            ),
            SystemConfig(
                config_key="hallucination.base_threshold",
                config_value={"threshold": 0.65, "adaptive": True},
                description="幻觉检测阈值配置",
                category="hallucination",
            ),
        ]

        for config in default_configs:
            db.add(config)

        db.commit()
        logger.info("✓ 初始数据插入成功")
        logger.info(f"  - 管理员账号: admin / admin123")
        logger.info(f"  - 测试账号: testuser / test123")
        logger.info(f"  - 示例项目ID: {demo_project.project_id}")

    except Exception as e:
        db.rollback()
        logger.error(f"✗ 初始数据插入失败: {e}")
        raise
    finally:
        db.close()


def check_database_connection() -> bool:
    """检查数据库连接"""
    logger.info("检查MySQL数据库连接...")

    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT VERSION()"))
            version = result.fetchone()[0]
            logger.info(f"✓ MySQL版本: {version}")

        logger.info("✓ 数据库连接正常")
        return True

    except Exception as e:
        logger.error(f"✗ 数据库连接失败: {e}")
        logger.error(f"  数据库URL: {get_settings().database.url}")
        logger.error(f"\n请确保:")
        logger.error(f"  1. MySQL服务已启动")
        logger.error(f"  2. 数据库 'mcp_db' 已创建: CREATE DATABASE mcp_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        logger.error(f"  3. 用户权限正确: GRANT ALL ON mcp_db.* TO 'mcp_user'@'localhost';")
        return False


def main() -> None:
    """主函数"""
    logger.info("="*60)
    logger.info("MCP数据库初始化 (MySQL)")
    logger.info("="*60)

    # 1. 检查连接
    if not check_database_connection():
        logger.error("数据库连接失败,请检查配置!")
        sys.exit(1)

    # 2. 创建表
    create_tables()

    # 3. 插入初始数据
    insert_initial_data()

    logger.info("="*60)
    logger.info("数据库初始化完成!")
    logger.info("="*60)


if __name__ == "__main__":
    main()

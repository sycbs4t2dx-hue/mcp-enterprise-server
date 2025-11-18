#!/usr/bin/env python3
"""
配置验证脚本
检查配置文件和数据库连接是否正常
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from urllib.parse import urlparse


def check_config_file():
    """检查配置文件是否存在"""
    print("=" * 60)
    print("1. 检查配置文件")
    print("=" * 60)

    config_path = Path("config.yaml")
    if config_path.exists():
        print(f"✓ 配置文件存在: {config_path.absolute()}")
        print(f"  文件大小: {config_path.stat().st_size} bytes")
        return True
    else:
        print(f"✗ 配置文件不存在: {config_path.absolute()}")
        print("\n请执行: cp config.example.yaml config.yaml")
        return False


def check_database_url():
    """检查数据库URL配置"""
    print("\n" + "=" * 60)
    print("2. 检查数据库URL配置")
    print("=" * 60)

    try:
        from src.mcp_core.common.config import get_settings

        settings = get_settings()
        db_url = settings.database.url

        print(f"✓ 配置加载成功")
        print(f"  数据库URL: {db_url}")

        # 解析URL
        parsed = urlparse(db_url)
        print(f"\n  URL组成:")
        print(f"  - 驱动: {parsed.scheme}")
        print(f"  - 用户: {parsed.username}")
        print(f"  - 密码: {'*' * len(parsed.password or '')}")
        print(f"  - 主机: {parsed.hostname}")
        print(f"  - 端口: {parsed.port}")
        print(f"  - 数据库: {parsed.path.lstrip('/')}")

        return db_url
    except Exception as e:
        print(f"✗ 配置加载失败: {e}")
        return None


def check_mysql_connection(db_url):
    """检查MySQL连接"""
    print("\n" + "=" * 60)
    print("3. 检查MySQL连接")
    print("=" * 60)

    try:
        engine = create_engine(db_url)

        with engine.connect() as conn:
            # 检查版本
            result = conn.execute(text("SELECT VERSION()"))
            version = result.scalar()
            print(f"✓ MySQL连接成功")
            print(f"  版本: {version}")

            # 检查字符集
            result = conn.execute(
                text("SELECT @@character_set_database, @@collation_database")
            )
            charset, collation = result.fetchone()
            print(f"  字符集: {charset}")
            print(f"  排序规则: {collation}")

            # 检查数据库
            result = conn.execute(text("SELECT DATABASE()"))
            db_name = result.scalar()
            print(f"  当前数据库: {db_name}")

        return True
    except Exception as e:
        print(f"✗ MySQL连接失败: {e}")
        print("\n可能的原因:")
        print("  1. MySQL服务未启动")
        print("  2. 密码错误")
        print("  3. 数据库不存在")
        print("\n解决方法:")
        print("  1. 检查MySQL: mysql -u root -p")
        print("  2. 创建数据库: mysql -u root -p < scripts/setup_mysql.sql")
        return False


def check_database_tables(db_url):
    """检查数据库表"""
    print("\n" + "=" * 60)
    print("4. 检查数据库表")
    print("=" * 60)

    try:
        engine = create_engine(db_url)

        with engine.connect() as conn:
            # 获取表列表
            result = conn.execute(text("SHOW TABLES"))
            tables = [row[0] for row in result]

            if tables:
                print(f"✓ 找到 {len(tables)} 张表:")
                for table in tables:
                    # 获取行数
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = result.scalar()
                    print(f"  - {table}: {count} 行")
                return True
            else:
                print("✗ 数据库中没有表")
                print("\n请运行初始化脚本:")
                print("  python scripts/init_database.py")
                return False
    except Exception as e:
        print(f"✗ 检查表失败: {e}")
        return False


def check_redis_connection():
    """检查Redis连接"""
    print("\n" + "=" * 60)
    print("5. 检查Redis连接 (可选)")
    print("=" * 60)

    try:
        from src.mcp_core.common.config import get_settings

        settings = get_settings()

        import redis

        r = redis.from_url(settings.redis.url)
        r.ping()
        print(f"✓ Redis连接成功")
        print(f"  URL: {settings.redis.url}")
        return True
    except ImportError:
        print("⚠ Redis未安装 (可选组件)")
        return None
    except Exception as e:
        print(f"⚠ Redis连接失败: {e}")
        print("  Redis是可选组件，不影响核心功能")
        return None


def check_dependencies():
    """检查Python依赖"""
    print("\n" + "=" * 60)
    print("6. 检查Python依赖")
    print("=" * 60)

    required_packages = [
        "fastapi",
        "uvicorn",
        "sqlalchemy",
        "pymysql",
        "pydantic",
        "passlib",
    ]

    all_ok = True
    for package in required_packages:
        try:
            __import__(package)
            print(f"✓ {package}")
        except ImportError:
            print(f"✗ {package} 未安装")
            all_ok = False

    if not all_ok:
        print("\n请安装依赖:")
        print("  pip install -e '.[dev]'")

    return all_ok


def main():
    """主函数"""
    print("=" * 60)
    print("MCP项目配置验证")
    print("=" * 60)

    results = []

    # 1. 检查配置文件
    results.append(("配置文件", check_config_file()))

    # 2. 检查数据库URL
    db_url = check_database_url()
    results.append(("数据库URL", db_url is not None))

    if db_url:
        # 3. 检查MySQL连接
        results.append(("MySQL连接", check_mysql_connection(db_url)))

        # 4. 检查数据库表
        results.append(("数据库表", check_database_tables(db_url)))

    # 5. 检查Redis (可选)
    redis_ok = check_redis_connection()
    if redis_ok is not None:
        results.append(("Redis连接", redis_ok))

    # 6. 检查依赖
    results.append(("Python依赖", check_dependencies()))

    # 总结
    print("\n" + "=" * 60)
    print("验证总结")
    print("=" * 60)

    for name, ok in results:
        status = "✓" if ok else "✗"
        print(f"{status} {name}")

    # 统计
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print(f"\n通过: {passed}/{total}")

    if passed == total:
        print("\n✓ 所有检查通过！可以启动服务:")
        print("  uvicorn src.mcp_core.main:app --reload")
        return 0
    else:
        print("\n✗ 部分检查失败，请修复后再启动服务")
        return 1


if __name__ == "__main__":
    sys.exit(main())

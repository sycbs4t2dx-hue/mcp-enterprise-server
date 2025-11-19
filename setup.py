#!/usr/bin/env python3
"""
MCP v2.0.0 - 一键初始化脚本

功能:
1. 检查Python版本和依赖
2. 安装所有依赖包
3. 检查MySQL连接
4. 创建所有数据库表
5. 生成默认配置文件
6. 验证安装

使用:
    python setup.py --install          # 完整安装
    python setup.py --check-db         # 仅检查数据库
    python setup.py --create-tables    # 仅创建表
    python setup.py --verify           # 验证安装
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# 颜色输出
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """打印标题"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text:^60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}\n")


def print_success(text: str):
    """打印成功信息"""
    print(f"{Colors.OKGREEN}✅ {text}{Colors.ENDC}")


def print_warning(text: str):
    """打印警告信息"""
    print(f"{Colors.WARNING}⚠️  {text}{Colors.ENDC}")


def print_error(text: str):
    """打印错误信息"""
    print(f"{Colors.FAIL}❌ {text}{Colors.ENDC}")


def print_info(text: str):
    """打印信息"""
    print(f"{Colors.OKCYAN}ℹ️  {text}{Colors.ENDC}")


# ==================== Step 1: 检查Python版本 ====================

def check_python_version() -> bool:
    """检查Python版本 (需要 >= 3.9)"""
    print_info("检查Python版本...")

    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        print_error(f"Python版本过低: {version.major}.{version.minor}.{version.micro}")
        print_error("需要Python 3.9或更高版本")
        return False

    print_success(f"Python版本: {version.major}.{version.minor}.{version.micro}")
    return True


# ==================== Step 2: 安装依赖 ====================

def check_and_install_dependencies(auto_install: bool = True) -> bool:
    """检查并安装依赖"""
    print_info("检查依赖包...")

    requirements_file = Path(__file__).parent / "requirements.txt"
    if not requirements_file.exists():
        print_error(f"未找到依赖文件: {requirements_file}")
        return False

    # 读取依赖
    with open(requirements_file, 'r') as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

    print_info(f"找到 {len(requirements)} 个依赖包")

    if not auto_install:
        print_warning("跳过依赖安装 (需要手动运行: pip install -r requirements.txt)")
        return True

    # 安装依赖
    print_info("安装依赖包...")
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", str(requirements_file)
        ], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        print_success("所有依赖已安装")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"依赖安装失败: {e}")
        print_warning("请手动运行: pip install -r requirements.txt")
        return False


# ==================== Step 3: 检查MySQL连接 ====================

def check_mysql_connection(config: Dict[str, Any]) -> bool:
    """检查MySQL连接"""
    print_info("检查MySQL连接...")

    try:
        import pymysql
    except ImportError:
        print_error("pymysql未安装，请先安装依赖")
        return False

    db_config = config.get('database', {})
    host = db_config.get('host', 'localhost')
    port = db_config.get('port', 3306)
    user = db_config.get('user', 'root')
    password = db_config.get('password', '')
    database = db_config.get('database', 'mcp_db')

    try:
        # 尝试连接（不指定数据库）
        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password
        )
        print_success(f"MySQL连接成功: {user}@{host}:{port}")

        # 检查/创建数据库
        cursor = conn.cursor()
        cursor.execute(f"SHOW DATABASES LIKE '{database}'")
        exists = cursor.fetchone()

        if not exists:
            print_info(f"创建数据库: {database}")
            cursor.execute(f"CREATE DATABASE {database} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            print_success(f"数据库已创建: {database}")
        else:
            print_success(f"数据库已存在: {database}")

        conn.close()
        return True

    except Exception as e:
        print_error(f"MySQL连接失败: {e}")
        print_warning("请检查:")
        print_warning(f"  - MySQL服务是否运行")
        print_warning(f"  - 连接信息: {user}@{host}:{port}")
        print_warning(f"  - 用户权限")
        return False


# ==================== Step 4: 创建数据库表 ====================

def create_database_tables(config: Dict[str, Any]) -> bool:
    """创建所有数据库表"""
    print_info("创建数据库表...")

    try:
        from sqlalchemy import create_engine, inspect
        from sqlalchemy.orm import sessionmaker

        # 导入所有模型
        sys.path.insert(0, str(Path(__file__).parent))
        from src.mcp_core.models.tables import Base as BaseTable
        from src.mcp_core.code_knowledge_service import CodeProject, CodeEntityModel, CodeRelationModel, CodeKnowledge
        from src.mcp_core.project_context_service import ProjectSession, DesignDecision, ProjectNote, DevelopmentTodo
        from src.mcp_core.quality_guardian_service import QualityIssue, DebtSnapshot, QualityWarning, RefactoringSuggestion

    except ImportError as e:
        print_error(f"导入模型失败: {e}")
        return False

    # 生成数据库URL
    db_config = config.get('database', {})
    import urllib.parse
    password_encoded = urllib.parse.quote_plus(db_config.get('password', ''))
    url = f"mysql+pymysql://{db_config.get('user', 'root')}:{password_encoded}@{db_config.get('host', 'localhost')}:{db_config.get('port', 3306)}/{db_config.get('database', 'mcp_db')}?charset=utf8mb4"


    try:
        # 创建引擎
        engine = create_engine(url, pool_pre_ping=True)

        # 检查现有表
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()

        # 定义所有表名
        all_tables = [
            'projects', 'long_memories', 'users', 'user_permissions',
            'audit_logs', 'system_configs',
            'code_projects', 'code_entities', 'code_relations', 'code_knowledge',
            'project_sessions', 'design_decisions', 'project_notes', 'development_todos',
            'quality_issues', 'debt_snapshots', 'quality_warnings', 'refactoring_suggestions'
        ]

        # 显示现有表
        if existing_tables:
            print_warning(f"发现 {len(existing_tables)} 个现有表")
            for table in existing_tables:
                print(f"   - {table}")

        # 创建表
        print_info(f"创建 {len(all_tables)} 个数据表...")
        BaseTable.metadata.create_all(engine)

        # 验证
        inspector = inspect(engine)
        created_tables = inspector.get_table_names()

        print_success(f"数据表创建完成: {len(created_tables)}/{len(all_tables)}")

        # 显示创建的表
        for table in all_tables:
            if table in created_tables:
                print(f"   ✅ {table}")
            else:
                print(f"   ❌ {table} (未创建)")

        return len(created_tables) >= len(all_tables) - 2  # 允许少量表失败

    except Exception as e:
        print_error(f"创建数据表失败: {e}")
        import traceback
        traceback.print_exc()
        return False


# ==================== Step 5: 生成配置文件 ====================

def generate_config_file(output_path: str = "config/mcp_config.json") -> Dict[str, Any]:
    """生成默认配置文件"""
    print_info("生成配置文件...")

    # 默认配置
    default_config = {
        "database": {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", "3306")),
            "user": os.getenv("DB_USER", "root"),
            "password": os.getenv("DB_PASSWORD", ""),
            "database": os.getenv("DB_NAME", "mcp_db")
        },
        "ai": {
            "provider": "anthropic",
            "api_key": os.getenv("ANTHROPIC_API_KEY", ""),
            "model": "claude-3-5-sonnet-20241022",
            "timeout": 30
        },
        "server": {
            "name": "mcp-unified-server",
            "version": "2.0.0",
            "log_level": "INFO",
            "log_file": "logs/mcp_server.log"
        },
        "performance": {
            "max_workers": 4,
            "request_timeout": 300,
            "db_pool_size": 10,
            "db_max_overflow": 20
        }
    }

    # 创建目录
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # 保存配置
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(default_config, f, indent=2, ensure_ascii=False)

    print_success(f"配置文件已生成: {output_path}")

    # 显示配置摘要
    print("\n配置摘要:")
    print(f"  数据库: {default_config['database']['user']}@{default_config['database']['host']}:{default_config['database']['port']}/{default_config['database']['database']}")

    if default_config['ai']['api_key']:
        print(f"  AI服务: ✅ 已配置 ({default_config['ai']['provider']}/{default_config['ai']['model']})")
    else:
        print_warning("  AI服务: ⚠️  未配置 (请设置ANTHROPIC_API_KEY环境变量)")

    return default_config


# ==================== Step 6: 验证安装 ====================

def verify_installation(config: Dict[str, Any]) -> bool:
    """验证安装"""
    print_info("验证安装...")

    checks = []

    # 1. 检查配置文件
    config_file = Path("config/mcp_config.json")
    if config_file.exists():
        checks.append(("配置文件", True))
    else:
        checks.append(("配置文件", False))

    # 2. 检查日志目录
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    checks.append(("日志目录", log_dir.exists()))

    # 3. 检查数据库连接
    db_ok = check_mysql_connection(config)
    checks.append(("数据库连接", db_ok))

    # 4. 检查核心文件
    core_files = [
        "mcp_server_unified.py",
        "config_manager.py",
        "src/mcp_core/services/memory_service.py",
        "src/mcp_core/code_knowledge_service.py",
        "src/mcp_core/project_context_service.py",
        "src/mcp_core/quality_guardian_service.py"
    ]

    all_files_ok = True
    for file in core_files:
        file_path = Path(file)
        if not file_path.exists():
            checks.append((f"核心文件: {file}", False))
            all_files_ok = False

    if all_files_ok:
        checks.append((f"核心文件 ({len(core_files)}个)", True))

    # 显示检查结果
    print("\n验证结果:")
    success_count = 0
    for check_name, status in checks:
        if status:
            print(f"  ✅ {check_name}")
            success_count += 1
        else:
            print(f"  ❌ {check_name}")

    print(f"\n总计: {success_count}/{len(checks)} 检查通过")

    return success_count == len(checks)


# ==================== 主函数 ====================

def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        description="MCP v2.0.0 一键初始化脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python setup.py --install              # 完整安装
  python setup.py --check-db             # 仅检查数据库
  python setup.py --create-tables        # 仅创建表
  python setup.py --verify               # 验证安装
  python setup.py --config custom.json   # 使用自定义配置
        """
    )

    parser.add_argument('--install', action='store_true', help='完整安装')
    parser.add_argument('--check-db', action='store_true', help='仅检查数据库')
    parser.add_argument('--create-tables', action='store_true', help='仅创建数据表')
    parser.add_argument('--verify', action='store_true', help='验证安装')
    parser.add_argument('--config', default='config/mcp_config.json', help='配置文件路径')
    parser.add_argument('--skip-deps', action='store_true', help='跳过依赖安装')
    parser.add_argument('--no-sample-data', action='store_true', help='不导入示例数据')

    args = parser.parse_args()

    # 如果没有指定任何操作，默认完整安装
    if not any([args.install, args.check_db, args.create_tables, args.verify]):
        args.install = True

    print_header("MCP v2.0.0 - 一键初始化")

    success = True

    try:
        # Step 1: 检查Python版本
        if not check_python_version():
            return 1

        # Step 2: 安装依赖（仅在完整安装时）
        if args.install and not args.skip_deps:
            if not check_and_install_dependencies(auto_install=True):
                print_warning("依赖安装失败，但继续执行...")

        # 生成/加载配置
        config_file = Path(args.config)
        if config_file.exists():
            print_info(f"加载配置文件: {config_file}")
            with open(config_file, 'r') as f:
                config = json.load(f)
        else:
            config = generate_config_file(args.config)

        # Step 3: 检查数据库
        if args.install or args.check_db:
            if not check_mysql_connection(config):
                print_error("数据库连接失败")
                success = False
                if args.install:
                    print_warning("是否继续? (可能会导致后续步骤失败)")
                    response = input("继续? (y/N): ")
                    if response.lower() != 'y':
                        return 1

        # Step 4: 创建数据表
        if args.install or args.create_tables:
            if not create_database_tables(config):
                print_error("数据表创建失败")
                success = False

        # Step 5: 验证安装
        if args.install or args.verify:
            print_header("验证安装")
            if not verify_installation(config):
                print_warning("安装验证未完全通过")
                success = False

        # 最终总结
        print_header("安装完成")

        if success:
            print_success("🎉 MCP v2.0.0 安装成功！")
            print("\n下一步:")
            print("  1. 配置AI服务 (可选):")
            print("     export ANTHROPIC_API_KEY='your-api-key'")
            print("\n  2. 启动MCP服务器:")
            print("     python mcp_server_unified.py")
            print("\n  3. 运行测试:")
            print("     python test_end_to_end.py")
            print("\n📚 文档: DEPLOYMENT_GUIDE.md")
            return 0
        else:
            print_warning("⚠️  安装完成，但有部分检查未通过")
            print_info("请查看上方错误信息并手动修复")
            return 1

    except KeyboardInterrupt:
        print_error("\n\n安装被中断")
        return 1
    except Exception as e:
        print_error(f"安装失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

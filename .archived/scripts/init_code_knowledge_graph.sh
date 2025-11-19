#!/bin/bash
#
# MCP代码知识图谱系统 - 一键初始化脚本
# 用法: ./init_code_knowledge_graph.sh
#

set -e

echo "========================================"
echo "MCP代码知识图谱系统初始化"
echo "========================================"
echo ""

# 检查Python版本
echo "1️⃣ 检查Python环境..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "   Python版本: $PYTHON_VERSION"

# 检查MySQL连接
echo ""
echo "2️⃣ 检查MySQL连接..."
read -p "MySQL root密码: " -s MYSQL_PASSWORD
echo ""

mysql -u root -p"$MYSQL_PASSWORD" -e "SELECT 1" &>/dev/null
if [ $? -eq 0 ]; then
    echo "   ✓ MySQL连接成功"
else
    echo "   ✗ MySQL连接失败，请检查密码"
    exit 1
fi

# 创建代码知识图谱表
echo ""
echo "3️⃣ 创建数据库表..."
python3 << EOF
from sqlalchemy import create_engine
from src.mcp_core.code_knowledge_service import Base

try:
    engine = create_engine("mysql+pymysql://root:$MYSQL_PASSWORD@localhost:3306/mcp_db?charset=utf8mb4")
    Base.metadata.create_all(engine)
    print("   ✓ 代码知识图谱表创建成功")
    print("     - code_projects")
    print("     - code_entities")
    print("     - code_relations")
    print("     - code_knowledge")
except Exception as e:
    print(f"   ✗ 表创建失败: {e}")
    exit(1)
EOF

if [ $? -ne 0 ]; then
    exit 1
fi

# 测试代码分析器
echo ""
echo "4️⃣ 测试代码分析器..."
echo "   分析MCP项目自身作为示例..."

python3 << EOF
import sys
sys.path.insert(0, '/Users/mac/Downloads/MCP')

from src.mcp_core.code_analyzer import ProjectAnalyzer
from src.mcp_core.code_knowledge_service import CodeKnowledgeGraphService
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

try:
    # 分析项目
    analyzer = ProjectAnalyzer("/Users/mac/Downloads/MCP/src/mcp_core")
    result = analyzer.analyze_project()

    print(f"   ✓ 代码分析完成")
    print(f"     文件数: {result['stats']['total_files']}")
    print(f"     实体数: {len(result['entities'])}")
    print(f"     关系数: {len(result['relations'])}")

    # 存储到数据库
    engine = create_engine("mysql+pymysql://root:$MYSQL_PASSWORD@localhost:3306/mcp_db?charset=utf8mb4")
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    service = CodeKnowledgeGraphService(db)
    service.create_project(
        project_id="mcp_core",
        name="MCP Core",
        path="/Users/mac/Downloads/MCP/src/mcp_core",
        language="python"
    )

    service.store_analysis_result(
        project_id="mcp_core",
        entities=result['entities'],
        relations=result['relations'],
        stats=result['stats']
    )

    print(f"   ✓ 知识图谱存储成功")

    db.close()

except Exception as e:
    print(f"   ✗ 测试失败: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
EOF

if [ $? -ne 0 ]; then
    echo "   测试失败，请查看错误信息"
    exit 1
fi

# 测试查询功能
echo ""
echo "5️⃣ 测试查询功能..."
python3 << EOF
import sys
sys.path.insert(0, '/Users/mac/Downloads/MCP')

from src.mcp_core.code_knowledge_service import CodeKnowledgeGraphService
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

try:
    engine = create_engine("mysql+pymysql://root:$MYSQL_PASSWORD@localhost:3306/mcp_db?charset=utf8mb4")
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    service = CodeKnowledgeGraphService(db)

    # 查询架构
    arch = service.query_architecture("mcp_core")
    if arch and 'project' in arch:
        print(f"   ✓ 架构查询成功")
        print(f"     项目: {arch['project']['name']}")
        print(f"     类数量: {arch['entity_stats'].get('class', 0)}")
        print(f"     函数数: {arch['entity_stats'].get('function', 0)}")

    # 搜索实体
    entities = service.search_by_name("mcp_core", "MemoryService", fuzzy=False)
    if entities:
        print(f"   ✓ 实体搜索成功")
        print(f"     找到 {len(entities)} 个匹配")

    db.close()

except Exception as e:
    print(f"   ✗ 查询测试失败: {e}")
    exit(1)
EOF

if [ $? -ne 0 ]; then
    echo "   测试失败"
    exit 1
fi

echo ""
echo "========================================"
echo "✅ 初始化完成！"
echo "========================================"
echo ""
echo "代码知识图谱系统已就绪！"
echo ""
echo "📚 示例数据:"
echo "   - 项目ID: mcp_core"
echo "   - 已分析MCP核心代码"
echo "   - 可以开始查询和测试"
echo ""
echo "🚀 下一步:"
echo "   1. 分析您自己的项目:"
echo "      python3 src/mcp_core/code_analyzer.py /path/to/your/project"
echo ""
echo "   2. 在Claude Desktop中使用:"
echo "      查看 CODE_KNOWLEDGE_GRAPH_GUIDE.md"
echo ""
echo "   3. 查看测试示例:"
echo "      python3 test_code_knowledge_graph.py"
echo ""
echo "========================================"

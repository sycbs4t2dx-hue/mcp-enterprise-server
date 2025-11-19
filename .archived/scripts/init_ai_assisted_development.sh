#!/bin/bash
# AI辅助持续开发系统 - 初始化脚本

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║   AI辅助项目持续开发系统 - 初始化                          ║"
echo "║   MCP v1.5.0                                             ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# 检查Python
echo "🔍 检查Python环境..."
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到Python3，请先安装Python3"
    exit 1
fi
echo "✅ Python3已安装"

# 检查pip
if ! command -v pip3 &> /dev/null; then
    echo "❌ 未找到pip3，请先安装pip3"
    exit 1
fi
echo "✅ pip3已安装"

# 安装依赖
echo ""
echo "📦 安装Python依赖..."
pip3 install sqlalchemy pymysql fastapi anthropic javalang uvicorn

if [ $? -eq 0 ]; then
    echo "✅ 依赖安装成功"
else
    echo "❌ 依赖安装失败"
    exit 1
fi

# 检查MySQL
echo ""
echo "🔍 检查MySQL连接..."
python3 -c "
import pymysql
try:
    conn = pymysql.connect(
        host='localhost',
        port=3306,
        user='root',
        password='Wxwy.2025@#',
        charset='utf8mb4'
    )
    print('✅ MySQL连接成功')
    conn.close()
except Exception as e:
    print(f'❌ MySQL连接失败: {e}')
    print('请确保MySQL已启动，并且密码正确')
    exit(1)
"

if [ $? -ne 0 ]; then
    exit 1
fi

# 创建数据库
echo ""
echo "🗄️  创建数据库和表..."
python3 << EOF
from sqlalchemy import create_engine
from src.mcp_core.project_context_service import Base as ContextBase
from src.mcp_core.code_knowledge_service import Base as CodeBase

DB_URL = "mysql+pymysql://root:Wxwy.2025%40%23@localhost:3306/mcp_db?charset=utf8mb4"
engine = create_engine(DB_URL)

print("创建代码知识图谱表...")
CodeBase.metadata.create_all(engine)

print("创建项目上下文管理表...")
ContextBase.metadata.create_all(engine)

print("✅ 数据库表创建成功")
EOF

if [ $? -ne 0 ]; then
    echo "❌ 数据库表创建失败"
    exit 1
fi

# 检查API Key
echo ""
echo "🔑 检查Claude API Key..."
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "⚠️  未设置ANTHROPIC_API_KEY环境变量"
    echo "   AI辅助功能将无法使用"
    echo "   设置方法: export ANTHROPIC_API_KEY='your-api-key'"
    echo ""
    echo "   如果没有API Key，可以从以下地址获取:"
    echo "   https://console.anthropic.com/account/keys"
else
    echo "✅ API Key已设置"
fi

# 运行测试
echo ""
echo "🧪 运行功能测试..."
python3 test_ai_assisted_development.py

if [ $? -eq 0 ]; then
    echo ""
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║   ✅ 初始化完成！                                         ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo ""
    echo "📚 使用指南:"
    echo ""
    echo "1. 在Claude Code/Desktop中配置MCP服务器:"
    echo "   {"
    echo "     \"mcpServers\": {"
    echo "       \"memory-with-ai\": {"
    echo "         \"command\": \"python3\","
    echo "         \"args\": [\"$(pwd)/src/mcp_stdio_server.py\"],"
    echo "         \"env\": {"
    echo "           \"ANTHROPIC_API_KEY\": \"your-key\""
    echo "         }"
    echo "       }"
    echo "     }"
    echo "   }"
    echo ""
    echo "2. 重启Claude Code/Desktop"
    echo ""
    echo "3. 开始使用:"
    echo "   - '分析这个项目'"
    echo "   - '帮我规划XXX功能'"
    echo "   - '继续开发'"
    echo ""
    echo "📖 完整文档:"
    echo "   - AI_ASSISTED_DEVELOPMENT_IMPLEMENTATION.md"
    echo "   - RELEASE_v1.5.0.md"
    echo ""
    echo "🎉 让项目永不烂尾！"
else
    echo ""
    echo "❌ 测试失败，请检查错误信息"
    exit 1
fi

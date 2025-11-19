#!/bin/bash
#
# MCP项目启动脚本
# 用法: ./start.sh
#

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "======================================"
echo "MCP项目启动"
echo "======================================"
echo "项目目录: $SCRIPT_DIR"
echo ""

# 检查Python版本
python3 --version
echo ""

# 检查依赖
echo "检查依赖..."
if ! python3 -c "import uvicorn" 2>/dev/null; then
    echo "错误: uvicorn未安装"
    echo "请运行: pip install -e '.[dev]'"
    exit 1
fi

if ! python3 -c "import fastapi" 2>/dev/null; then
    echo "错误: fastapi未安装"
    echo "请运行: pip install -e '.[dev]'"
    exit 1
fi

echo "✓ 依赖检查通过"
echo ""

# 检查配置文件
if [ ! -f "config.yaml" ]; then
    echo "警告: config.yaml不存在"
    if [ -f "config.example.yaml" ]; then
        echo "复制示例配置..."
        cp config.example.yaml config.yaml
        echo "✓ 配置文件已创建，请检查并修改"
    else
        echo "错误: 找不到配置文件"
        exit 1
    fi
fi

echo "✓ 配置文件存在"
echo ""

# 启动服务
echo "======================================"
echo "启动FastAPI服务..."
echo "======================================"
echo "地址: http://0.0.0.0:8000"
echo "API文档: http://localhost:8000/docs"
echo "健康检查: http://localhost:8000/health"
echo ""
echo "按 Ctrl+C 停止服务"
echo ""

# 启动uvicorn
python3 -m uvicorn src.mcp_core.main:app \
    --reload \
    --host 0.0.0.0 \
    --port 8000 \
    --log-level info

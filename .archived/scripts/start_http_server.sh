#!/bin/bash
# MCP HTTP服务器启动脚本

echo "🚀 启动MCP HTTP服务器 (局域网版本)"
echo "=========================================="
echo ""

# 设置数据库密码
export DB_PASSWORD="Wxwy.2025@#"

# 检查Docker服务
echo "📦 检查Docker服务..."
if ! docker ps | grep -q "mcp-mysql\|mcp-redis\|mcp-milvus"; then
    echo "⚠️  Docker服务未运行，正在启动..."
    docker start mcp-mysql mcp-redis mcp-milvus
    sleep 5
fi

docker ps --filter "name=mcp-" --format "✅ {{.Names}} - {{.Status}}"
echo ""

# 获取本机IP
LOCAL_IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -1)

echo "🌐 网络信息:"
echo "  本机IP: $LOCAL_IP"
echo "  服务端口: 8765"
echo "  访问地址: http://$LOCAL_IP:8765"
echo ""

echo "📋 同事配置:"
echo "  让同事在Claude Desktop中配置："
echo "  http://$LOCAL_IP:8765"
echo ""

echo "🔧 启动服务器..."
echo "  按 Ctrl+C 停止服务器"
echo ""

# 启动HTTP服务器
python3 mcp_server_http.py --host 0.0.0.0 --port 8765

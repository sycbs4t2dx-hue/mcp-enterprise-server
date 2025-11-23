#!/bin/bash

# ============================================
# MCP Frontend 启动和测试脚本
# ============================================

set -e

PROJECT_DIR="/Users/mac/Downloads/MCP"
UI_DIR="${PROJECT_DIR}/mcp-admin-ui"

echo "============================================"
echo "🚀 MCP Frontend 启动脚本"
echo "============================================"
echo ""

# 检查后端服务
echo "📡 检查后端服务状态..."
if curl -s http://localhost:8765/health > /dev/null; then
    echo "✅ 后端服务运行正常"
    HEALTH=$(curl -s http://localhost:8765/health | python3 -c "import sys, json; data=json.load(sys.stdin); print(f'Version: {data[\"version\"]}, Uptime: {int(data[\"uptime_seconds\"]/60)}分钟')")
    echo "   $HEALTH"
else
    echo "❌ 后端服务未运行"
    echo "   请先启动后端服务："
    echo "   cd $PROJECT_DIR && python3 mcp_server_enterprise.py"
    exit 1
fi

# 检查WebSocket
echo ""
echo "🔌 测试WebSocket连接..."
RESPONSE=$(curl -s -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" -H "Sec-WebSocket-Version: 13" -H "Sec-WebSocket-Key: test" http://localhost:8765/ws 2>&1 | head -1)
if [[ $RESPONSE == *"101"* ]]; then
    echo "✅ WebSocket连接正常"
else
    echo "⚠️  WebSocket连接异常"
fi

# 检查前端服务
echo ""
echo "🎨 检查前端服务..."
if lsof -i :5173 > /dev/null 2>&1; then
    echo "   端口5173已被占用"
    FRONTEND_URL="http://localhost:5174"
elif lsof -i :5174 > /dev/null 2>&1; then
    echo "   端口5174已被占用"
    FRONTEND_URL="http://localhost:5175"
elif lsof -i :5175 > /dev/null 2>&1; then
    echo "✅ 前端服务已在运行"
    FRONTEND_URL="http://localhost:5175"
else
    echo "🔧 启动前端服务..."
    cd $UI_DIR
    npm run dev &
    sleep 3
    FRONTEND_URL="http://localhost:5173"
    echo "✅ 前端服务已启动"
fi

echo ""
echo "============================================"
echo "📊 系统状态总览"
echo "============================================"
echo "后端API: http://localhost:8765"
echo "WebSocket: ws://localhost:8765/ws"
echo "前端页面: $FRONTEND_URL"
echo "API文档: http://localhost:8765/docs"
echo "健康检查: http://localhost:8765/health"
echo ""
echo "============================================"
echo "🎯 快速访问链接"
echo "============================================"
echo ""
echo "1. 打开前端页面"
echo "   open $FRONTEND_URL"
echo ""
echo "2. 打开测试页面"
echo "   open ${PROJECT_DIR}/test_frontend.html"
echo ""
echo "3. 查看API文档"
echo "   open http://localhost:8765/docs"
echo ""
echo "============================================"
echo "💡 常见问题"
echo "============================================"
echo ""
echo "Q: 前端页面无法连接WebSocket?"
echo "A: 1. 确保后端服务正在运行"
echo "   2. 检查防火墙设置"
echo "   3. 刷新页面重试"
echo ""
echo "Q: 页面显示空白?"
echo "A: 1. 打开浏览器开发者工具(F12)"
echo "   2. 查看Console是否有错误"
echo "   3. 检查Network标签页的WebSocket连接"
echo ""
echo "============================================"

# 询问是否打开页面
echo ""
read -p "是否打开前端页面? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    open $FRONTEND_URL
    echo "✅ 已在浏览器中打开前端页面"
fi

echo ""
echo "🎉 设置完成！"
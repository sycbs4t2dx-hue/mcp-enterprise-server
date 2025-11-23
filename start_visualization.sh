#!/bin/bash

# 启动MCP知识图谱可视化服务器

echo "============================================"
echo "🗺️  MCP知识图谱可视化服务器"
echo "============================================"

# 检查端口
PORT=8888
if lsof -i :$PORT > /dev/null 2>&1; then
    echo "⚠️  端口 $PORT 已被占用"
    echo "正在尝试使用端口 8889..."
    PORT=8889
fi

echo ""
echo "📊 启动可视化服务器..."
echo "   端口: $PORT"
echo ""

# 启动服务器
python3 visualization_server.py --port $PORT &

# 等待服务器启动
sleep 3

# 打开浏览器
echo "🌐 打开浏览器..."
open http://localhost:$PORT

echo ""
echo "============================================"
echo "✅ 可视化服务器已启动"
echo "   访问地址: http://localhost:$PORT"
echo "============================================"
echo ""
echo "功能特性:"
echo "   • 查看所有项目的知识图谱"
echo "   • 3D/2D可视化切换"
echo "   • 时间轴查看历史快照"
echo "   • 跨项目搜索和对比"
echo "   • 实时更新通过WebSocket"
echo ""
echo "按 Ctrl+C 停止服务器"

# 等待用户中断
wait
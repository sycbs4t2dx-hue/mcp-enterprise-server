#!/bin/bash

# ============================================
# 智能进化系统停止脚本
# ============================================

PROJECT_DIR="/Users/mac/Downloads/MCP"

echo "正在停止智能进化编码系统..."

# 停止前端
if [ -f ${PROJECT_DIR}/logs/frontend.pid ]; then
    kill $(cat ${PROJECT_DIR}/logs/frontend.pid) 2>/dev/null
    rm ${PROJECT_DIR}/logs/frontend.pid
    echo "✅ 前端服务已停止"
fi

# 停止WebSocket
if [ -f ${PROJECT_DIR}/logs/websocket.pid ]; then
    kill $(cat ${PROJECT_DIR}/logs/websocket.pid) 2>/dev/null
    rm ${PROJECT_DIR}/logs/websocket.pid
    echo "✅ WebSocket服务已停止"
fi

# 停止API
if [ -f ${PROJECT_DIR}/logs/api.pid ]; then
    kill $(cat ${PROJECT_DIR}/logs/api.pid) 2>/dev/null
    rm ${PROJECT_DIR}/logs/api.pid
    echo "✅ API服务已停止"
fi

# 停止Docker容器
docker-compose -f ${PROJECT_DIR}/docker-compose.yml down
echo "✅ Docker容器已停止"

echo ""
echo "系统已完全停止。"
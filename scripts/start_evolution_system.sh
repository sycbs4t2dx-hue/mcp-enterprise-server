#!/bin/bash

# ============================================
# 智能进化系统快速启动脚本
# ============================================

set -e

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJECT_DIR="/Users/mac/Downloads/MCP"

echo -e "${BLUE}===========================================${NC}"
echo -e "${BLUE}智能进化编码系统 - 快速启动${NC}"
echo -e "${BLUE}===========================================${NC}"
echo ""

# 检查Docker
if ! command -v docker &> /dev/null; then
    echo "请先安装Docker Desktop"
    exit 1
fi

# 启动核心服务
echo -e "${BLUE}[1/5] 启动数据库服务...${NC}"
docker-compose -f ${PROJECT_DIR}/docker-compose.yml up -d mysql redis

echo -e "${BLUE}[2/5] 等待数据库就绪...${NC}"
sleep 10

echo -e "${BLUE}[3/5] 启动API服务...${NC}"
cd ${PROJECT_DIR}
nohup python3 mcp_server_enterprise.py > ${PROJECT_DIR}/logs/api.log 2>&1 &
echo $! > ${PROJECT_DIR}/logs/api.pid

echo -e "${BLUE}[4/5] 启动WebSocket服务...${NC}"
nohup python3 -m src.mcp_core.services.websocket_server > ${PROJECT_DIR}/logs/websocket.log 2>&1 &
echo $! > ${PROJECT_DIR}/logs/websocket.pid

echo -e "${BLUE}[5/5] 启动前端界面...${NC}"
cd ${PROJECT_DIR}/mcp-admin-ui
nohup npm start > ${PROJECT_DIR}/logs/frontend.log 2>&1 &
echo $! > ${PROJECT_DIR}/logs/frontend.pid

echo ""
echo -e "${GREEN}===========================================${NC}"
echo -e "${GREEN}✅ 系统启动成功！${NC}"
echo -e "${GREEN}===========================================${NC}"
echo ""
echo "访问地址:"
echo "  📊 前端界面: http://localhost:3000"
echo "  🚀 API服务: http://localhost:8765"
echo "  🔌 WebSocket: ws://localhost:8766"
echo ""
echo "查看日志:"
echo "  tail -f ${PROJECT_DIR}/logs/api.log"
echo "  tail -f ${PROJECT_DIR}/logs/websocket.log"
echo "  tail -f ${PROJECT_DIR}/logs/frontend.log"
echo ""
echo "停止服务:"
echo "  ${PROJECT_DIR}/scripts/stop_evolution_system.sh"
echo ""
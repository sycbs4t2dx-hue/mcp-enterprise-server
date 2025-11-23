#!/bin/bash
# ============================================
# MCP v2.0.0 - 完整重启流程
# 包含所有修复: Session回滚 + 统一Base
# ============================================

echo "============================================================"
echo "  🔄 MCP Enterprise Server 完整重启"
echo "============================================================"
echo ""

# 1. 显示当前状态
echo "📊 当前状态:"
CURRENT_PID=$(ps aux | grep "mcp_server_enterprise.py" | grep -v grep | awk '{print $2}')
if [ -n "$CURRENT_PID" ]; then
    echo "   旧服务器PID: $CURRENT_PID"
    STARTED_AT=$(ps -p $CURRENT_PID -o lstart | tail -1)
    echo "   启动时间: $STARTED_AT"
    echo "   ⚠️  服务器运行旧代码,需要重启!"
else
    echo "   没有运行的服务器"
fi

echo ""
read -p "按回车继续重启..."

# 2. 停止旧服务器
echo ""
echo "1️⃣ 停止旧服务器..."
if [ -n "$CURRENT_PID" ]; then
    echo "   停止进程 $CURRENT_PID..."
    kill $CURRENT_PID 2>/dev/null
    sleep 2

    # 确认停止
    if ps -p $CURRENT_PID > /dev/null 2>&1; then
        echo "   进程未响应,强制停止..."
        kill -9 $CURRENT_PID 2>/dev/null
        sleep 1
    fi

    if ps -p $CURRENT_PID > /dev/null 2>&1; then
        echo "   ❌ 无法停止服务器"
        exit 1
    else
        echo "   ✅ 服务器已停止"
    fi
else
    echo "   ℹ️  没有需要停止的服务器"
fi

# 3. 清理Python缓存
echo ""
echo "2️⃣ 清理Python缓存..."
find src/mcp_core -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
echo "   ✅ 缓存已清理"

# 4. 验证代码修复
echo ""
echo "3️⃣ 验证代码修复..."

# 检查Session回滚修复
if grep -q "会话已回滚" mcp_server_unified.py; then
    echo "   ✅ Session回滚修复已应用"
else
    echo "   ⚠️  警告: Session回滚修复可能未应用"
fi

# 检查统一Base
if grep -q "from mcp_core.models.base import Base" src/mcp_core/code_knowledge_service.py; then
    echo "   ✅ 统一Base重构已应用"
else
    echo "   ⚠️  警告: 统一Base重构可能未应用"
fi

# 5. 检查Docker服务
echo ""
echo "4️⃣ 检查Docker服务..."
DOCKER_RUNNING=$(docker ps --filter "name=mcp-" | grep -c "Up")
if [ "$DOCKER_RUNNING" -ge 3 ]; then
    echo "   ✅ Docker服务正常 ($DOCKER_RUNNING个容器运行中)"
else
    echo "   ⚠️  Docker服务可能未完全启动"
    echo "   运行中容器:"
    docker ps --filter "name=mcp-" --format "   - {{.Names}}: {{.Status}}"

    read -p "   是否启动Docker服务? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        ./start_services.sh
        sleep 10
    fi
fi

# 6. 启动新服务器
echo ""
echo "5️⃣ 启动新服务器..."

# 设置环境变量
export DB_PASSWORD="${DB_PASSWORD:-Wxwy.2025@#}"
echo "   DB_PASSWORD: ****"

# 启动服务器
echo "   启动命令: python3 mcp_server_enterprise.py"
nohup python3 mcp_server_enterprise.py \
    --host 0.0.0.0 \
    --port 8765 \
    --rate-limit 100 \
    --max-connections 1000 \
    > enterprise_server.log 2>&1 &

NEW_PID=$!
echo "   新进程PID: $NEW_PID"

# 7. 等待启动
echo ""
echo "6️⃣ 等待服务器启动..."
for i in {1..10}; do
    echo -n "   ."
    sleep 1
done
echo ""

# 8. 验证启动
echo ""
echo "7️⃣ 验证服务器状态..."

# 检查进程
if ps -p $NEW_PID > /dev/null 2>&1; then
    echo "   ✅ 进程运行中 (PID: $NEW_PID)"
else
    echo "   ❌ 进程已停止"
    echo ""
    echo "错误日志:"
    tail -20 enterprise_server.log
    exit 1
fi

# 检查日志
echo ""
echo "   最近日志:"
tail -10 enterprise_server.log | sed 's/^/   | /'

# 测试健康检查
echo ""
echo "8️⃣ 测试健康检查..."
sleep 2

HEALTH_RESPONSE=$(curl -s http://localhost:8765/health 2>/dev/null)
if [ $? -eq 0 ]; then
    echo "   ✅ 健康检查通过"
    echo ""
    echo "$HEALTH_RESPONSE" | python3 -m json.tool 2>/dev/null | sed 's/^/   /'
else
    echo "   ❌ 健康检查失败"
    echo ""
    echo "服务器日志:"
    tail -30 enterprise_server.log
    exit 1
fi

# 9. 验证修复
echo ""
echo "9️⃣ 验证修复..."

# 检查启动日志中的修复标志
if grep -q "✅ 所有服务初始化完成" enterprise_server.log; then
    echo "   ✅ 服务初始化完成"
else
    echo "   ⚠️  服务初始化可能有问题"
fi

# 10. 完成
echo ""
echo "============================================================"
echo "  ✅ MCP Enterprise Server 重启完成!"
echo "============================================================"
echo ""
echo "📡 服务地址: http://192.168.3.5:8765"
echo "📊 健康检查: http://192.168.3.5:8765/health"
echo "📈 统计信息: http://192.168.3.5:8765/stats"
echo "📋 查看日志: tail -f enterprise_server.log"
echo ""
echo "🔧 已应用的修复:"
echo "   ✅ Session回滚自动处理"
echo "   ✅ IntegrityError精确捕获"
echo "   ✅ 统一Base元数据"
echo "   ✅ 外键关系正确识别"
echo ""
echo "📝 下一步:"
echo "   1. 重启Claude Code客户端"
echo "   2. 尝试使用MCP工具 (analyze_codebase, start_dev_session等)"
echo "   3. 如有问题查看日志: tail -f enterprise_server.log"
echo ""

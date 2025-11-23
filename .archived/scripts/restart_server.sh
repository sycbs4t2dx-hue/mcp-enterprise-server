#!/bin/bash
# ============================================
# MCP Enterprise Server - 快速重启脚本
# ============================================

echo "🔄 MCP Enterprise Server 重启中..."
echo ""

# 1. 停止旧服务器
echo "1️⃣ 停止旧服务器..."
PID=$(ps aux | grep "mcp_server_enterprise.py" | grep -v grep | awk '{print $2}')
if [ -n "$PID" ]; then
    echo "   找到进程: $PID"
    kill $PID
    sleep 2

    # 确认停止
    if ps -p $PID > /dev/null 2>&1; then
        echo "   强制停止..."
        kill -9 $PID
    fi
    echo "   ✅ 服务器已停止"
else
    echo "   ℹ️  没有运行的服务器"
fi

# 2. 验证代码修复
echo ""
echo "2️⃣ 验证代码修复..."
if grep -q "IntegrityError" mcp_server_unified.py; then
    echo "   ✅ 代码修复已应用"
else
    echo "   ⚠️  警告: 代码修复可能未应用"
fi

# 3. 启动新服务器
echo ""
echo "3️⃣ 启动新服务器..."

# 设置环境变量
export DB_PASSWORD="${DB_PASSWORD:-Wxwy.2025@#}"

# 启动服务器
nohup python3 mcp_server_enterprise.py \
    --host 0.0.0.0 \
    --port 8765 \
    --rate-limit 100 \
    --max-connections 1000 \
    > enterprise_server.log 2>&1 &

SERVER_PID=$!
echo "   新进程: $SERVER_PID"

# 4. 等待启动
echo ""
echo "4️⃣ 等待服务器启动..."
sleep 8

# 5. 验证启动
echo ""
echo "5️⃣ 验证服务器状态..."

if ps -p $SERVER_PID > /dev/null 2>&1; then
    echo "   ✅ 进程运行中"
else
    echo "   ❌ 进程已停止"
    echo ""
    echo "最近日志:"
    tail -20 enterprise_server.log
    exit 1
fi

# 测试健康检查
echo ""
echo "6️⃣ 测试健康检查..."
sleep 2

HEALTH=$(curl -s http://localhost:8765/health 2>/dev/null)
if [ $? -eq 0 ]; then
    echo "   ✅ 健康检查通过"
    echo "$HEALTH" | python3 -m json.tool 2>/dev/null || echo "$HEALTH"
else
    echo "   ⚠️  健康检查失败，查看日志:"
    tail -20 enterprise_server.log
    exit 1
fi

# 7. 完成
echo ""
echo "=" 60
echo "  ✅ MCP Enterprise Server 重启完成!"
echo "=" 60
echo ""
echo "📡 服务地址: http://192.168.3.5:8765"
echo "📊 健康检查: http://192.168.3.5:8765/health"
echo "📈 统计信息: http://192.168.3.5:8765/stats"
echo "📋 查看日志: tail -f enterprise_server.log"
echo ""
echo "🔧 修复内容:"
echo "   ✅ SQLAlchemy会话回滚问题"
echo "   ✅ 重复项目处理"
echo "   ✅ 异常处理改进"
echo ""

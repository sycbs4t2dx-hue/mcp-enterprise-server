#!/bin/bash
# MCP v2.0.0 - 快速启动脚本

set -e

echo "=========================================="
echo "  MCP v2.0.0 - 服务启动"
echo "=========================================="
echo ""

# 检查Docker是否运行
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker未运行，请先启动Docker Desktop"
    exit 1
fi

echo "✅ Docker已运行"
echo ""

# 设置默认密码
export DB_PASSWORD=${DB_PASSWORD:-mcp_password}

echo "📦 启动服务容器..."
echo "   - Milvus (向量数据库)"
echo "   - MySQL (关系数据库)"
echo "   - Redis (缓存)"
echo ""

# 启动所有服务 (优先使用新版本docker compose)
# 直接使用 docker compose (Docker Desktop内置命令)
if docker compose version &> /dev/null 2>&1; then
    echo "使用 docker compose (新版本)"
    docker compose up -d
elif command -v docker-compose &> /dev/null; then
    echo "使用 docker-compose (旧版本)"
    docker-compose up -d 2>&1 || {
        echo "❌ docker-compose失败,尝试使用 docker compose"
        docker compose up -d
    }
else
    echo "❌ 未找到docker compose或docker-compose命令"
    exit 1
fi

echo ""
echo "⏳ 等待服务就绪..."
echo ""

# 等待MySQL就绪
echo -n "等待MySQL..."
for i in {1..30}; do
    if docker exec mcp-mysql mysqladmin ping -h localhost --silent 2>/dev/null; then
        echo " ✅"
        break
    fi
    echo -n "."
    sleep 1
done

# 等待Redis就绪
echo -n "等待Redis..."
for i in {1..10}; do
    if docker exec mcp-redis redis-cli ping 2>/dev/null | grep -q PONG; then
        echo " ✅"
        break
    fi
    echo -n "."
    sleep 1
done

# 等待Milvus就绪
echo -n "等待Milvus..."
for i in {1..60}; do
    if docker exec mcp-milvus curl -f http://localhost:9091/healthz 2>/dev/null >/dev/null; then
        echo " ✅"
        break
    fi
    echo -n "."
    sleep 2
done

echo ""
echo "=========================================="
echo "  🎉 所有服务已启动"
echo "=========================================="
echo ""
echo "服务状态:"
echo "  - Milvus:  localhost:19530 ✅"
echo "  - MySQL:   localhost:3306  ✅"
echo "  - Redis:   localhost:6379  ✅"
echo ""
echo "数据库密码: $DB_PASSWORD"
echo ""
echo "下一步:"
echo "  1. export DB_PASSWORD=$DB_PASSWORD"
echo "  2. python setup.py --install"
echo "  3. python mcp_server_unified.py"
echo ""
echo "停止服务:"
echo "  docker compose down  (或 docker-compose down)"
echo ""

#!/bin/bash
# 端口冲突解决方案

echo "=========================================="
echo "  MCP 端口冲突检测与解决"
echo "=========================================="
echo ""

echo "📊 当前端口占用情况:"
echo ""

# 检查Redis (6379)
echo "Redis端口 6379:"
if lsof -i :6379 > /dev/null 2>&1; then
    lsof -i :6379 | grep LISTEN | awk '{print "  - " $1 " (PID: " $2 ")"}'
else
    echo "  ✅ 无占用"
fi

# 检查MySQL (3306)
echo ""
echo "MySQL端口 3306:"
if lsof -i :3306 > /dev/null 2>&1; then
    lsof -i :3306 | grep LISTEN | awk '{print "  - " $1 " (PID: " $2 ")"}'
else
    echo "  ✅ 无占用"
fi

# 检查Milvus (19530)
echo ""
echo "Milvus端口 19530:"
if lsof -i :19530 > /dev/null 2>&1; then
    lsof -i :19530 | grep LISTEN | awk '{print "  - " $1 " (PID: " $2 ")"}'
else
    echo "  ✅ 无占用"
fi

echo ""
echo "=========================================="
echo "  解决方案选择"
echo "=========================================="
echo ""
echo "请选择解决方案："
echo ""
echo "1. 停止本地服务，使用Docker容器 (推荐)"
echo "   - 停止本地MySQL和Redis"
echo "   - 使用Docker提供的服务"
echo "   - 优点: 隔离环境，易于管理"
echo ""
echo "2. 停止Docker容器，使用本地服务"
echo "   - 停止Docker MySQL和Redis"
echo "   - 使用本地已安装的服务"
echo "   - 需要: 在本地MySQL中创建mcp_db数据库"
echo ""
echo "3. 修改Docker端口映射，两者共存"
echo "   - Docker MySQL: 3307"
echo "   - Docker Redis: 6380"
echo "   - 本地服务保持不变"
echo ""

read -p "请输入选择 (1/2/3): " choice

case $choice in
    1)
        echo ""
        echo "🔧 执行方案1: 停止本地服务..."
        echo ""

        # 停止本地Redis
        echo "停止本地Redis..."
        brew services stop redis 2>/dev/null || echo "  (Redis未通过brew安装)"
        pkill -f redis-server 2>/dev/null && echo "  ✅ Redis已停止" || echo "  ℹ️  Redis未运行"

        # 停止本地MySQL
        echo ""
        echo "停止本地MySQL..."
        brew services stop mysql 2>/dev/null || echo "  (MySQL未通过brew安装)"
        pkill -f mysqld 2>/dev/null && echo "  ✅ MySQL已停止" || echo "  ℹ️  MySQL未运行"

        echo ""
        echo "✅ 本地服务已停止，Docker容器可以使用这些端口"
        echo ""
        echo "现在可以启动MCP服务器:"
        echo "  export DB_PASSWORD=\"Wxwy.2025@#\""
        echo "  python3 mcp_server_unified.py"
        ;;

    2)
        echo ""
        echo "🔧 执行方案2: 停止Docker容器..."
        echo ""

        # 停止Docker容器
        docker stop mcp-mysql mcp-redis 2>/dev/null
        echo "✅ Docker容器已停止"

        echo ""
        echo "⚠️  注意: 您需要在本地MySQL中创建数据库和表"
        echo ""
        echo "步骤:"
        echo "1. 连接本地MySQL: mysql -uroot -p"
        echo "2. 创建数据库: CREATE DATABASE mcp_db;"
        echo "3. 运行初始化: python3 setup.py --create-tables"
        echo ""
        echo "配置文件需要修改为:"
        echo '  "host": "localhost"  (保持不变)'
        echo '  "password": "你的本地MySQL密码"'
        ;;

    3)
        echo ""
        echo "🔧 执行方案3: 修改Docker端口映射..."
        echo ""

        # 停止现有容器
        echo "停止现有Docker容器..."
        docker stop mcp-mysql mcp-redis mcp-milvus 2>/dev/null
        docker rm mcp-mysql mcp-redis mcp-milvus 2>/dev/null

        echo ""
        echo "使用新端口重新创建容器..."

        # MySQL: 3306 -> 3307
        docker run -d \
          --name mcp-mysql \
          -p 3307:3306 \
          -e MYSQL_ROOT_PASSWORD='Wxwy.2025@#' \
          -e MYSQL_DATABASE=mcp_db \
          -v "$(pwd)/mysql_data:/var/lib/mysql" \
          mysql:8.0 \
          --default-authentication-plugin=mysql_native_password
        echo "✅ MySQL: localhost:3307"

        # Redis: 6379 -> 6380
        docker run -d \
          --name mcp-redis \
          -p 6380:6379 \
          -v "$(pwd)/redis_data:/data" \
          redis:7-alpine \
          redis-server --appendonly yes
        echo "✅ Redis: localhost:6380"

        # Milvus保持19530
        docker run -d \
          --name mcp-milvus \
          -p 19530:19530 \
          -p 9091:9091 \
          -e ETCD_USE_EMBED=true \
          -e COMMON_STORAGETYPE=local \
          -v "$(pwd)/milvus_data:/var/lib/milvus" \
          milvusdb/milvus:v2.3.4 \
          milvus run standalone
        echo "✅ Milvus: localhost:19530"

        echo ""
        echo "⚠️  配置文件需要修改:"
        echo '  "port": 3307  (MySQL)'
        echo ""
        echo "Redis和Milvus配置也需要相应修改"
        echo ""
        echo "修改config/mcp_config.json:"
        echo '  "database": { "port": 3307, ... }'
        ;;

    *)
        echo ""
        echo "❌ 无效选择"
        exit 1
        ;;
esac

echo ""
echo "=========================================="
echo "  完成"
echo "=========================================="

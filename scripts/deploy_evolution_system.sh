#!/bin/bash

# ============================================
# 智能进化系统完整部署脚本
# ============================================

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置变量
PROJECT_NAME="evolution_system"
PROJECT_DIR="/Users/mac/Downloads/MCP"
BACKUP_DIR="${PROJECT_DIR}/backups"
LOG_DIR="${PROJECT_DIR}/logs"
DATA_DIR="${PROJECT_DIR}/data"
MODELS_DIR="${PROJECT_DIR}/models"
CONFIG_FILE="${PROJECT_DIR}/config/evolution_config.yaml"

# 环境变量
export ENVIRONMENT=${1:-production}
export DB_PASSWORD="Wxwy.2025@#"
export REDIS_PASSWORD=""
export JWT_SECRET=$(openssl rand -base64 32)

# ============================================
# 工具函数
# ============================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

check_command() {
    if ! command -v $1 &> /dev/null; then
        log_error "$1 未安装，请先安装 $1"
    fi
}

create_directories() {
    log_info "创建必要目录..."

    mkdir -p ${BACKUP_DIR}
    mkdir -p ${LOG_DIR}
    mkdir -p ${DATA_DIR}
    mkdir -p ${MODELS_DIR}
    mkdir -p ${PROJECT_DIR}/config

    log_success "目录创建完成"
}

# ============================================
# 环境检查
# ============================================

check_environment() {
    log_info "检查系统环境..."

    # 检查必要命令
    check_command docker
    check_command docker-compose
    check_command python3
    check_command npm
    check_command git
    check_command mysql

    # 检查Python版本
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
    REQUIRED_VERSION="3.9"

    if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
        log_error "Python版本需要 >= $REQUIRED_VERSION，当前版本: $PYTHON_VERSION"
    fi

    # 检查Node版本
    NODE_VERSION=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
    if [ "$NODE_VERSION" -lt 14 ]; then
        log_error "Node.js版本需要 >= 14，当前版本: $NODE_VERSION"
    fi

    log_success "环境检查通过"
}

# ============================================
# 备份功能
# ============================================

backup_system() {
    log_info "备份现有系统..."

    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_PATH="${BACKUP_DIR}/backup_${TIMESTAMP}"
    mkdir -p ${BACKUP_PATH}

    # 备份数据库
    if docker ps | grep -q evolution_mysql; then
        log_info "备份数据库..."
        docker exec evolution_mysql mysqldump -u root -p${DB_PASSWORD} mcp_evolution > ${BACKUP_PATH}/database.sql
    fi

    # 备份配置文件
    if [ -d "${PROJECT_DIR}/config" ]; then
        cp -r ${PROJECT_DIR}/config ${BACKUP_PATH}/
    fi

    # 备份数据目录
    if [ -d "${DATA_DIR}" ]; then
        tar -czf ${BACKUP_PATH}/data.tar.gz -C ${DATA_DIR} .
    fi

    log_success "备份完成: ${BACKUP_PATH}"
}

# ============================================
# 依赖安装
# ============================================

install_dependencies() {
    log_info "安装系统依赖..."

    # Python依赖
    log_info "安装Python依赖..."
    cd ${PROJECT_DIR}

    # 创建虚拟环境
    if [ ! -d "venv" ]; then
        python3 -m venv venv
    fi

    # 激活虚拟环境并安装依赖
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt

    # 前端依赖
    log_info "安装前端依赖..."
    cd ${PROJECT_DIR}/mcp-admin-ui
    npm install

    log_success "依赖安装完成"
}

# ============================================
# 数据库初始化
# ============================================

init_database() {
    log_info "初始化数据库..."

    # 等待MySQL启动
    log_info "等待MySQL服务启动..."
    for i in {1..30}; do
        if docker exec evolution_mysql mysql -u root -p${DB_PASSWORD} -e "SELECT 1" &> /dev/null; then
            break
        fi
        sleep 2
    done

    # 创建数据库
    docker exec evolution_mysql mysql -u root -p${DB_PASSWORD} -e "CREATE DATABASE IF NOT EXISTS mcp_evolution;"

    # 执行数据库脚本
    log_info "执行数据库初始化脚本..."
    docker exec -i evolution_mysql mysql -u root -p${DB_PASSWORD} mcp_evolution < ${PROJECT_DIR}/scripts/create_evolution_tables.sql
    docker exec -i evolution_mysql mysql -u root -p${DB_PASSWORD} mcp_evolution < ${PROJECT_DIR}/scripts/create_error_firewall_schema.sql

    log_success "数据库初始化完成"
}

# ============================================
# 模型下载
# ============================================

download_models() {
    log_info "下载AI模型..."

    cd ${PROJECT_DIR}
    source venv/bin/activate

    # 下载嵌入模型
    python3 scripts/download_models.py

    log_success "模型下载完成"
}

# ============================================
# Docker部署
# ============================================

deploy_docker() {
    log_info "启动Docker容器..."

    cd ${PROJECT_DIR}

    # 停止旧容器
    if docker-compose -f docker-compose.evolution.yml ps | grep -q Up; then
        log_info "停止旧容器..."
        docker-compose -f docker-compose.evolution.yml down
    fi

    # 构建镜像
    log_info "构建Docker镜像..."
    docker-compose -f docker-compose.evolution.yml build

    # 启动容器
    log_info "启动容器..."
    docker-compose -f docker-compose.evolution.yml up -d

    # 等待服务启动
    log_info "等待服务启动..."
    sleep 10

    # 检查服务状态
    check_services

    log_success "Docker部署完成"
}

# ============================================
# 服务检查
# ============================================

check_services() {
    log_info "检查服务状态..."

    SERVICES=(
        "evolution_mysql:3306"
        "evolution_redis:6379"
        "evolution_api:8765"
        "evolution_websocket:8766"
        "evolution_frontend:3000"
    )

    for service in "${SERVICES[@]}"; do
        IFS=':' read -r container port <<< "$service"
        if docker ps | grep -q $container; then
            log_success "$container 运行中 (端口: $port)"
        else
            log_error "$container 未运行"
        fi
    done

    # 检查API健康状态
    if curl -s http://localhost:8765/health > /dev/null; then
        log_success "API服务健康检查通过"
    else
        log_warning "API服务健康检查失败"
    fi
}

# ============================================
# 加载预置数据
# ============================================

load_preset_data() {
    log_info "加载预置模式库..."

    cd ${PROJECT_DIR}
    source venv/bin/activate

    # 生成预置模式
    python3 -c "
from src.mcp_core.data.preset_patterns import export_patterns_to_json, load_patterns_to_database
export_patterns_to_json('${DATA_DIR}/preset_patterns.json')
load_patterns_to_database()
"

    log_success "预置数据加载完成"
}

# ============================================
# 运行测试
# ============================================

run_tests() {
    log_info "运行系统测试..."

    cd ${PROJECT_DIR}
    source venv/bin/activate

    # 运行单元测试
    python3 tests/test_evolution_framework.py

    # 运行集成测试
    python3 tests/test_evolution_system.py

    log_success "测试完成"
}

# ============================================
# 配置Nginx
# ============================================

configure_nginx() {
    log_info "配置Nginx反向代理..."

    # 创建Nginx配置
    cat > ${PROJECT_DIR}/config/nginx/sites/evolution.conf << 'EOF'
upstream api_backend {
    server localhost:8765;
}

upstream websocket_backend {
    server localhost:8766;
}

server {
    listen 80;
    server_name localhost;

    # 前端
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # API
    location /api/ {
        proxy_pass http://api_backend/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket
    location /ws/ {
        proxy_pass http://websocket_backend/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
EOF

    log_success "Nginx配置完成"
}

# ============================================
# 系统监控
# ============================================

setup_monitoring() {
    log_info "设置系统监控..."

    # Prometheus配置
    cat > ${PROJECT_DIR}/config/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'evolution_system'
    static_configs:
      - targets: ['localhost:8765', 'localhost:8766']
EOF

    # 启动监控服务
    if ! docker ps | grep -q evolution_prometheus; then
        docker run -d \
            --name evolution_prometheus \
            -p 9090:9090 \
            -v ${PROJECT_DIR}/config/prometheus.yml:/etc/prometheus/prometheus.yml \
            prom/prometheus
    fi

    log_success "监控设置完成"
}

# ============================================
# 清理功能
# ============================================

cleanup() {
    log_info "清理系统..."

    # 停止所有容器
    docker-compose -f docker-compose.evolution.yml down

    # 清理未使用的镜像
    docker image prune -f

    # 清理日志
    find ${LOG_DIR} -name "*.log" -mtime +7 -delete

    log_success "清理完成"
}

# ============================================
# 显示信息
# ============================================

show_info() {
    echo ""
    echo "============================================"
    echo "智能进化编码系统部署完成！"
    echo "============================================"
    echo ""
    echo "访问地址:"
    echo "  - 前端界面: http://localhost:3000"
    echo "  - API文档: http://localhost:8765/docs"
    echo "  - WebSocket: ws://localhost:8766"
    echo "  - Prometheus: http://localhost:9090"
    echo "  - Grafana: http://localhost:3001 (admin/admin)"
    echo ""
    echo "服务状态:"
    docker-compose -f docker-compose.evolution.yml ps
    echo ""
    echo "查看日志:"
    echo "  docker-compose -f docker-compose.evolution.yml logs -f"
    echo ""
    echo "停止服务:"
    echo "  docker-compose -f docker-compose.evolution.yml down"
    echo ""
}

# ============================================
# 主函数
# ============================================

main() {
    echo "============================================"
    echo "智能进化编码系统部署脚本"
    echo "环境: ${ENVIRONMENT}"
    echo "============================================"
    echo ""

    # 环境检查
    check_environment

    # 创建目录
    create_directories

    # 备份
    if [ "$2" == "--backup" ]; then
        backup_system
    fi

    # 安装依赖
    install_dependencies

    # Docker部署
    deploy_docker

    # 初始化数据库
    init_database

    # 下载模型
    if [ "$2" == "--with-models" ]; then
        download_models
    fi

    # 加载预置数据
    load_preset_data

    # 配置Nginx
    configure_nginx

    # 设置监控
    if [ "$ENVIRONMENT" == "production" ]; then
        setup_monitoring
    fi

    # 运行测试
    if [ "$2" == "--test" ]; then
        run_tests
    fi

    # 显示信息
    show_info

    log_success "部署完成！"
}

# 执行主函数
main "$@"
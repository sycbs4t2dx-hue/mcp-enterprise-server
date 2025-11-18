#!/bin/bash
#
# MCP项目依赖安装脚本
# 用法: ./install_dependencies.sh
#

echo "======================================"
echo "MCP项目依赖安装"
echo "======================================"
echo ""

# 更新pip
echo "1. 更新pip..."
python3 -m pip install --upgrade pip

echo ""
echo "2. 安装核心依赖..."
pip3 install \
    'fastapi>=0.108.0' \
    'uvicorn[standard]>=0.25.0' \
    'pydantic>=2.5.0' \
    'pydantic-settings>=2.1.0' \
    'sqlalchemy>=2.0.23' \
    'alembic>=1.13.0'

echo ""
echo "3. 安装数据库驱动..."
pip3 install \
    'pymysql>=1.1.0' \
    'cryptography>=41.0.0'

echo ""
echo "4. 安装Redis..."
pip3 install 'redis>=5.0.1'

echo ""
echo "5. 安装Milvus..."
pip3 install 'pymilvus>=2.3.4'

echo ""
echo "6. 安装机器学习库..."
pip3 install \
    'sentence-transformers>=2.2.2' \
    'torch>=2.1.0' \
    'transformers>=4.36.0' \
    'numpy>=1.24.0' \
    'scikit-learn>=1.3.0'

echo ""
echo "7. 安装其他依赖..."
pip3 install \
    'pyyaml>=6.0.1' \
    'httpx>=0.27.0' \
    'python-jose[cryptography]>=3.3.0' \
    'passlib[bcrypt]>=1.7.4' \
    'prometheus-client>=0.19.0' \
    'python-multipart>=0.0.6'

echo ""
echo "======================================"
echo "依赖安装完成!"
echo "======================================"
echo ""
echo "验证安装:"
python3 -c "from src.mcp_core.main import app; print('✓ 应用导入成功!')"

echo ""
echo "下一步: 运行 ./start.sh 启动服务"

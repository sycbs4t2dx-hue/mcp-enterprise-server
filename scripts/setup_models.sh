#!/bin/bash
# Hugging Face模型快速设置脚本
# 用途: 一键下载和配置所有必需的模型

set -e  # 遇到错误立即退出

echo "╔══════════════════════════════════════════════════════════╗"
echo "║   Hugging Face 模型快速设置                               ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到python3"
    exit 1
fi

# 检查依赖
echo "📦 检查依赖..."
pip3 list | grep -q "PyYAML" || pip3 install PyYAML
pip3 list | grep -q "requests" || pip3 install requests
pip3 list | grep -q "tqdm" || pip3 install tqdm
echo "✅ 依赖完整"
echo ""

# 创建models目录
echo "📁 创建models目录..."
mkdir -p models
echo "✅ 目录创建完成: ./models"
echo ""

# 列出模型
echo "📋 可用模型列表:"
python3 scripts/download_models.py --list
echo ""

# 询问用户是否下载
read -p "是否下载所有模型? (y/n) [默认: y]: " DOWNLOAD
DOWNLOAD=${DOWNLOAD:-y}

if [[ "$DOWNLOAD" =~ ^[Yy]$ ]]; then
    # 询问是否使用镜像
    read -p "是否使用国内镜像加速? (y/n) [默认: y]: " MIRROR
    MIRROR=${MIRROR:-y}

    MIRROR_FLAG=""
    if [[ "$MIRROR" =~ ^[Yy]$ ]]; then
        MIRROR_FLAG="--mirror"
        echo ""
        echo "🌍 将使用Hugging Face镜像站: https://hf-mirror.com"
    fi

    echo ""
    echo "⏬ 开始下载模型..."
    echo ""

    # 下载所有模型
    if python3 scripts/download_models.py --download all $MIRROR_FLAG; then
        echo ""
        echo "✅ 模型下载成功!"
    else
        echo ""
        echo "❌ 模型下载失败,请检查网络连接"
        exit 1
    fi
else
    echo "ℹ️  跳过下载,您可以稍后手动下载"
    echo "   命令: python3 scripts/download_models.py --download all"
fi

echo ""
echo "🔍 验证模型文件..."
python3 scripts/download_models.py --validate all

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║   ✅ 设置完成!                                            ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "📝 后续步骤:"
echo ""
echo "1. 启动MCP服务器:"
echo "   export DB_PASSWORD=\"Wxwy.2025@#\""
echo "   python3 mcp_server_enterprise.py"
echo ""
echo "2. 查看日志确认使用本地模型:"
echo "   应显示: ✅ 使用本地模型: ./models/all-MiniLM-L6-v2"
echo ""
echo "3. 如需重新下载:"
echo "   python3 scripts/download_models.py --download all --force"
echo ""
echo "📖 详细文档: docs/HUGGINGFACE_MODEL_SETUP.md"

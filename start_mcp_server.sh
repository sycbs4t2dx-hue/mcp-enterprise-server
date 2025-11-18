#!/bin/bash
#
# MCP服务端启动脚本
# 用于被Claude Desktop或其他MCP客户端调用
#

# 切换到项目目录
cd "$(dirname "$0")"

# 激活虚拟环境（如果使用）
# source venv/bin/activate

# 确保日志目录存在
mkdir -p logs

# 启动MCP服务端
exec python3 -m src.mcp_core.mcp_server

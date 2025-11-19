#!/usr/bin/env python3
"""
MCP SSE服务器 - 通过HTTP SSE提供MCP服务
兼容Claude Code CLI的远程MCP配置
"""

import json
import asyncio
from typing import Dict, Optional
from aiohttp import web
import aiohttp_cors
from datetime import datetime
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_server_unified import UnifiedMCPServer


class MCPSSEServer:
    """MCP SSE服务器 - 提供基于HTTP SSE的MCP协议"""

    def __init__(self, host: str = "0.0.0.0", port: int = 8765, config_file: Optional[str] = None):
        self.host = host
        self.port = port
        self.mcp_server = UnifiedMCPServer(config_file)
        self.app = web.Application()
        self._setup_routes()

    def _setup_routes(self):
        """设置路由"""
        # MCP SSE端点
        self.app.router.add_get('/sse', self.handle_sse)
        self.app.router.add_post('/message', self.handle_message)

        # 信息端点
        self.app.router.add_get('/health', self.handle_health)
        self.app.router.add_get('/', self.handle_index)

        # 配置CORS
        cors = aiohttp_cors.setup(self.app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods="*"
            )
        })

        for route in list(self.app.router.routes()):
            cors.add(route)

    async def handle_index(self, request):
        """首页 - 显示配置信息"""
        server_url = f"http://{request.host}"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>MCP SSE服务器 v2.0.0</title>
            <meta charset="utf-8">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                    max-width: 1000px;
                    margin: 50px auto;
                    padding: 20px;
                    background: #f5f5f5;
                }}
                .container {{
                    background: white;
                    padding: 40px;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
                h2 {{ color: #34495e; margin-top: 30px; }}
                .status {{
                    padding: 20px;
                    background: #d4edda;
                    border-left: 4px solid #28a745;
                    margin: 20px 0;
                    border-radius: 5px;
                }}
                .config-box {{
                    background: #2c3e50;
                    color: #ecf0f1;
                    padding: 20px;
                    border-radius: 5px;
                    margin: 20px 0;
                    font-family: 'Monaco', 'Courier New', monospace;
                    overflow-x: auto;
                }}
                .highlight {{
                    background: #f39c12;
                    color: white;
                    padding: 2px 8px;
                    border-radius: 3px;
                    font-weight: bold;
                }}
                .info-box {{
                    background: #e8f4f8;
                    border-left: 4px solid #3498db;
                    padding: 15px;
                    margin: 15px 0;
                    border-radius: 5px;
                }}
                code {{
                    background: #ecf0f1;
                    padding: 2px 6px;
                    border-radius: 3px;
                    font-family: 'Monaco', 'Courier New', monospace;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🚀 MCP SSE服务器 v2.0.0</h1>

                <div class="status">
                    <strong>✅ 服务器运行中</strong><br>
                    服务器地址: <span class="highlight">{server_url}</span><br>
                    MCP协议: 2024-11-05<br>
                    可用工具: 37个<br>
                    通信方式: SSE (Server-Sent Events)
                </div>

                <h2>👥 同事配置（Claude Code CLI）</h2>

                <div class="info-box">
                    <strong>配置文件位置：</strong>
                    <ul>
                        <li>macOS/Linux: <code>~/.config/claude/claude_desktop_config.json</code></li>
                        <li>Windows: <code>%APPDATA%\\Claude\\claude_desktop_config.json</code></li>
                    </ul>
                </div>

                <p><strong>配置内容（复制粘贴即可）：</strong></p>
                <div class="config-box">{{
  "mcpServers": {{
    "mcp-remote": {{
      "url": "{server_url}/sse"
    }}
  }}
}}</div>

                <h2>🔧 可用工具（37个）</h2>
                <ul>
                    <li><strong>基础记忆</strong> (2个): store_memory, retrieve_memory</li>
                    <li><strong>代码分析</strong> (8个): analyze_codebase, query_architecture, find_entity, ...</li>
                    <li><strong>项目上下文</strong> (12个): start_dev_session, create_todo, record_design_decision, ...</li>
                    <li><strong>AI辅助</strong> (7个): ai_understand_function, ai_suggest_next_steps, ...</li>
                    <li><strong>质量守护</strong> (8个): detect_code_smells, assess_technical_debt, ...</li>
                </ul>

                <h2>✅ 使用步骤</h2>
                <ol>
                    <li>将上面的JSON配置复制到配置文件中</li>
                    <li>保存配置文件</li>
                    <li>重启Claude Code CLI</li>
                    <li>开始使用37个MCP工具！</li>
                </ol>

                <h2>🧪 测试连接</h2>
                <p>健康检查: <a href="/health">{server_url}/health</a></p>
                <p>SSE端点: <a href="/sse">{server_url}/sse</a></p>

                <h2>📋 架构说明</h2>
                <pre style="background: #ecf0f1; padding: 15px; border-radius: 5px;">
同事的Claude Code CLI
    ↓ (HTTP SSE)
{server_url}/sse
    ↓
MCP统一服务器 (37个工具)
    ↓
Docker服务 (MySQL/Redis/Milvus)</pre>

                <h2>ℹ️ 技术信息</h2>
                <ul>
                    <li><strong>协议</strong>: MCP over SSE</li>
                    <li><strong>传输</strong>: HTTP Server-Sent Events</li>
                    <li><strong>端口</strong>: {request.host.split(':')[1] if ':' in request.host else '80'}</li>
                    <li><strong>CORS</strong>: 已启用</li>
                </ul>

            </div>
        </body>
        </html>
        """
        return web.Response(text=html, content_type='text/html')

    async def handle_health(self, request):
        """健康检查"""
        return web.json_response({
            "status": "healthy",
            "version": "v2.0.0",
            "protocol": "MCP-SSE",
            "tools_count": len(self.mcp_server.get_all_tools()),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })

    async def handle_sse(self, request):
        """SSE端点 - 处理MCP连接"""
        response = web.StreamResponse()
        response.headers['Content-Type'] = 'text/event-stream'
        response.headers['Cache-Control'] = 'no-cache'
        response.headers['Connection'] = 'keep-alive'
        response.headers['X-Accel-Buffering'] = 'no'

        await response.prepare(request)

        try:
            # SSE endpoint只负责响应客户端的请求
            # 不主动发送消息，等待客户端通过POST /message发送请求

            # 保持连接并发送心跳
            while True:
                await asyncio.sleep(15)
                # 发送SSE心跳（注释格式，不会被解析）
                await response.write(b": ping\n\n")

        except asyncio.CancelledError:
            print("SSE连接关闭")
        except Exception as e:
            print(f"SSE错误: {e}")

        return response

    async def handle_message(self, request):
        """处理JSON-RPC消息"""
        try:
            json_request = await request.json()
            response = self.mcp_server.handle_request(json_request)
            return web.json_response(response)

        except Exception as e:
            return web.json_response({
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            }, status=500)

    def run(self):
        """启动服务器"""
        print(f"")
        print(f"{'='*60}")
        print(f"  🚀 MCP SSE服务器 v2.0.0")
        print(f"{'='*60}")
        print(f"")
        print(f"📡 监听地址: http://{self.host}:{self.port}")
        print(f"🌐 局域网地址: http://192.168.1.34:{self.port}")
        print(f"🔧 工具数量: {len(self.mcp_server.get_all_tools())}")
        print(f"")
        print(f"📋 同事配置（复制到Claude Code配置文件）:")
        print(f"")
        print(f'{{')
        print(f'  "mcpServers": {{')
        print(f'    "mcp-remote": {{')
        print(f'      "url": "http://192.168.1.34:{self.port}/sse"')
        print(f'    }}')
        print(f'  }}')
        print(f'}}')
        print(f"")
        print(f"🌐 浏览器访问: http://192.168.1.34:{self.port}")
        print(f"")
        print(f"{'='*60}")
        print(f"")

        web.run_app(self.app, host=self.host, port=self.port, print=lambda x: None)


def main():
    import argparse

    parser = argparse.ArgumentParser(description='MCP SSE服务器')
    parser.add_argument('--host', default='0.0.0.0', help='监听地址')
    parser.add_argument('--port', type=int, default=8765, help='监听端口')
    parser.add_argument('--config', help='配置文件路径')

    args = parser.parse_args()

    server = MCPSSEServer(
        host=args.host,
        port=args.port,
        config_file=args.config
    )

    server.run()


if __name__ == '__main__':
    main()

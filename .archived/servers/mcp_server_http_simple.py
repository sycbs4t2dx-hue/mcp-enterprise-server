#!/usr/bin/env python3
"""
MCP标准HTTP服务器 - 符合MCP规范
支持streamable和sse两种传输方式
"""

import json
import asyncio
from typing import Dict, Optional, Any
from aiohttp import web
import aiohttp_cors
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcp_server_unified import UnifiedMCPServer


class MCPStandardServer:
    """MCP标准HTTP服务器"""

    def __init__(self, host: str = "0.0.0.0", port: int = 8765, config_file: Optional[str] = None):
        self.host = host
        self.port = port
        self.mcp_server = UnifiedMCPServer(config_file)
        self.app = web.Application()
        self._setup_routes()

    def _setup_routes(self):
        """设置路由"""
        # 根路径处理所有MCP请求
        self.app.router.add_post('/', self.handle_mcp_request)

        # 信息端点
        self.app.router.add_get('/health', self.handle_health)
        self.app.router.add_get('/info', self.handle_info)

        # CORS
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

    async def handle_info(self, request):
        """信息页面"""
        server_url = f"http://{request.host}"
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>MCP服务器 v2.0.0</title>
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
            font-family: 'Monaco', monospace;
        }}
        .highlight {{ background: #f39c12; color: white; padding: 2px 8px; border-radius: 3px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 MCP服务器 v2.0.0</h1>
        <div class="status">
            <strong>✅ 服务器运行中</strong><br>
            地址: <span class="highlight">{server_url}</span><br>
            工具数量: 37个
        </div>

        <h2>📋 Claude Code配置</h2>
        <p><strong>方式1：stdio (推荐用于本机)</strong></p>
        <div class="config-box">{{
  "mcpServers": {{
    "mcp-local": {{
      "command": "python3",
      "args": ["/Users/mac/Downloads/MCP/mcp_server_unified.py"],
      "env": {{
        "DB_PASSWORD": "Wxwy.2025@#"
      }}
    }}
  }}
}}</div>

        <p><strong>方式2：HTTP (用于局域网)</strong></p>
        <div class="config-box">{{
  "mcpServers": {{
    "mcp-remote": {{
      "url": "{server_url}"
    }}
  }}
}}</div>

        <h2>🔧 可用工具（37个）</h2>
        <ul>
            <li>基础记忆 (2): store_memory, retrieve_memory</li>
            <li>代码分析 (8): analyze_codebase, ...</li>
            <li>项目上下文 (12): start_dev_session, ...</li>
            <li>AI辅助 (7): ai_understand_function, ...</li>
            <li>质量守护 (8): detect_code_smells, ...</li>
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
            "tools_count": len(self.mcp_server.get_all_tools()),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })

    async def handle_mcp_request(self, request):
        """处理MCP请求 - streamable方式"""
        try:
            # 解析JSON-RPC请求
            json_request = await request.json()

            method = json_request.get('method', 'unknown')
            request_id = json_request.get('id', 'N/A')

            print(f"[MCP] 请求 [ID:{request_id}]: {method}")

            # 调用MCP服务器处理
            mcp_response = self.mcp_server.handle_request(json_request)

            print(f"[MCP] 响应 [ID:{request_id}]: OK")

            # 直接返回JSON响应
            return web.json_response(mcp_response)

        except json.JSONDecodeError as e:
            print(f"[MCP] JSON解析错误: {e}")
            return web.json_response({
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32700,
                    "message": "Parse error"
                }
            }, status=400)

        except Exception as e:
            print(f"[MCP] 错误: {e}")
            import traceback
            traceback.print_exc()
            return web.json_response({
                "jsonrpc": "2.0",
                "id": json_request.get('id') if 'json_request' in locals() else None,
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            }, status=500)

    def run(self):
        """启动服务器"""
        print(f"")
        print(f"{'='*60}")
        print(f"  🚀 MCP HTTP服务器 v2.0.0")
        print(f"{'='*60}")
        print(f"")
        print(f"📡 监听地址: http://{self.host}:{self.port}")
        print(f"🌐 局域网地址: http://192.168.3.5:{self.port}")
        print(f"🔧 工具数量: {len(self.mcp_server.get_all_tools())}")
        print(f"")
        print(f"📋 Claude Code配置:")
        print(f"")
        print(f'{{')
        print(f'  "mcpServers": {{')
        print(f'    "mcp-remote": {{')
        print(f'      "url": "http://192.168.3.5:{self.port}"')
        print(f'    }}')
        print(f'  }}')
        print(f'}}')
        print(f"")
        print(f"🌐 浏览器访问: http://192.168.3.5:{self.port}/info")
        print(f"")
        print(f"{'='*60}")
        print(f"")

        web.run_app(self.app, host=self.host, port=self.port, print=lambda x: None)


def main():
    import argparse

    parser = argparse.ArgumentParser(description='MCP标准HTTP服务器')
    parser.add_argument('--host', default='0.0.0.0', help='监听地址')
    parser.add_argument('--port', type=int, default=8765, help='监听端口')
    parser.add_argument('--config', help='配置文件路径')

    args = parser.parse_args()

    server = MCPStandardServer(
        host=args.host,
        port=args.port,
        config_file=args.config
    )

    server.run()


if __name__ == '__main__':
    main()

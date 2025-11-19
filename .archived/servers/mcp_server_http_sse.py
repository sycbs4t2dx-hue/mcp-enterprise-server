#!/usr/bin/env python3
"""
MCP HTTP+SSE服务器 - 符合MCP协议规范
支持Claude Code CLI远程连接
"""

import json
import asyncio
from typing import Dict, Optional
from aiohttp import web
import aiohttp_cors
from datetime import datetime
import sys
import os
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcp_server_unified import UnifiedMCPServer


class MCPHTTPSSEServer:
    """MCP HTTP+SSE服务器"""

    def __init__(self, host: str = "0.0.0.0", port: int = 8765, config_file: Optional[str] = None):
        self.host = host
        self.port = port
        self.mcp_server = UnifiedMCPServer(config_file)
        self.app = web.Application()
        self.active_connections = {}
        self._setup_routes()

    def _setup_routes(self):
        """设置路由"""
        # MCP端点 - 根路径用于SSE
        self.app.router.add_get('/', self.handle_sse)
        self.app.router.add_post('/', self.handle_post_message)

        # 备用端点
        self.app.router.add_get('/sse', self.handle_sse)
        self.app.router.add_post('/messages', self.handle_post_message)

        # 信息端点
        self.app.router.add_get('/health', self.handle_health)
        self.app.router.add_get('/info', self.handle_index)

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

    async def handle_index(self, request):
        """首页"""
        server_url = f"http://{request.host}"
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>MCP HTTP服务器 v2.0.0</title>
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
            font-family: 'Monaco', 'Courier New', monospace;
        }}
        .highlight {{
            background: #f39c12;
            color: white;
            padding: 2px 8px;
            border-radius: 3px;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 MCP HTTP服务器 v2.0.0</h1>

        <div class="status">
            <strong>✅ 服务器运行中</strong><br>
            服务器地址: <span class="highlight">{server_url}</span><br>
            MCP协议: 2024-11-05<br>
            可用工具: 37个
        </div>

        <h2>👥 Claude Code配置</h2>
        <p><strong>配置文件位置：</strong></p>
        <ul>
            <li>macOS/Linux: <code>~/.config/claude/claude_desktop_config.json</code></li>
            <li>Windows: <code>%APPDATA%\\Claude\\claude_desktop_config.json</code></li>
        </ul>

        <p><strong>配置内容：</strong></p>
        <div class="config-box">{{
  "mcpServers": {{
    "mcp-remote": {{
      "url": "{server_url}",
      "transport": "sse"
    }}
  }}
}}</div>

        <h2>🔧 可用工具（37个）</h2>
        <ul>
            <li><strong>基础记忆</strong> (2个): store_memory, retrieve_memory</li>
            <li><strong>代码分析</strong> (8个): analyze_codebase, query_architecture, ...</li>
            <li><strong>项目上下文</strong> (12个): start_dev_session, create_todo, ...</li>
            <li><strong>AI辅助</strong> (7个): ai_understand_function, ai_suggest_next_steps, ...</li>
            <li><strong>质量守护</strong> (8个): detect_code_smells, assess_technical_debt, ...</li>
        </ul>

        <h2>📡 端点</h2>
        <ul>
            <li>健康检查: <a href="/health">/health</a></li>
            <li>SSE连接: <a href="/sse">/sse</a></li>
            <li>消息POST: /messages</li>
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
            "protocol": "MCP",
            "tools_count": len(self.mcp_server.get_all_tools()),
            "active_connections": len(self.active_connections),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })

    async def handle_sse(self, request):
        """SSE端点 - 建立连接并保持"""
        # 只处理GET请求
        if request.method != 'GET':
            return web.Response(status=405, text="Method Not Allowed")

        conn_id = str(uuid.uuid4())

        response = web.StreamResponse()
        response.headers['Content-Type'] = 'text/event-stream'
        response.headers['Cache-Control'] = 'no-cache, no-transform'
        response.headers['Connection'] = 'keep-alive'
        response.headers['X-Accel-Buffering'] = 'no'

        await response.prepare(request)

        # 创建消息队列
        queue = asyncio.Queue()
        self.active_connections[conn_id] = queue

        print(f"[SSE] 新连接: {conn_id}")

        try:
            # 发送endpoint消息告知客户端POST地址
            endpoint_event = {
                "endpoint": f"/?session_id={conn_id}"
            }
            await response.write(f"event: endpoint\ndata: {json.dumps(endpoint_event)}\n\n".encode('utf-8'))
            # await response.drain()  # Deprecated - removed

            # 持续从队列读取并发送消息
            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=30.0)
                    data = json.dumps(message)
                    await response.write(f"data: {data}\n\n".encode('utf-8'))
                    # await response.drain()  # Deprecated - removed
                except asyncio.TimeoutError:
                    # 发送心跳
                    await response.write(b": ping\n\n")
                    # await response.drain()  # Deprecated - removed

        except Exception as e:
            print(f"[SSE] 连接错误 {conn_id}: {e}")
        finally:
            if conn_id in self.active_connections:
                del self.active_connections[conn_id]
            print(f"[SSE] 连接关闭: {conn_id}")

        return response

    async def handle_post_message(self, request):
        """处理POST消息"""
        # 只处理POST请求
        if request.method != 'POST':
            return web.Response(status=405, text="Method Not Allowed")

        try:
            # 获取session_id
            session_id = request.query.get('session_id')
            if not session_id or session_id not in self.active_connections:
                print(f"[HTTP] 无效session: {session_id}, 活动连接: {list(self.active_connections.keys())}")
                return web.json_response(
                    {"error": "Invalid session"},
                    status=400
                )

            # 解析请求
            json_request = await request.json()
            method = json_request.get('method', 'unknown')
            request_id = json_request.get('id', 'N/A')
            print(f"[HTTP] 收到请求 [ID:{request_id}]: {method}")

            # 调用MCP服务器处理
            mcp_response = self.mcp_server.handle_request(json_request)
            print(f"[HTTP] 响应 [ID:{request_id}]: {len(str(mcp_response))} bytes")

            # 将响应放入SSE队列
            queue = self.active_connections[session_id]
            await queue.put(mcp_response)

            # 返回HTTP 202 Accepted
            return web.Response(status=202)

        except Exception as e:
            print(f"[HTTP] 错误: {e}")
            import traceback
            traceback.print_exc()
            return web.json_response(
                {"error": str(e)},
                status=500
            )

    def run(self):
        """启动服务器"""
        print(f"")
        print(f"{'='*60}")
        print(f"  🚀 MCP HTTP服务器 v2.0.0")
        print(f"{'='*60}")
        print(f"")
        print(f"📡 监听地址: http://{self.host}:{self.port}")
        print(f"🌐 局域网地址: http://192.168.1.34:{self.port}")
        print(f"🔧 工具数量: {len(self.mcp_server.get_all_tools())}")
        print(f"")
        print(f"📋 Claude Code配置:")
        print(f"")
        print(f'{{')
        print(f'  "mcpServers": {{')
        print(f'    "mcp-remote": {{')
        print(f'      "url": "http://192.168.1.34:{self.port}",')
        print(f'      "transport": "sse"')
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

    parser = argparse.ArgumentParser(description='MCP HTTP+SSE服务器')
    parser.add_argument('--host', default='0.0.0.0', help='监听地址')
    parser.add_argument('--port', type=int, default=8765, help='监听端口')
    parser.add_argument('--config', help='配置文件路径')

    args = parser.parse_args()

    server = MCPHTTPSSEServer(
        host=args.host,
        port=args.port,
        config_file=args.config
    )

    server.run()


if __name__ == '__main__':
    main()

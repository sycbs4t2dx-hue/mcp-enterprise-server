#!/usr/bin/env python3
"""
MCP HTTP服务器 - 支持局域网访问
提供HTTP/WebSocket接口，允许远程客户端连接
"""

import json
import sys
import asyncio
from typing import Dict, Optional
from aiohttp import web
import aiohttp_cors
from datetime import datetime

# 导入统一服务器
from mcp_server_unified import UnifiedMCPServer


class MCPHTTPServer:
    """MCP HTTP服务器 - 包装stdio MCP服务器为HTTP API"""

    def __init__(self, host: str = "0.0.0.0", port: int = 8765, config_file: Optional[str] = None):
        self.host = host
        self.port = port
        self.mcp_server = UnifiedMCPServer(config_file)
        self.app = web.Application()
        self._setup_routes()

    def _setup_routes(self):
        """设置HTTP路由"""
        # API路由
        self.app.router.add_post('/mcp/call', self.handle_mcp_call)
        self.app.router.add_get('/mcp/tools', self.handle_list_tools)
        self.app.router.add_get('/health', self.handle_health)
        self.app.router.add_get('/', self.handle_index)

        # 配置CORS（允许跨域）
        cors = aiohttp_cors.setup(self.app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods="*"
            )
        })

        # 为所有路由添加CORS
        for route in list(self.app.router.routes()):
            cors.add(route)

    async def handle_index(self, request):
        """首页 - API文档"""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>MCP v2.0.0 HTTP服务器</title>
            <meta charset="utf-8">
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                    max-width: 1200px;
                    margin: 50px auto;
                    padding: 20px;
                    background: #f5f5f5;
                }
                .container {
                    background: white;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }
                h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
                h2 { color: #34495e; margin-top: 30px; }
                .status {
                    padding: 15px;
                    background: #d4edda;
                    border-left: 4px solid #28a745;
                    margin: 20px 0;
                    border-radius: 5px;
                }
                .endpoint {
                    background: #f8f9fa;
                    padding: 15px;
                    margin: 10px 0;
                    border-radius: 5px;
                    border-left: 4px solid #3498db;
                }
                .method {
                    display: inline-block;
                    padding: 3px 10px;
                    border-radius: 3px;
                    font-weight: bold;
                    font-size: 12px;
                    margin-right: 10px;
                }
                .get { background: #61affe; color: white; }
                .post { background: #49cc90; color: white; }
                pre {
                    background: #2c3e50;
                    color: #ecf0f1;
                    padding: 15px;
                    border-radius: 5px;
                    overflow-x: auto;
                }
                code { font-family: 'Monaco', 'Courier New', monospace; }
                .tool-list { columns: 2; }
                .tool-item { margin: 5px 0; padding: 5px; background: #ecf0f1; border-radius: 3px; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🚀 MCP v2.0.0 HTTP服务器</h1>

                <div class="status">
                    <strong>✅ 服务器运行中</strong><br>
                    服务器地址: <code>http://""" + request.host + """</code><br>
                    协议版本: MCP 2024-11-05<br>
                    可用工具: 37个
                </div>

                <h2>📡 API端点</h2>

                <div class="endpoint">
                    <span class="method get">GET</span>
                    <strong>/health</strong> - 健康检查
                    <pre>curl http://""" + request.host + """/health</pre>
                </div>

                <div class="endpoint">
                    <span class="method get">GET</span>
                    <strong>/mcp/tools</strong> - 获取所有可用工具
                    <pre>curl http://""" + request.host + """/mcp/tools</pre>
                </div>

                <div class="endpoint">
                    <span class="method post">POST</span>
                    <strong>/mcp/call</strong> - 调用MCP工具
                    <pre>curl -X POST http://""" + request.host + """/mcp/call \\
  -H "Content-Type: application/json" \\
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "store_memory",
      "arguments": {
        "content": "测试记忆",
        "memory_type": "long_term"
      }
    }
  }'</pre>
                </div>

                <h2>🔧 Claude Desktop配置</h2>
                <p>同事可以使用以下配置连接到您的MCP服务器：</p>
                <pre>{
  "mcpServers": {
    "mcp-remote": {
      "command": "python3",
      "args": ["/path/to/mcp_client_http.py", "http://192.168.3.5:8765"]
    }
  }
}</pre>

                <h2>📋 可用工具列表</h2>
                <p>访问 <a href="/mcp/tools">/mcp/tools</a> 查看完整列表</p>

                <h2>💡 使用示例</h2>
                <h3>存储记忆</h3>
                <pre>POST /mcp/call
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "store_memory",
    "arguments": {
      "content": "重要的项目决策",
      "memory_type": "long_term",
      "tags": ["决策", "架构"]
    }
  }
}</pre>

                <h3>分析代码</h3>
                <pre>POST /mcp/call
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "analyze_codebase",
    "arguments": {
      "project_path": "/path/to/project",
      "project_name": "MyProject"
    }
  }
}</pre>

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
            "protocol": "MCP 2024-11-05",
            "tools_count": len(self.mcp_server.get_all_tools()),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })

    async def handle_list_tools(self, request):
        """列出所有可用工具"""
        tools = self.mcp_server.get_all_tools()

        tools_info = []
        for tool in tools:
            tools_info.append({
                "name": tool.get("name"),
                "description": tool.get("description", ""),
                "inputSchema": tool.get("inputSchema", {})
            })

        return web.json_response({
            "jsonrpc": "2.0",
            "result": {
                "tools": tools_info,
                "count": len(tools_info)
            }
        })

    async def handle_mcp_call(self, request):
        """处理MCP工具调用"""
        try:
            # 解析JSON请求
            json_request = await request.json()

            # 调用MCP服务器
            response = self.mcp_server.handle_request(json_request)

            # 返回响应
            return web.json_response(response)

        except json.JSONDecodeError as e:
            return web.json_response({
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32700,
                    "message": "Parse error",
                    "data": str(e)
                }
            }, status=400)

        except Exception as e:
            return web.json_response({
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32603,
                    "message": "Internal error",
                    "data": str(e)
                }
            }, status=500)

    def run(self):
        """启动HTTP服务器"""
        print(f"🚀 MCP HTTP服务器启动中...")
        print(f"📡 监听地址: http://{self.host}:{self.port}")
        print(f"🌐 局域网地址: http://192.168.3.5:{self.port}")
        print(f"🔧 工具数量: {len(self.mcp_server.get_all_tools())}")
        print(f"")
        print(f"访问 http://192.168.3.5:{self.port} 查看文档")
        print(f"")

        web.run_app(self.app, host=self.host, port=self.port)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='MCP HTTP服务器')
    parser.add_argument('--host', default='0.0.0.0', help='监听地址 (默认: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=8765, help='监听端口 (默认: 8765)')
    parser.add_argument('--config', help='配置文件路径')

    args = parser.parse_args()

    server = MCPHTTPServer(
        host=args.host,
        port=args.port,
        config_file=args.config
    )

    server.run()


if __name__ == '__main__':
    main()

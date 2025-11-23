#!/usr/bin/env python3
"""
MCP HTTP客户端 - 用于连接远程MCP HTTP服务器
供Claude Desktop使用
"""

import sys
import json
import requests
from typing import Dict


class MCPHTTPClient:
    """MCP HTTP客户端 - 将stdio请求转发到HTTP服务器"""

    def __init__(self, server_url: str):
        self.server_url = server_url.rstrip('/')
        self.session = requests.Session()

    def call_tool(self, request: Dict) -> Dict:
        """调用远程MCP工具"""
        try:
            response = self.session.post(
                f"{self.server_url}/mcp/call",
                json=request,
                timeout=30
            )
            response.raise_for_status()
            return response.json()

        except requests.RequestException as e:
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {
                    "code": -32603,
                    "message": f"HTTP请求失败: {str(e)}"
                }
            }

    def run(self):
        """运行客户端 - stdio模式"""
        # 从stdin读取请求，转发到HTTP服务器
        for line in sys.stdin:
            try:
                request = json.loads(line.strip())
                response = self.call_tool(request)
                print(json.dumps(response), flush=True)

            except json.JSONDecodeError as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32700,
                        "message": "Parse error",
                        "data": str(e)
                    }
                }
                print(json.dumps(error_response), flush=True)


def main():
    if len(sys.argv) < 2:
        print("用法: python3 mcp_client_http.py <server_url>", file=sys.stderr)
        print("示例: python3 mcp_client_http.py http://192.168.3.5:8765", file=sys.stderr)
        sys.exit(1)

    server_url = sys.argv[1]
    client = MCPHTTPClient(server_url)
    client.run()


if __name__ == '__main__':
    main()

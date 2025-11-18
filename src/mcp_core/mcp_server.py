#!/usr/bin/env python3
"""
MCP (Model Context Protocol) Server Implementation

基于Anthropic MCP规范的标准服务端实现
支持Claude Desktop和其他MCP客户端连接

协议: JSON-RPC 2.0
传输: stdio
"""

import json
import sys
import logging
from typing import Any, Optional, Dict, List
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .common.config import settings
from .services.memory_service import MemoryService

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/mcp_server.log'),
        logging.StreamHandler(sys.stderr)  # MCP要求错误输出到stderr
    ]
)
logger = logging.getLogger(__name__)


class MCPServer:
    """MCP协议服务端"""

    # MCP协议版本
    PROTOCOL_VERSION = "2025-06-18"

    # 服务器信息
    SERVER_NAME = "mcp-memory-server"
    SERVER_VERSION = "1.0.0"

    def __init__(self):
        """初始化MCP服务端"""
        self.memory_service: Optional[MemoryService] = None
        self.current_project_id: Optional[str] = None

        # 初始化数据库连接
        try:
            engine = create_engine(settings.database.url, pool_pre_ping=True)
            SessionLocal = sessionmaker(bind=engine)
            db = SessionLocal()
            self.memory_service = MemoryService(db)
            logger.info("✓ 数据库连接成功")
        except Exception as e:
            logger.error(f"✗ 数据库连接失败: {e}")

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理JSON-RPC 2.0请求

        Args:
            request: JSON-RPC请求对象

        Returns:
            JSON-RPC响应对象
        """
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")

        logger.debug(f"收到请求: {method}")

        # 路由到对应的处理方法
        try:
            if method == "initialize":
                result = self._handle_initialize(params)
            elif method == "resources/list":
                result = self._handle_resources_list(params)
            elif method == "resources/read":
                result = self._handle_resources_read(params)
            elif method == "tools/list":
                result = self._handle_tools_list(params)
            elif method == "tools/call":
                result = self._handle_tools_call(params)
            elif method == "prompts/list":
                result = self._handle_prompts_list(params)
            elif method == "prompts/get":
                result = self._handle_prompts_get(params)
            else:
                return self._error_response(
                    request_id,
                    -32601,
                    f"Method not found: {method}"
                )

            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }

        except Exception as e:
            logger.error(f"处理请求失败: {e}", exc_info=True)
            return self._error_response(
                request_id,
                -32603,
                f"Internal error: {str(e)}"
            )

    def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理初始化请求"""
        client_info = params.get("clientInfo", {})
        logger.info(f"客户端连接: {client_info.get('name', 'unknown')}")

        return {
            "protocolVersion": self.PROTOCOL_VERSION,
            "serverInfo": {
                "name": self.SERVER_NAME,
                "version": self.SERVER_VERSION
            },
            "capabilities": {
                "resources": {
                    "subscribe": False,  # 暂不支持订阅
                    "listChanged": False
                },
                "tools": {},
                "prompts": {
                    "listChanged": False
                }
            }
        }

    def _handle_resources_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        列出可用资源

        资源代表项目中的记忆数据
        """
        if not self.memory_service or not self.current_project_id:
            return {"resources": []}

        try:
            # 获取项目的所有记忆
            memories = self.memory_service.db.query(
                self.memory_service.db.query(
                    # 这里简化处理，实际应该通过MemoryService的方法
                ).filter_by(project_id=self.current_project_id).all()
            )

            resources = []
            for memory in memories[:10]:  # 限制数量
                resources.append({
                    "uri": f"memory://{self.current_project_id}/{memory.memory_id}",
                    "name": f"Memory: {memory.content[:50]}...",
                    "description": f"记忆级别: {memory.memory_level}",
                    "mimeType": "text/plain"
                })

            return {"resources": resources}

        except Exception as e:
            logger.error(f"获取资源列表失败: {e}")
            return {"resources": []}

    def _handle_resources_read(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """读取特定资源"""
        uri = params.get("uri", "")

        # 解析URI: memory://project_id/memory_id
        if not uri.startswith("memory://"):
            raise ValueError(f"Invalid URI: {uri}")

        parts = uri.replace("memory://", "").split("/")
        if len(parts) != 2:
            raise ValueError(f"Invalid URI format: {uri}")

        project_id, memory_id = parts

        # 这里需要实现读取单个记忆的逻辑
        # 简化处理，返回示例
        return {
            "contents": [{
                "uri": uri,
                "mimeType": "text/plain",
                "text": "记忆内容..."
            }]
        }

    def _handle_tools_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        列出可用工具

        MCP Tools = 可供LLM调用的函数
        """
        tools = [
            {
                "name": "store_memory",
                "description": "存储新的记忆到项目中",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "项目ID"
                        },
                        "content": {
                            "type": "string",
                            "description": "记忆内容"
                        },
                        "memory_level": {
                            "type": "string",
                            "enum": ["short", "mid", "long"],
                            "description": "记忆级别",
                            "default": "mid"
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "标签（可选）"
                        }
                    },
                    "required": ["project_id", "content"]
                }
            },
            {
                "name": "retrieve_memory",
                "description": "根据查询检索相关记忆",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "项目ID"
                        },
                        "query": {
                            "type": "string",
                            "description": "检索查询"
                        },
                        "top_k": {
                            "type": "integer",
                            "description": "返回结果数量",
                            "default": 5
                        },
                        "memory_level": {
                            "type": "string",
                            "enum": ["short", "mid", "long"],
                            "description": "记忆级别过滤（可选）"
                        }
                    },
                    "required": ["project_id", "query"]
                }
            },
            {
                "name": "compress_content",
                "description": "压缩长文本以节省Token",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "待压缩内容"
                        },
                        "target_ratio": {
                            "type": "number",
                            "description": "目标压缩率(0-1)",
                            "default": 0.5
                        }
                    },
                    "required": ["content"]
                }
            },
            {
                "name": "detect_hallucination",
                "description": "检测AI输出是否包含幻觉",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "项目ID"
                        },
                        "output": {
                            "type": "string",
                            "description": "AI生成的输出"
                        }
                    },
                    "required": ["project_id", "output"]
                }
            }
        ]

        return {"tools": tools}

    def _handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行工具调用

        这是核心方法，将MCP工具调用桥接到现有服务
        """
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        logger.info(f"执行工具: {tool_name}")
        logger.debug(f"参数: {arguments}")

        if not self.memory_service:
            raise RuntimeError("记忆服务未初始化")

        try:
            if tool_name == "store_memory":
                result = self._tool_store_memory(arguments)
            elif tool_name == "retrieve_memory":
                result = self._tool_retrieve_memory(arguments)
            elif tool_name == "compress_content":
                result = self._tool_compress_content(arguments)
            elif tool_name == "detect_hallucination":
                result = self._tool_detect_hallucination(arguments)
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            return {
                "content": [{
                    "type": "text",
                    "text": json.dumps(result, ensure_ascii=False, indent=2)
                }]
            }

        except Exception as e:
            logger.error(f"工具执行失败: {e}", exc_info=True)
            return {
                "content": [{
                    "type": "text",
                    "text": f"错误: {str(e)}"
                }],
                "isError": True
            }

    def _tool_store_memory(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """工具: 存储记忆"""
        memory = self.memory_service.store_memory(
            project_id=args["project_id"],
            content=args["content"],
            memory_level=args.get("memory_level", "mid"),
            tags=args.get("tags", []),
            metadata={}
        )

        return {
            "success": True,
            "memory_id": memory.memory_id,
            "message": "记忆存储成功"
        }

    def _tool_retrieve_memory(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """工具: 检索记忆"""
        results = self.memory_service.retrieve_memory(
            project_id=args["project_id"],
            query=args["query"],
            top_k=args.get("top_k", 5),
            memory_level=args.get("memory_level")
        )

        return {
            "success": True,
            "count": len(results),
            "memories": [
                {
                    "content": m.content,
                    "memory_level": m.memory_level,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                    "score": getattr(m, 'score', None)
                }
                for m in results
            ]
        }

    def _tool_compress_content(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """工具: 压缩内容"""
        from .services.token_service import get_token_service

        token_service = get_token_service()
        result = token_service.compress_content(
            content=args["content"],
            target_ratio=args.get("target_ratio", 0.5)
        )

        return {
            "success": True,
            "original_tokens": result["original_tokens"],
            "compressed_tokens": result["compressed_tokens"],
            "compression_ratio": result["compression_ratio"],
            "compressed_content": result["compressed_content"]
        }

    def _tool_detect_hallucination(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """工具: 检测幻觉"""
        from .services.hallucination_service import create_hallucination_service

        hallucination_service = create_hallucination_service(self.memory_service)
        result = hallucination_service.detect_hallucination(
            project_id=args["project_id"],
            output=args["output"]
        )

        return {
            "success": True,
            "is_hallucination": result.is_hallucination,
            "confidence": result.confidence,
            "risk_level": result.risk_level,
            "details": result.details
        }

    def _handle_prompts_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """列出可用提示模板"""
        prompts = [
            {
                "name": "memory-assistant",
                "description": "记忆管理助手提示词",
                "arguments": [
                    {
                        "name": "project_id",
                        "description": "项目ID",
                        "required": True
                    }
                ]
            }
        ]

        return {"prompts": prompts}

    def _handle_prompts_get(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取提示模板"""
        prompt_name = params.get("name")
        arguments = params.get("arguments", {})

        if prompt_name == "memory-assistant":
            project_id = arguments.get("project_id", "default")
            return {
                "description": "记忆管理助手",
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": f"""你是项目 {project_id} 的记忆管理助手。

你可以使用以下功能:
1. store_memory - 存储新记忆
2. retrieve_memory - 检索相关记忆
3. compress_content - 压缩长文本
4. detect_hallucination - 检测幻觉

请根据用户需求智能调用这些工具。"""
                        }
                    }
                ]
            }

        raise ValueError(f"Unknown prompt: {prompt_name}")

    def _error_response(self, request_id: Any, code: int, message: str) -> Dict[str, Any]:
        """构造错误响应"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": message
            }
        }

    def run(self):
        """
        运行MCP服务端

        通过stdin/stdout进行JSON-RPC通信
        """
        logger.info(f"=== {self.SERVER_NAME} v{self.SERVER_VERSION} ===")
        logger.info(f"MCP协议版本: {self.PROTOCOL_VERSION}")
        logger.info("等待客户端连接...")

        # 读取stdin，处理请求，输出到stdout
        for line in sys.stdin:
            try:
                request = json.loads(line.strip())
                response = self.handle_request(request)

                # 输出响应到stdout
                print(json.dumps(response), flush=True)

            except json.JSONDecodeError as e:
                logger.error(f"JSON解析失败: {e}")
                error_response = self._error_response(
                    None,
                    -32700,
                    "Parse error"
                )
                print(json.dumps(error_response), flush=True)

            except Exception as e:
                logger.error(f"未处理异常: {e}", exc_info=True)


def main():
    """主入口"""
    server = MCPServer()
    server.run()


if __name__ == "__main__":
    main()

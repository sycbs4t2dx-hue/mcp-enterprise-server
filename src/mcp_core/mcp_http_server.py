#!/usr/bin/env python3
"""
MCP HTTP Server with SSE (Server-Sent Events)

远程MCP服务端实现，支持HTTP传输
用于部署到远程服务器，供多用户访问

协议: JSON-RPC 2.0 over HTTP
传输: HTTP + Server-Sent Events (SSE)
"""

import json
import logging
import asyncio
from typing import Any, Dict, Optional, AsyncIterator
from datetime import datetime
import secrets

from fastapi import FastAPI, Request, HTTPException, Depends, Header
from fastapi.responses import StreamingResponse
from starlette.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from .common.config import settings
from .services.memory_service import MemoryService
from .services.token_service import get_token_service
from .services.hallucination_service import create_hallucination_service
from .mcp_server import MCPServer

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ==================== 认证管理 ====================

class MCPAuthManager:
    """MCP API Key管理"""

    def __init__(self):
        # 简单的内存存储，生产环境应使用数据库
        self.api_keys: Dict[str, Dict[str, Any]] = {}

    def create_api_key(self, user_id: str, description: str = "") -> str:
        """创建API Key"""
        api_key = f"mcp_{secrets.token_urlsafe(32)}"
        self.api_keys[api_key] = {
            "user_id": user_id,
            "description": description,
            "created_at": datetime.now().isoformat(),
            "last_used": None
        }
        return api_key

    def validate_api_key(self, api_key: str) -> Optional[str]:
        """验证API Key，返回user_id"""
        if api_key in self.api_keys:
            self.api_keys[api_key]["last_used"] = datetime.now().isoformat()
            return self.api_keys[api_key]["user_id"]
        return None

    def revoke_api_key(self, api_key: str):
        """撤销API Key"""
        if api_key in self.api_keys:
            del self.api_keys[api_key]


# 全局认证管理器
auth_manager = MCPAuthManager()


# ==================== FastAPI应用 ====================

# 创建独立的FastAPI应用（与REST API分离）
app = FastAPI(
    title="MCP HTTP Server",
    description="Remote MCP Server with HTTP+SSE transport",
    version="1.1.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== 依赖注入 ====================

def get_db() -> Session:
    """获取数据库会话"""
    engine = create_engine(settings.database.url, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_api_key(authorization: Optional[str] = Header(None)) -> str:
    """验证API Key"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing API Key")

    # 支持两种格式: "Bearer <key>" 或 直接 "<key>"
    if authorization.startswith("Bearer "):
        api_key = authorization[7:]
    else:
        api_key = authorization

    user_id = auth_manager.validate_api_key(api_key)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid API Key")

    return user_id


# ==================== MCP处理器 ====================

class MCPHTTPHandler:
    """HTTP版本的MCP请求处理器"""

    def __init__(self, db: Session, user_id: str):
        self.db = db
        self.user_id = user_id
        self.memory_service = MemoryService(db)
        self.token_service = get_token_service()
        self.hallucination_service = create_hallucination_service(self.memory_service)

    def handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理初始化"""
        return {
            "protocolVersion": "2025-06-18",
            "serverInfo": {
                "name": "mcp-memory-http-server",
                "version": "1.1.0"
            },
            "capabilities": {
                "resources": {"subscribe": False, "listChanged": False},
                "tools": {},
                "prompts": {"listChanged": False}
            }
        }

    def handle_tools_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """列出工具"""
        return {
            "tools": [
                {
                    "name": "store_memory",
                    "description": "存储新的记忆到项目中",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "project_id": {"type": "string", "description": "项目ID"},
                            "content": {"type": "string", "description": "记忆内容"},
                            "memory_level": {
                                "type": "string",
                                "enum": ["short", "mid", "long"],
                                "description": "记忆级别",
                                "default": "mid"
                            },
                            "tags": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "标签"
                            }
                        },
                        "required": ["project_id", "content"]
                    }
                },
                {
                    "name": "retrieve_memory",
                    "description": "检索相关记忆",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "project_id": {"type": "string", "description": "项目ID"},
                            "query": {"type": "string", "description": "检索查询"},
                            "top_k": {"type": "integer", "description": "返回数量", "default": 5}
                        },
                        "required": ["project_id", "query"]
                    }
                },
                {
                    "name": "compress_content",
                    "description": "压缩长文本",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "content": {"type": "string", "description": "待压缩内容"},
                            "target_ratio": {"type": "number", "description": "目标压缩率", "default": 0.5}
                        },
                        "required": ["content"]
                    }
                },
                {
                    "name": "detect_hallucination",
                    "description": "检测AI输出幻觉",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "project_id": {"type": "string", "description": "项目ID"},
                            "output": {"type": "string", "description": "AI输出"}
                        },
                        "required": ["project_id", "output"]
                    }
                }
            ]
        }

    def handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具"""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

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
            logger.error(f"Tool execution failed: {e}", exc_info=True)
            return {
                "content": [{
                    "type": "text",
                    "text": f"错误: {str(e)}"
                }],
                "isError": True
            }

    def _tool_store_memory(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """存储记忆"""
        memory = self.memory_service.store_memory(
            project_id=args["project_id"],
            content=args["content"],
            memory_level=args.get("memory_level", "mid"),
            tags=args.get("tags", []),
            metadata={"user_id": self.user_id}  # 记录用户ID
        )
        return {
            "success": True,
            "memory_id": memory.memory_id,
            "message": "记忆存储成功"
        }

    def _tool_retrieve_memory(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """检索记忆"""
        results = self.memory_service.retrieve_memory(
            project_id=args["project_id"],
            query=args["query"],
            top_k=args.get("top_k", 5)
        )
        return {
            "success": True,
            "count": len(results),
            "memories": [
                {
                    "content": m.content,
                    "memory_level": m.memory_level,
                    "created_at": m.created_at.isoformat() if m.created_at else None
                }
                for m in results
            ]
        }

    def _tool_compress_content(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """压缩内容"""
        result = self.token_service.compress_content(
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
        """检测幻觉"""
        result = self.hallucination_service.detect_hallucination(
            project_id=args["project_id"],
            output=args["output"]
        )
        return {
            "success": True,
            "is_hallucination": result.is_hallucination,
            "confidence": result.confidence,
            "risk_level": result.risk_level
        }

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """处理JSON-RPC请求"""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")

        try:
            if method == "initialize":
                result = self.handle_initialize(params)
            elif method == "tools/list":
                result = self.handle_tools_list(params)
            elif method == "tools/call":
                result = self.handle_tools_call(params)
            elif method == "prompts/list":
                result = {"prompts": []}
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"}
                }

            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }

        except Exception as e:
            logger.error(f"Request handling failed: {e}", exc_info=True)
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32603, "message": f"Internal error: {str(e)}"}
            }


# ==================== API端点 ====================

@app.get("/")
async def root():
    """根路径"""
    return {
        "name": "MCP HTTP Server",
        "version": "1.1.0",
        "protocol": "MCP 2025-06-18",
        "transport": "HTTP + SSE",
        "endpoints": {
            "health": "/health",
            "mcp": "/mcp (POST)",
            "sse": "/sse (GET with SSE)",
            "api_keys": "/api/keys"
        }
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "mcp-http-server",
        "version": "1.1.0",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/mcp")
async def mcp_endpoint(
    request: Request,
    db: Session = Depends(get_db),
    user_id: str = Depends(verify_api_key)
):
    """
    MCP JSON-RPC端点

    支持标准的JSON-RPC 2.0请求
    """
    try:
        body = await request.json()
        handler = MCPHTTPHandler(db, user_id)
        response = handler.handle_request(body)
        return response

    except Exception as e:
        logger.error(f"MCP endpoint error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sse")
async def sse_endpoint(
    db: Session = Depends(get_db),
    user_id: str = Depends(verify_api_key)
):
    """
    Server-Sent Events (SSE) 端点

    用于MCP客户端建立长连接，接收服务器推送的事件
    """
    async def event_stream() -> AsyncIterator[str]:
        """事件流生成器"""
        # 发送连接确认
        yield f"data: {json.dumps({'type': 'connection', 'status': 'connected', 'user_id': user_id})}\n\n"

        # 保持连接
        while True:
            await asyncio.sleep(30)  # 每30秒发送心跳
            yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': datetime.now().isoformat()})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


# ==================== API Key管理端点 ====================

@app.post("/api/keys/create")
async def create_api_key(
    user_id: str,
    description: str = ""
):
    """
    创建API Key

    注意: 这个端点应该有额外的认证保护
    生产环境应该使用管理员Token或其他安全机制
    """
    api_key = auth_manager.create_api_key(user_id, description)
    return {
        "api_key": api_key,
        "user_id": user_id,
        "description": description,
        "created_at": datetime.now().isoformat()
    }


@app.get("/api/keys/info")
async def get_api_key_info(user_id: str = Depends(verify_api_key)):
    """获取当前API Key信息"""
    return {
        "user_id": user_id,
        "message": "API Key is valid"
    }


@app.delete("/api/keys/revoke")
async def revoke_api_key(
    api_key: str,
    user_id: str = Depends(verify_api_key)
):
    """撤销API Key"""
    auth_manager.revoke_api_key(api_key)
    return {"message": "API Key revoked successfully"}


# ==================== 启动 ====================

if __name__ == "__main__":
    import uvicorn

    # 创建初始API Key供测试
    test_key = auth_manager.create_api_key("admin", "Initial test key")
    logger.info("=" * 60)
    logger.info("MCP HTTP Server Starting...")
    logger.info(f"Test API Key: {test_key}")
    logger.info("=" * 60)

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,  # 使用8001避免与REST API冲突
        log_level="info"
    )

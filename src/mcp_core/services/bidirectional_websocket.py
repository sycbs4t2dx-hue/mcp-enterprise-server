"""
WebSocket双向通信服务
增强版WebSocket服务，支持客户端到服务器的消息处理
"""

import json
import asyncio
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
from aiohttp import web
import uuid

from ..common.logger import get_logger

logger = get_logger(__name__)


class BidirectionalWebSocket:
    """
    双向WebSocket通信服务

    特性：
    - 客户端到服务器的消息处理
    - 命令注册和执行
    - 请求-响应模式支持
    - 心跳保活
    """

    def __init__(self):
        """初始化双向WebSocket服务"""
        # 活动连接
        self.connections: Dict[str, web.WebSocketResponse] = {}

        # 客户端信息
        self.client_info: Dict[str, Dict[str, Any]] = {}

        # 命令处理器注册表
        self.command_handlers: Dict[str, Callable] = {}

        # 请求响应追踪
        self.pending_requests: Dict[str, asyncio.Future] = {}

        # 注册默认命令
        self._register_default_commands()

        logger.info("双向WebSocket服务初始化完成")

    def _register_default_commands(self):
        """注册默认命令处理器"""
        # 订阅频道
        self.register_command("subscribe", self._handle_subscribe)

        # 取消订阅
        self.register_command("unsubscribe", self._handle_unsubscribe)

        # 心跳
        self.register_command("ping", self._handle_ping)

        # 执行MCP工具
        self.register_command("execute_tool", self._handle_execute_tool)

        # 查询缓存
        self.register_command("query_cache", self._handle_query_cache)

        # 清除缓存
        self.register_command("clear_cache", self._handle_clear_cache)

        # 获取统计
        self.register_command("get_stats", self._handle_get_stats)

        # 执行查询
        self.register_command("query", self._handle_query)

    def register_command(self, command: str, handler: Callable):
        """
        注册命令处理器

        Args:
            command: 命令名称
            handler: 处理函数 async def handler(client_id, data) -> Any
        """
        self.command_handlers[command] = handler
        logger.debug(f"注册命令处理器: {command}")

    async def handle_websocket(self, request: web.Request) -> web.WebSocketResponse:
        """
        处理WebSocket连接

        Args:
            request: HTTP请求

        Returns:
            WebSocket响应
        """
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        # 生成客户端ID
        client_id = str(uuid.uuid4())[:8]

        # 记录连接
        self.connections[client_id] = ws
        self.client_info[client_id] = {
            "connected_at": datetime.now(),
            "remote": request.remote,
            "user_agent": request.headers.get("User-Agent", ""),
            "subscribed_channels": set(),
            "request_count": 0,
            "last_activity": datetime.now()
        }

        logger.info(f"WebSocket客户端连接: {client_id} from {request.remote}")

        # 发送连接确认
        await ws.send_json({
            "type": "connected",
            "client_id": client_id,
            "timestamp": datetime.now().isoformat(),
            "available_commands": list(self.command_handlers.keys())
        })

        try:
            # 消息循环
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    await self._handle_client_message(client_id, msg.data)
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"WebSocket错误 {client_id}: {ws.exception()}")
                    break

        except Exception as e:
            logger.error(f"WebSocket处理异常 {client_id}: {e}")

        finally:
            # 清理连接
            await self._cleanup_client(client_id)

        return ws

    async def _handle_client_message(self, client_id: str, message: str):
        """
        处理客户端消息

        Args:
            client_id: 客户端ID
            message: 消息内容
        """
        try:
            data = json.loads(message)
            msg_type = data.get("type")
            msg_id = data.get("id")  # 可选的消息ID（用于请求-响应）

            # 更新活动时间
            if client_id in self.client_info:
                self.client_info[client_id]["last_activity"] = datetime.now()
                self.client_info[client_id]["request_count"] += 1

            # 处理命令
            if msg_type in self.command_handlers:
                handler = self.command_handlers[msg_type]
                try:
                    result = await handler(client_id, data.get("data", {}))

                    # 发送响应
                    response = {
                        "type": "response",
                        "command": msg_type,
                        "success": True,
                        "data": result,
                        "timestamp": datetime.now().isoformat()
                    }

                    if msg_id:
                        response["id"] = msg_id

                    await self._send_to_client(client_id, response)

                except Exception as e:
                    logger.error(f"命令处理失败 {msg_type}: {e}")
                    # 发送错误响应
                    error_response = {
                        "type": "error",
                        "command": msg_type,
                        "success": False,
                        "error": str(e),
                        "timestamp": datetime.now().isoformat()
                    }
                    if msg_id:
                        error_response["id"] = msg_id

                    await self._send_to_client(client_id, error_response)

            else:
                logger.warning(f"未知命令类型: {msg_type}")
                await self._send_to_client(client_id, {
                    "type": "error",
                    "error": f"Unknown command: {msg_type}",
                    "available_commands": list(self.command_handlers.keys())
                })

        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败 {client_id}: {e}")
            await self._send_to_client(client_id, {
                "type": "error",
                "error": "Invalid JSON"
            })

    async def _send_to_client(self, client_id: str, data: Dict[str, Any]):
        """发送消息给特定客户端"""
        if client_id in self.connections:
            ws = self.connections[client_id]
            try:
                await ws.send_json(data)
            except Exception as e:
                logger.error(f"发送消息失败 {client_id}: {e}")

    async def broadcast(self, channel: str, data: Dict[str, Any]):
        """广播消息到订阅频道的所有客户端"""
        message = {
            "type": "broadcast",
            "channel": channel,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }

        # 找到订阅该频道的客户端
        for client_id, info in self.client_info.items():
            if channel in info.get("subscribed_channels", set()):
                await self._send_to_client(client_id, message)

    async def _cleanup_client(self, client_id: str):
        """清理断开的客户端"""
        if client_id in self.connections:
            del self.connections[client_id]
        if client_id in self.client_info:
            del self.client_info[client_id]
        # 清理待处理请求
        for req_id in list(self.pending_requests.keys()):
            if req_id.startswith(client_id):
                self.pending_requests[req_id].cancel()
                del self.pending_requests[req_id]

        logger.info(f"WebSocket客户端断开: {client_id}")

    # ==================== 默认命令处理器 ====================

    async def _handle_subscribe(self, client_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """处理订阅请求"""
        channels = data.get("channels", [])
        if not isinstance(channels, list):
            channels = [channels]

        subscribed = []
        for channel in channels:
            if client_id in self.client_info:
                self.client_info[client_id]["subscribed_channels"].add(channel)
                subscribed.append(channel)

        return {
            "subscribed": subscribed,
            "total_subscriptions": len(self.client_info[client_id]["subscribed_channels"])
        }

    async def _handle_unsubscribe(self, client_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """处理取消订阅请求"""
        channels = data.get("channels", [])
        if not isinstance(channels, list):
            channels = [channels]

        unsubscribed = []
        for channel in channels:
            if client_id in self.client_info:
                self.client_info[client_id]["subscribed_channels"].discard(channel)
                unsubscribed.append(channel)

        return {
            "unsubscribed": unsubscribed,
            "remaining_subscriptions": len(self.client_info[client_id]["subscribed_channels"])
        }

    async def _handle_ping(self, client_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """处理心跳"""
        return {
            "pong": True,
            "server_time": datetime.now().isoformat(),
            "client_id": client_id
        }

    async def _handle_execute_tool(self, client_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """执行MCP工具"""
        tool_name = data.get("tool")
        arguments = data.get("arguments", {})

        # 使用WebSocket工具执行器
        from .websocket_tool_executor import execute_mcp_tool

        try:
            # 异步执行工具
            result = await execute_mcp_tool(
                tool_name=tool_name,
                arguments=arguments,
                client_id=client_id
            )

            return {
                "tool": tool_name,
                "status": "success",
                "result": result,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"工具执行失败: {tool_name} - {e}")
            return {
                "tool": tool_name,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def _handle_query_cache(self, client_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """查询缓存"""
        from .cache_integration import get_cache_integration

        cache = get_cache_integration()
        key = data.get("key")
        category = data.get("category", "default")

        if not key:
            return {"error": "Cache key required"}

        value = cache.cache.get(key)
        return {
            "key": key,
            "category": category,
            "found": value is not None,
            "value": value
        }

    async def _handle_clear_cache(self, client_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """清除缓存"""
        from .cache_integration import get_cache_integration

        cache = get_cache_integration()
        category = data.get("category")

        if category:
            count = cache.invalidate_category(category)
            return {
                "category": category,
                "cleared": count
            }
        else:
            cache.clear_all()
            return {
                "message": "All cache cleared"
            }

    async def _handle_get_stats(self, client_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """获取统计信息"""
        stats_type = data.get("type", "all")

        stats = {
            "websocket": {
                "active_connections": len(self.connections),
                "total_clients": len(self.client_info)
            }
        }

        if stats_type in ["all", "cache"]:
            from .cache_integration import get_cache_integration
            cache = get_cache_integration()
            stats["cache"] = cache.get_stats()

        if stats_type in ["all", "system"]:
            import psutil
            stats["system"] = {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage": psutil.disk_usage('/').percent
            }

        return stats

    async def _handle_query(self, client_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """处理查询请求（可扩展）"""
        query_type = data.get("query_type")
        query_params = data.get("params", {})

        # 这里可以根据查询类型调用不同的服务
        # 例如：数据库查询、向量检索、错误查询等

        return {
            "query_type": query_type,
            "status": "completed",
            "result": f"Query {query_type} executed"
        }

    def get_connection_stats(self) -> Dict[str, Any]:
        """获取连接统计"""
        active_clients = []
        for client_id, info in self.client_info.items():
            active_clients.append({
                "client_id": client_id,
                "connected_at": info["connected_at"].isoformat(),
                "remote": info["remote"],
                "request_count": info["request_count"],
                "subscriptions": list(info["subscribed_channels"]),
                "last_activity": info["last_activity"].isoformat()
            })

        return {
            "total_connections": len(self.connections),
            "active_clients": active_clients,
            "command_handlers": list(self.command_handlers.keys())
        }


# 全局实例
_bidirectional_ws: Optional[BidirectionalWebSocket] = None


def get_bidirectional_websocket() -> BidirectionalWebSocket:
    """获取双向WebSocket服务单例"""
    global _bidirectional_ws
    if _bidirectional_ws is None:
        _bidirectional_ws = BidirectionalWebSocket()
    return _bidirectional_ws


# 便捷函数
async def broadcast_message(channel: str, data: Dict[str, Any]):
    """广播消息到频道"""
    ws = get_bidirectional_websocket()
    await ws.broadcast(channel, data)
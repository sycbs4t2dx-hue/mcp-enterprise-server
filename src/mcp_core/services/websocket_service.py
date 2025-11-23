"""
WebSocket实时通知服务
基于aiohttp WebSocket + Redis Pub/Sub实现实时消息推送
"""

import asyncio
import json
from typing import Dict, Set, Optional, Any
from datetime import datetime
import aiohttp
from aiohttp import web

from ..common.logger import get_context_logger
from .redis_client import get_redis_client

logger = get_context_logger(__name__)


# 频道定义
class Channels:
    """WebSocket频道定义"""
    ERROR_FIREWALL = "error_firewall"      # 错误防火墙拦截通知
    VECTOR_SEARCH = "vector_search"        # 向量检索进度
    DB_POOL_STATS = "db_pool_stats"        # 数据库连接池状态
    AI_ANALYSIS = "ai_analysis"            # AI代码分析进度
    MEMORY_UPDATES = "memory_updates"      # 记忆更新通知
    SYSTEM_ALERTS = "system_alerts"        # 系统告警
    SYSTEM_STATS = "system_stats"          # 系统统计（新增）

    @classmethod
    def all(cls) -> Set[str]:
        """获取所有频道"""
        return {
            cls.ERROR_FIREWALL,
            cls.VECTOR_SEARCH,
            cls.DB_POOL_STATS,
            cls.AI_ANALYSIS,
            cls.MEMORY_UPDATES,
            cls.SYSTEM_ALERTS,
            cls.SYSTEM_STATS
        }


class WebSocketManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        """初始化WebSocket管理器"""
        # 频道 -> WebSocket连接集合
        self.active_connections: Dict[str, Set[web.WebSocketResponse]] = {}
        
        # WebSocket连接 -> 订阅频道集合
        self.client_channels: Dict[web.WebSocketResponse, Set[str]] = {}
        
        # WebSocket连接 -> 客户端ID
        self.client_ids: Dict[web.WebSocketResponse, str] = {}
        
        # Redis客户端 (用于Pub/Sub)
        self.redis_client = get_redis_client()
        
        # Redis Pub/Sub任务
        self.pubsub_task: Optional[asyncio.Task] = None
        
        # 统计
        self.total_messages_sent = 0
        self.total_connections = 0
        
        logger.info("WebSocket管理器初始化完成")
    
    async def connect(self, websocket: web.WebSocketResponse, client_id: str) -> None:
        """
        客户端连接
        
        Args:
            websocket: WebSocket连接
            client_id: 客户端ID
        """
        # 记录客户端ID
        self.client_ids[websocket] = client_id
        
        # 初始化频道集合
        self.client_channels[websocket] = set()
        
        # 统计
        self.total_connections += 1
        
        # 发送欢迎消息
        await websocket.send_json({
            "type": "connection",
            "status": "connected",
            "client_id": client_id,
            "timestamp": datetime.now().isoformat(),
            "available_channels": list(Channels.all())
        })
        
        logger.info(f"WebSocket客户端连接: {client_id}")
    
    async def disconnect(self, websocket: web.WebSocketResponse) -> None:
        """
        客户端断开
        
        Args:
            websocket: WebSocket连接
        """
        client_id = self.client_ids.get(websocket, "unknown")
        
        # 从所有频道移除
        if websocket in self.client_channels:
            channels = self.client_channels[websocket]
            for channel in channels:
                if channel in self.active_connections:
                    self.active_connections[channel].discard(websocket)
                    # 如果频道没有订阅者，清理
                    if not self.active_connections[channel]:
                        del self.active_connections[channel]
            
            del self.client_channels[websocket]
        
        # 清理客户端ID
        if websocket in self.client_ids:
            del self.client_ids[websocket]
        
        logger.info(f"WebSocket客户端断开: {client_id}")
    
    async def subscribe(self, websocket: web.WebSocketResponse, channel: str) -> None:
        """
        订阅频道
        
        Args:
            websocket: WebSocket连接
            channel: 频道名称
        """
        client_id = self.client_ids.get(websocket, "unknown")
        
        # 验证频道
        if channel not in Channels.all():
            await websocket.send_json({
                "type": "error",
                "message": f"Invalid channel: {channel}",
                "available_channels": list(Channels.all())
            })
            return
        
        # 添加到频道
        if channel not in self.active_connections:
            self.active_connections[channel] = set()
        
        self.active_connections[channel].add(websocket)
        self.client_channels[websocket].add(channel)
        
        await websocket.send_json({
            "type": "subscribe",
            "channel": channel,
            "status": "success",
            "subscribers": len(self.active_connections[channel])
        })
        
        logger.info(f"客户端 {client_id} 订阅频道: {channel}")
    
    async def unsubscribe(self, websocket: web.WebSocketResponse, channel: str) -> None:
        """
        取消订阅频道
        
        Args:
            websocket: WebSocket连接
            channel: 频道名称
        """
        client_id = self.client_ids.get(websocket, "unknown")
        
        if channel in self.active_connections:
            self.active_connections[channel].discard(websocket)
        
        if websocket in self.client_channels:
            self.client_channels[websocket].discard(channel)
        
        await websocket.send_json({
            "type": "unsubscribe",
            "channel": channel,
            "status": "success"
        })
        
        logger.info(f"客户端 {client_id} 取消订阅频道: {channel}")
    
    async def broadcast(self, channel: str, message: Dict[str, Any]) -> int:
        """
        向频道广播消息
        
        Args:
            channel: 频道名称
            message: 消息内容
            
        Returns:
            接收消息的客户端数量
        """
        if channel not in self.active_connections:
            logger.debug(f"频道 {channel} 无订阅者")
            return 0
        
        # 添加元数据
        message["timestamp"] = datetime.now().isoformat()
        message["channel"] = channel
        
        count = 0
        disconnected = []
        
        for websocket in self.active_connections[channel].copy():
            try:
                await websocket.send_json(message)
                count += 1
                self.total_messages_sent += 1
            except Exception as e:
                logger.error(f"发送消息失败: {e}")
                disconnected.append(websocket)
        
        # 清理断开的连接
        for ws in disconnected:
            await self.disconnect(ws)
        
        logger.debug(f"广播消息到频道 {channel}: {count}个客户端")
        return count
    
    async def send_to_client(
        self,
        websocket: web.WebSocketResponse,
        message: Dict[str, Any]
    ) -> None:
        """
        向特定客户端发送消息
        
        Args:
            websocket: WebSocket连接
            message: 消息内容
        """
        message["timestamp"] = datetime.now().isoformat()
        
        try:
            await websocket.send_json(message)
            self.total_messages_sent += 1
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            await self.disconnect(websocket)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取WebSocket统计"""
        total_clients = len(self.client_channels)
        channel_stats = {
            channel: len(clients)
            for channel, clients in self.active_connections.items()
        }
        
        return {
            "total_clients": total_clients,
            "total_channels": len(self.active_connections),
            "total_messages_sent": self.total_messages_sent,
            "total_connections_ever": self.total_connections,
            "channel_stats": channel_stats,
            "active_channels": list(self.active_connections.keys())
        }


# 全局实例
_websocket_manager: Optional[WebSocketManager] = None


def get_websocket_manager() -> WebSocketManager:
    """获取WebSocket管理器单例"""
    global _websocket_manager
    
    if _websocket_manager is None:
        _websocket_manager = WebSocketManager()
    
    return _websocket_manager


# WebSocket路由处理
async def websocket_handler(request: web.Request) -> web.WebSocketResponse:
    """
    WebSocket连接处理器
    
    使用示例:
        ws://localhost:8080/ws?client_id=my_client
    """
    ws = web.WebSocketResponse(
        heartbeat=30,  # 30秒心跳
        timeout=300    # 5分钟超时
    )
    await ws.prepare(request)
    
    manager = get_websocket_manager()
    client_id = request.query.get("client_id", f"client_{id(ws)}")
    
    await manager.connect(ws, client_id)
    
    try:
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                    action = data.get("action")
                    
                    if action == "subscribe":
                        channel = data.get("channel")
                        if channel:
                            await manager.subscribe(ws, channel)
                        else:
                            await ws.send_json({
                                "type": "error",
                                "message": "Missing channel parameter"
                            })
                    
                    elif action == "unsubscribe":
                        channel = data.get("channel")
                        if channel:
                            await manager.unsubscribe(ws, channel)
                        else:
                            await ws.send_json({
                                "type": "error",
                                "message": "Missing channel parameter"
                            })
                    
                    elif action == "ping":
                        await ws.send_json({"type": "pong"})
                    
                    elif action == "get_stats":
                        stats = manager.get_stats()
                        await ws.send_json({
                            "type": "stats",
                            "data": stats
                        })
                    
                    else:
                        await ws.send_json({
                            "type": "error",
                            "message": f"Unknown action: {action}"
                        })
                
                except json.JSONDecodeError:
                    await ws.send_json({
                        "type": "error",
                        "message": "Invalid JSON"
                    })
            
            elif msg.type == aiohttp.WSMsgType.ERROR:
                logger.error(f"WebSocket错误: {ws.exception()}")
                break
    
    finally:
        await manager.disconnect(ws)
    
    return ws


# 便捷函数：向频道发送消息
async def notify_channel(channel: str, message_type: str, data: Dict[str, Any]) -> int:
    """
    向频道发送通知
    
    Args:
        channel: 频道名称
        message_type: 消息类型
        data: 消息数据
        
    Returns:
        接收消息的客户端数量
    
    示例:
        await notify_channel(
            Channels.ERROR_FIREWALL,
            "error_blocked",
            {"error_id": "xxx", "solution": "..."}
        )
    """
    manager = get_websocket_manager()
    message = {
        "type": message_type,
        "data": data
    }
    return await manager.broadcast(channel, message)

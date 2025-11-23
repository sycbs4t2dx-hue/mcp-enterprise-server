"""
WebSocket实时通信服务器
提供实时协作、通知推送、状态同步
"""

import json
import asyncio
import logging
from typing import Dict, Set, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

import websockets
from websockets.server import WebSocketServerProtocol
from websockets.exceptions import ConnectionClosed
import redis.asyncio as redis

from ..common.logger import get_logger

logger = get_logger(__name__)

# ============================================
# 消息类型定义
# ============================================

class MessageType(Enum):
    """消息类型"""
    # 连接管理
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    HEARTBEAT = "heartbeat"

    # 协作消息
    AGENT_STATUS = "agent_status"
    LOCK_UPDATE = "lock_update"
    TASK_UPDATE = "task_update"
    CONFLICT_ALERT = "conflict_alert"

    # 学习消息
    PATTERN_DETECTED = "pattern_detected"
    EXPERIENCE_SHARED = "experience_shared"
    LEARNING_UPDATE = "learning_update"

    # 系统消息
    SYSTEM_ALERT = "system_alert"
    PROGRESS_UPDATE = "progress_update"
    ERROR_NOTIFICATION = "error_notification"

@dataclass
class WebSocketMessage:
    """WebSocket消息"""
    type: MessageType
    payload: Dict[str, Any]
    sender: Optional[str] = None
    timestamp: str = None

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_json(self) -> str:
        return json.dumps({
            "type": self.type.value,
            "payload": self.payload,
            "sender": self.sender,
            "timestamp": self.timestamp
        })

# ============================================
# 客户端管理
# ============================================

@dataclass
class Client:
    """WebSocket客户端"""
    client_id: str
    websocket: WebSocketServerProtocol
    user_id: Optional[str] = None
    project_id: Optional[str] = None
    agent_id: Optional[str] = None
    subscriptions: Set[str] = None
    connected_at: datetime = None

    def __post_init__(self):
        if not self.subscriptions:
            self.subscriptions = set()
        if not self.connected_at:
            self.connected_at = datetime.now()

# ============================================
# WebSocket服务器
# ============================================

class WebSocketServer:
    """WebSocket服务器"""

    def __init__(self, host: str = "localhost", port: int = 8766):
        """
        初始化WebSocket服务器

        Args:
            host: 服务器地址
            port: 服务器端口
        """
        self.host = host
        self.port = port

        # 客户端管理
        self.clients: Dict[str, Client] = {}
        self.websocket_to_client: Dict[WebSocketServerProtocol, str] = {}

        # 频道订阅
        self.channels: Dict[str, Set[str]] = {}  # channel -> client_ids

        # Redis连接（用于跨服务器通信）
        self.redis_client: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None

        # 统计信息
        self.stats = {
            "total_connections": 0,
            "messages_sent": 0,
            "messages_received": 0,
            "errors": 0
        }

        logger.info(f"WebSocket服务器初始化: {host}:{port}")

    async def start(self):
        """启动服务器"""
        try:
            # 连接Redis
            await self.connect_redis()

            # 启动WebSocket服务器
            async with websockets.serve(
                self.handle_client,
                self.host,
                self.port,
                ping_interval=30,
                ping_timeout=10
            ):
                logger.info(f"WebSocket服务器启动在 ws://{self.host}:{self.port}")

                # 启动Redis订阅监听
                asyncio.create_task(self.redis_listener())

                # 启动心跳检查
                asyncio.create_task(self.heartbeat_checker())

                # 保持运行
                await asyncio.Future()

        except Exception as e:
            logger.error(f"WebSocket服务器启动失败: {e}")
            raise

    async def connect_redis(self):
        """连接Redis"""
        try:
            self.redis_client = await redis.from_url(
                "redis://localhost:6379",
                decode_responses=True
            )
            self.pubsub = self.redis_client.pubsub()

            # 订阅全局频道
            await self.pubsub.subscribe("websocket:broadcast")

            logger.info("Redis连接成功")

        except Exception as e:
            logger.warning(f"Redis连接失败: {e}")
            # 可以在没有Redis的情况下运行（单服务器模式）

    async def handle_client(self, websocket: WebSocketServerProtocol, path: str):
        """
        处理客户端连接

        Args:
            websocket: WebSocket连接
            path: 连接路径
        """
        client_id = self.generate_client_id()
        client = Client(
            client_id=client_id,
            websocket=websocket
        )

        # 注册客户端
        self.clients[client_id] = client
        self.websocket_to_client[websocket] = client_id
        self.stats["total_connections"] += 1

        logger.info(f"客户端连接: {client_id} from {websocket.remote_address}")

        try:
            # 发送连接确认
            await self.send_to_client(
                client_id,
                WebSocketMessage(
                    type=MessageType.CONNECT,
                    payload={"client_id": client_id, "status": "connected"}
                )
            )

            # 处理客户端消息
            async for message in websocket:
                await self.handle_message(client_id, message)

        except ConnectionClosed:
            logger.info(f"客户端断开连接: {client_id}")

        except Exception as e:
            logger.error(f"客户端处理错误 {client_id}: {e}")
            self.stats["errors"] += 1

        finally:
            # 清理客户端
            await self.remove_client(client_id)

    async def handle_message(self, client_id: str, message: str):
        """
        处理客户端消息

        Args:
            client_id: 客户端ID
            message: 消息内容
        """
        try:
            self.stats["messages_received"] += 1

            # 解析消息
            data = json.loads(message)
            msg_type = MessageType(data.get("type"))
            payload = data.get("payload", {})

            logger.debug(f"收到消息 from {client_id}: {msg_type.value}")

            # 根据消息类型处理
            if msg_type == MessageType.HEARTBEAT:
                await self.handle_heartbeat(client_id)

            elif msg_type == MessageType.AGENT_STATUS:
                await self.handle_agent_status(client_id, payload)

            elif msg_type == MessageType.LOCK_UPDATE:
                await self.handle_lock_update(client_id, payload)

            elif msg_type == MessageType.TASK_UPDATE:
                await self.handle_task_update(client_id, payload)

            elif msg_type == MessageType.PATTERN_DETECTED:
                await self.handle_pattern_detected(client_id, payload)

            elif msg_type == MessageType.EXPERIENCE_SHARED:
                await self.handle_experience_shared(client_id, payload)

            else:
                # 转发到相关频道
                await self.broadcast_to_channel(
                    payload.get("channel", "global"),
                    WebSocketMessage(type=msg_type, payload=payload, sender=client_id)
                )

        except json.JSONDecodeError:
            logger.error(f"无效的JSON消息 from {client_id}: {message}")

        except Exception as e:
            logger.error(f"消息处理错误 from {client_id}: {e}")
            self.stats["errors"] += 1

    async def handle_heartbeat(self, client_id: str):
        """处理心跳"""
        client = self.clients.get(client_id)
        if client:
            client.last_heartbeat = datetime.now()
            await self.send_to_client(
                client_id,
                WebSocketMessage(
                    type=MessageType.HEARTBEAT,
                    payload={"status": "alive"}
                )
            )

    async def handle_agent_status(self, client_id: str, payload: Dict):
        """处理代理状态更新"""
        agent_id = payload.get("agent_id")
        status = payload.get("status")

        # 更新客户端的代理ID
        client = self.clients.get(client_id)
        if client:
            client.agent_id = agent_id

        # 广播给所有订阅者
        await self.broadcast_to_channel(
            f"agent:{agent_id}",
            WebSocketMessage(
                type=MessageType.AGENT_STATUS,
                payload=payload,
                sender=client_id
            )
        )

        # 记录到Redis
        if self.redis_client:
            await self.redis_client.hset(
                f"agent:status:{agent_id}",
                mapping={
                    "status": status,
                    "updated_by": client_id,
                    "updated_at": datetime.now().isoformat()
                }
            )

    async def handle_lock_update(self, client_id: str, payload: Dict):
        """处理锁更新"""
        lock_id = payload.get("lock_id")
        action = payload.get("action")  # acquire, release, wait

        # 广播锁更新
        await self.broadcast_to_channel(
            "locks",
            WebSocketMessage(
                type=MessageType.LOCK_UPDATE,
                payload=payload,
                sender=client_id
            )
        )

        # 如果是冲突，发送警告
        if action == "conflict":
            await self.broadcast_to_channel(
                "alerts",
                WebSocketMessage(
                    type=MessageType.CONFLICT_ALERT,
                    payload={
                        "lock_id": lock_id,
                        "message": "Lock conflict detected",
                        "severity": "warning"
                    }
                )
            )

    async def handle_task_update(self, client_id: str, payload: Dict):
        """处理任务更新"""
        task_id = payload.get("task_id")
        status = payload.get("status")

        # 广播任务更新
        await self.broadcast_to_channel(
            f"task:{task_id}",
            WebSocketMessage(
                type=MessageType.TASK_UPDATE,
                payload=payload,
                sender=client_id
            )
        )

        # 发送进度更新
        if "progress" in payload:
            await self.broadcast_to_channel(
                "progress",
                WebSocketMessage(
                    type=MessageType.PROGRESS_UPDATE,
                    payload={
                        "task_id": task_id,
                        "progress": payload["progress"]
                    }
                )
            )

    async def handle_pattern_detected(self, client_id: str, payload: Dict):
        """处理模式检测"""
        pattern_type = payload.get("pattern_type")
        pattern_name = payload.get("pattern_name")

        # 广播模式检测
        await self.broadcast_to_channel(
            "patterns",
            WebSocketMessage(
                type=MessageType.PATTERN_DETECTED,
                payload=payload,
                sender=client_id
            )
        )

        # 如果是反模式，发送警告
        if pattern_type == "anti_pattern":
            await self.broadcast_to_channel(
                "alerts",
                WebSocketMessage(
                    type=MessageType.SYSTEM_ALERT,
                    payload={
                        "type": "anti_pattern",
                        "message": f"Anti-pattern detected: {pattern_name}",
                        "severity": "warning"
                    }
                )
            )

    async def handle_experience_shared(self, client_id: str, payload: Dict):
        """处理经验共享"""
        experience_id = payload.get("experience_id")
        target_project = payload.get("target_project")

        # 广播经验共享
        await self.broadcast_to_channel(
            f"project:{target_project}",
            WebSocketMessage(
                type=MessageType.EXPERIENCE_SHARED,
                payload=payload,
                sender=client_id
            )
        )

        # 发送学习更新
        await self.broadcast_to_channel(
            "learning",
            WebSocketMessage(
                type=MessageType.LEARNING_UPDATE,
                payload={
                    "type": "experience_shared",
                    "experience_id": experience_id,
                    "shared_to": target_project
                }
            )
        )

    async def send_to_client(self, client_id: str, message: WebSocketMessage):
        """
        发送消息给特定客户端

        Args:
            client_id: 客户端ID
            message: 消息
        """
        client = self.clients.get(client_id)
        if client:
            try:
                await client.websocket.send(message.to_json())
                self.stats["messages_sent"] += 1

            except Exception as e:
                logger.error(f"发送消息失败 to {client_id}: {e}")
                await self.remove_client(client_id)

    async def broadcast_to_channel(self, channel: str, message: WebSocketMessage):
        """
        广播消息到频道

        Args:
            channel: 频道名称
            message: 消息
        """
        client_ids = self.channels.get(channel, set())

        # 并发发送
        tasks = [
            self.send_to_client(client_id, message)
            for client_id in client_ids
            if client_id in self.clients
        ]

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        # 发布到Redis（跨服务器）
        if self.redis_client:
            await self.redis_client.publish(
                f"websocket:channel:{channel}",
                message.to_json()
            )

    async def broadcast_to_all(self, message: WebSocketMessage):
        """广播消息给所有客户端"""
        tasks = [
            self.send_to_client(client_id, message)
            for client_id in self.clients.keys()
        ]

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def subscribe_client_to_channel(self, client_id: str, channel: str):
        """
        订阅客户端到频道

        Args:
            client_id: 客户端ID
            channel: 频道名称
        """
        if channel not in self.channels:
            self.channels[channel] = set()

        self.channels[channel].add(client_id)

        client = self.clients.get(client_id)
        if client:
            client.subscriptions.add(channel)

        logger.info(f"客户端 {client_id} 订阅频道 {channel}")

    async def unsubscribe_client_from_channel(self, client_id: str, channel: str):
        """
        取消客户端的频道订阅

        Args:
            client_id: 客户端ID
            channel: 频道名称
        """
        if channel in self.channels:
            self.channels[channel].discard(client_id)

            if not self.channels[channel]:
                del self.channels[channel]

        client = self.clients.get(client_id)
        if client:
            client.subscriptions.discard(channel)

        logger.info(f"客户端 {client_id} 取消订阅频道 {channel}")

    async def remove_client(self, client_id: str):
        """
        移除客户端

        Args:
            client_id: 客户端ID
        """
        client = self.clients.get(client_id)
        if not client:
            return

        # 从所有频道取消订阅
        for channel in list(client.subscriptions):
            await self.unsubscribe_client_from_channel(client_id, channel)

        # 删除客户端
        del self.clients[client_id]

        if client.websocket in self.websocket_to_client:
            del self.websocket_to_client[client.websocket]

        # 广播断开连接消息
        await self.broadcast_to_channel(
            "global",
            WebSocketMessage(
                type=MessageType.DISCONNECT,
                payload={"client_id": client_id}
            )
        )

        logger.info(f"客户端移除: {client_id}")

    async def redis_listener(self):
        """监听Redis消息"""
        if not self.pubsub:
            return

        try:
            async for message in self.pubsub.listen():
                if message["type"] == "message":
                    # 转发Redis消息到本地客户端
                    channel = message["channel"].replace("websocket:", "")
                    data = json.loads(message["data"])

                    # 不转发自己发送的消息
                    if data.get("sender") not in self.clients:
                        msg = WebSocketMessage(
                            type=MessageType(data["type"]),
                            payload=data["payload"],
                            sender=data.get("sender"),
                            timestamp=data.get("timestamp")
                        )

                        if channel == "broadcast":
                            await self.broadcast_to_all(msg)
                        elif channel.startswith("channel:"):
                            channel_name = channel.replace("channel:", "")
                            await self.broadcast_to_channel(channel_name, msg)

        except Exception as e:
            logger.error(f"Redis监听错误: {e}")

    async def heartbeat_checker(self):
        """定期检查心跳"""
        while True:
            try:
                await asyncio.sleep(60)  # 每分钟检查一次

                now = datetime.now()
                timeout_clients = []

                for client_id, client in self.clients.items():
                    if hasattr(client, "last_heartbeat"):
                        if (now - client.last_heartbeat).seconds > 120:  # 2分钟超时
                            timeout_clients.append(client_id)

                # 移除超时客户端
                for client_id in timeout_clients:
                    logger.warning(f"客户端心跳超时: {client_id}")
                    await self.remove_client(client_id)

            except Exception as e:
                logger.error(f"心跳检查错误: {e}")

    def generate_client_id(self) -> str:
        """生成客户端ID"""
        import uuid
        return f"client_{uuid.uuid4().hex[:8]}"

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            "active_connections": len(self.clients),
            "active_channels": len(self.channels),
            "clients": [
                {
                    "client_id": client.client_id,
                    "agent_id": client.agent_id,
                    "subscriptions": list(client.subscriptions),
                    "connected_at": client.connected_at.isoformat()
                }
                for client in self.clients.values()
            ]
        }

# ============================================
# 启动函数
# ============================================

async def run_websocket_server(host: str = "0.0.0.0", port: int = 8766):
    """运行WebSocket服务器"""
    server = WebSocketServer(host, port)
    await server.start()

if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 运行服务器
    asyncio.run(run_websocket_server())
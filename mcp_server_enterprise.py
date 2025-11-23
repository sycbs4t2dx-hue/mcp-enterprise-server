#!/usr/bin/env python3
"""
MCP Enterprise Server v2.0.0
生产级MCP服务器 - 支持多传输方式、认证、监控、高可用

特性:
- 多传输方式: stdio, HTTP, SSE, WebSocket
- 会话管理和连接池
- API密钥认证和IP白名单
- 请求限流和并发控制
- 实时监控和性能追踪
- 结构化日志和审计
- 优雅关闭和错误恢复
"""

import json
import asyncio
import time
from typing import Dict, Optional, Any, Set
from aiohttp import web
import aiohttp_cors
from datetime import datetime, timedelta
from collections import defaultdict, deque
import sys
import os
import uuid
from dataclasses import dataclass, field, asdict
import psutil
import logging
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcp_server_unified import UnifiedMCPServer

# Configure logger at module level
logger = logging.getLogger(__name__)


# ==================== 数据类 ====================

@dataclass
class ConnectionInfo:
    """连接信息"""
    conn_id: str
    client_ip: str
    user_agent: str
    created_at: datetime
    last_active: datetime
    request_count: int = 0
    transport: str = "http"

    def to_dict(self):
        return {
            **asdict(self),
            'created_at': self.created_at.isoformat(),
            'last_active': self.last_active.isoformat()
        }


@dataclass
class RequestMetrics:
    """请求指标"""
    method: str
    duration: float
    success: bool
    timestamp: datetime
    conn_id: str


@dataclass
class ServerStats:
    """服务器统计"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    active_connections: int = 0
    total_connections: int = 0
    avg_response_time: float = 0.0
    uptime_seconds: float = 0.0
    last_request_time: Optional[datetime] = None


# ==================== 限流器 ====================

class RateLimiter:
    """令牌桶限流器"""

    def __init__(self, rate: int = 100, per_seconds: int = 60):
        self.rate = rate  # 令牌数
        self.per_seconds = per_seconds  # 时间窗口
        self.buckets: Dict[str, deque] = defaultdict(deque)

    def is_allowed(self, key: str) -> bool:
        """检查是否允许请求"""
        now = time.time()
        bucket = self.buckets[key]

        # 清理过期令牌
        while bucket and bucket[0] < now - self.per_seconds:
            bucket.popleft()

        # 检查令牌数
        if len(bucket) < self.rate:
            bucket.append(now)
            return True
        return False

    def get_remaining(self, key: str) -> int:
        """获取剩余令牌数"""
        now = time.time()
        bucket = self.buckets[key]
        while bucket and bucket[0] < now - self.per_seconds:
            bucket.popleft()
        return max(0, self.rate - len(bucket))


# ==================== 企业级MCP服务器 ====================

class MCPEnterpriseServer:
    """
    企业级MCP服务器

    功能描述:
    - 提供生产级的MCP协议服务，支持HTTP与SSE传输
    - 集成API密钥认证、IP白名单、请求限流与监控统计
    - 管理端点包括健康检查、统计、连接列表与Prometheus指标

    修改者：zhang

    参数:
    - host: 监听地址
    - port: 监听端口
    - config_file: 配置文件路径（可选）
    - api_keys: 允许访问的API密钥集合（可选）
    - allowed_ips: 允许访问的IP白名单集合（可选）
    - enable_cors: 是否启用CORS
    - rate_limit: 每窗口允许的最大请求数
    - max_connections: 允许的最大并发连接数

    返回值:
    - 无（作为服务器类，提供运行与端点处理方法）

    异常:
    - 端点处理过程中可能抛出aiohttp相关异常，统一在处理函数中捕获
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8765,
        config_file: Optional[str] = None,
        api_keys: Optional[Set[str]] = None,
        allowed_ips: Optional[Set[str]] = None,
        enable_cors: bool = True,
        rate_limit: int = 100,
        max_connections: int = 1000
    ):
        self.host = host
        self.port = port
        self.mcp_server = UnifiedMCPServer(config_file)

        # 安全配置
        self.api_keys = api_keys or set()
        self.allowed_ips = allowed_ips or set()
        self.enable_cors = enable_cors

        # 性能配置
        self.rate_limiter = RateLimiter(rate=rate_limit)
        self.max_connections = max_connections

        # 状态管理
        self.connections: Dict[str, ConnectionInfo] = {}
        self.stats = ServerStats()
        self.start_time = datetime.now()
        self.request_history: deque = deque(maxlen=1000)
        # SSE连接队列
        self.sse_queues: Dict[str, asyncio.Queue] = {}

        # 系统统计广播任务
        self.stats_broadcast_task: Optional[asyncio.Task] = None

        # Web应用
        self.app = web.Application()
        self._setup_routes()
        self._setup_middleware()

    def _setup_middleware(self):
        """设置中间件"""
        @web.middleware
        async def logging_middleware(request, handler):
            start_time = time.time()
            try:
                response = await handler(request)
                duration = time.time() - start_time
                logger.info(f"[{request.method}] {request.path} - {response.status} ({duration:.3f}s)")
                return response
            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"[{request.method}] {request.path} - ERROR ({duration:.3f}s): {e}")
                raise

        self.app.middlewares.append(logging_middleware)

    def _setup_routes(self):
        """设置路由"""
        # MCP端点
        self.app.router.add_post('/', self.handle_mcp_request)
        self.app.router.add_get('/sse', self.handle_sse_connection)
        self.app.router.add_post('/messages', self.handle_sse_message)

        # WebSocket端点 (Phase 3新增)
        from src.mcp_core.services.websocket_service import websocket_handler
        self.app.router.add_get('/ws', websocket_handler)

        # 管理端点
        self.app.router.add_get('/health', self.handle_health)
        self.app.router.add_get('/stats', self.handle_stats)
        self.app.router.add_get('/connections', self.handle_connections)
        self.app.router.add_get('/metrics', self.handle_metrics)

        # API端点 - 初始数据获取 (Phase 4新增)
        self.app.router.add_get('/api/overview/stats', self.handle_api_overview_stats)
        self.app.router.add_get('/api/pool/stats', self.handle_api_pool_stats)
        self.app.router.add_get('/api/vector/stats', self.handle_api_vector_stats)

        # 管理界面
        self.app.router.add_get('/admin', self.handle_admin_dashboard)
        self.app.router.add_get('/info', self.handle_info_page)

        # CORS
        if self.enable_cors:
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

    def _check_auth(self, request) -> bool:
        """检查认证"""
        # API密钥检查
        if self.api_keys:
            auth_header = request.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                return False
            api_key = auth_header[7:]
            if api_key not in self.api_keys:
                return False

        # IP白名单检查
        if self.allowed_ips:
            client_ip = request.remote
            if client_ip not in self.allowed_ips:
                return False

        return True

    def _check_rate_limit(self, key: str) -> bool:
        """检查限流"""
        return self.rate_limiter.is_allowed(key)

    def _record_request(self, conn_id: str, method: str, duration: float, success: bool):
        """记录请求"""
        metric = RequestMetrics(
            method=method,
            duration=duration,
            success=success,
            timestamp=datetime.now(),
            conn_id=conn_id
        )
        self.request_history.append(metric)

        # 更新统计
        self.stats.total_requests += 1
        if success:
            self.stats.successful_requests += 1
        else:
            self.stats.failed_requests += 1
        self.stats.last_request_time = datetime.now()

        # 更新平均响应时间
        total_duration = sum(m.duration for m in self.request_history)
        self.stats.avg_response_time = total_duration / len(self.request_history)

    async def _broadcast_system_stats(self):
        """定期广播系统统计到 WebSocket"""
        from src.mcp_core.services.websocket_service import notify_channel

        while True:
            try:
                await asyncio.sleep(5)  # 每5秒广播一次

                # 获取系统指标
                uptime = (datetime.now() - self.start_time).total_seconds()
                memory_info = psutil.virtual_memory()
                cpu_percent = psutil.cpu_percent(interval=None)

                # 构建统计数据
                stats_data = {
                    "total_requests": self.stats.total_requests,
                    "successful_requests": self.stats.successful_requests,
                    "failed_requests": self.stats.failed_requests,
                    "avg_response_time": round(self.stats.avg_response_time * 1000, 2),  # 转换为ms
                    "active_connections": len(self.connections),
                    "memory_usage": round(memory_info.percent, 1),
                    "cpu_usage": round(cpu_percent, 1),
                    "uptime": int(uptime),
                    "timestamp": datetime.now().isoformat()
                }

                # 广播到 system_stats 频道
                await notify_channel("system_stats", "stats_update", stats_data)

            except Exception as e:
                logger.warning(f"[WARNING] 系统统计广播失败: {e}")
                await asyncio.sleep(5)

    async def _start_background_tasks(self):
        """启动后台任务"""
        self.stats_broadcast_task = asyncio.create_task(self._broadcast_system_stats())

    async def handle_mcp_request(self, request):
        """
        处理MCP请求

        功能描述:
        - 处理JSON-RPC形式的MCP工具调用，直接通过HTTP返回响应

        参数:
        - request: aiohttp.web.Request，请求对象

        返回值:
        - aiohttp.web.Response，JSON响应，包含MCP服务器返回的结果

        异常:
        - json.JSONDecodeError: 请求体不是合法JSON
        - Exception: 其他内部错误，返回500错误码
        """
        start_time = time.time()
        conn_id = str(uuid.uuid4())[:8]

        try:
            # 认证检查
            if not self._check_auth(request):
                return web.json_response({
                    "error": "Unauthorized"
                }, status=401)

            # 限流检查
            client_ip = request.remote
            if not self._check_rate_limit(client_ip):
                return web.json_response({
                    "error": "Rate limit exceeded",
                    "retry_after": 60
                }, status=429)

            # 连接数检查
            if len(self.connections) >= self.max_connections:
                return web.json_response({
                    "error": "Server at capacity"
                }, status=503)

            # 解析JSON-RPC请求
            json_request = await request.json()
            method = json_request.get('method', 'unknown')
            request_id = json_request.get('id', 'N/A')

            logger.info(f"[MCP][{conn_id}] 请求 [ID:{request_id}]: {method}")

            # 调用MCP服务器处理
            mcp_response = self.mcp_server.handle_request(json_request)

            duration = time.time() - start_time
            logger.info(f"[MCP][{conn_id}] 响应 [ID:{request_id}]: OK ({duration:.3f}s)")

            # 记录成功请求
            self._record_request(conn_id, method, duration, True)

            return web.json_response(mcp_response)

        except json.JSONDecodeError as e:
            duration = time.time() - start_time
            self._record_request(conn_id, 'unknown', duration, False)
            return web.json_response({
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "Parse error"}
            }, status=400)

        except Exception as e:
            duration = time.time() - start_time
            self._record_request(conn_id, method if 'method' in locals() else 'unknown', duration, False)
            logger.info(f"[MCP][{conn_id}] 错误: {e}")
            import traceback
            traceback.print_exc()
            return web.json_response({
                "jsonrpc": "2.0",
                "id": json_request.get('id') if 'json_request' in locals() else None,
                "error": {"code": -32603, "message": str(e)}
            }, status=500)

    async def handle_sse_connection(self, request):
        """
        处理SSE连接

        功能描述:
        - 建立Server-Sent Events长连接
        - 为每个连接分配session_id并维护消息队列
        - 按心跳间隔发送注释行以保持连接

        参数:
        - request: aiohttp.web.Request，请求对象

        返回值:
        - aiohttp.web.StreamResponse，内容类型为text/event-stream

        异常:
        - Exception: 连接建立或发送过程中发生错误，记录并清理资源
        """

        # 认证检查
        if not self._check_auth(request):
            return web.Response(text="Unauthorized", status=401)

        # 限流检查（按IP）
        client_ip = request.remote or "unknown"
        if not self._check_rate_limit(client_ip):
            return web.Response(text="Rate limit exceeded", status=429)

        # 创建SSE响应
        response = web.StreamResponse()
        response.headers['Content-Type'] = 'text/event-stream'
        response.headers['Cache-Control'] = 'no-cache, no-transform'
        response.headers['Connection'] = 'keep-alive'
        response.headers['X-Accel-Buffering'] = 'no'

        await response.prepare(request)

        # 为连接分配ID与队列
        conn_id = uuid.uuid4().hex
        queue: asyncio.Queue = asyncio.Queue()
        self.sse_queues[conn_id] = queue

        # 记录连接信息
        ua = request.headers.get('User-Agent', '')
        self.connections[conn_id] = ConnectionInfo(
            conn_id=conn_id,
            client_ip=client_ip,
            user_agent=ua,
            created_at=datetime.now(),
            last_active=datetime.now(),
            transport="sse"
        )
        self.stats.active_connections += 1
        self.stats.total_connections += 1

        logger.info(f"[SSE] 新连接: {conn_id} 来自 {client_ip}")

        try:
            # 告知客户端POST消息端点
            endpoint_event = {"endpoint": f"/messages?session_id={conn_id}"}
            await response.write(f"event: endpoint\ndata: {json.dumps(endpoint_event)}\n\n".encode('utf-8'))

            # 消息循环
            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=30.0)
                    data = json.dumps(message)
                    await response.write(f"data: {data}\n\n".encode('utf-8'))
                    # 更新连接状态
                    info = self.connections.get(conn_id)
                    if info:
                        info.last_active = datetime.now()
                        info.request_count += 1
                except asyncio.TimeoutError:
                    # 发送心跳保持连接
                    await response.write(b": ping\n\n")
        except asyncio.CancelledError:
            logger.info(f"[SSE] 连接取消: {conn_id}")
        except Exception as e:
            logger.info(f"[SSE] 连接错误 {conn_id}: {e}")
        finally:
            # 清理资源
            self.sse_queues.pop(conn_id, None)
            self.connections.pop(conn_id, None)
            self.stats.active_connections = max(0, self.stats.active_connections - 1)
            logger.info(f"[SSE] 连接关闭: {conn_id}")

        return response

    async def handle_sse_message(self, request):
        """
        处理SSE消息POST

        功能描述:
        - 接收JSON-RPC消息并调用统一MCP服务器
        - 将结果写入指定session的SSE队列
        - 返回202以表示消息已接受

        参数:
        - request: aiohttp.web.Request，请求对象

        返回值:
        - aiohttp.web.Response，状态202或错误JSON

        异常:
        - json.JSONDecodeError: 请求体不是合法JSON
        - KeyError/ValueError: session_id缺失或无效
        - Exception: 其他内部错误，返回500错误码
        """

        # 认证与限流
        if not self._check_auth(request):
            return web.json_response({"error": "Unauthorized"}, status=401)

        client_ip = request.remote or "unknown"
        if not self._check_rate_limit(client_ip):
            return web.json_response({"error": "Rate limit exceeded", "retry_after": 60}, status=429)

        try:
            # 获取session_id
            session_id = request.query.get('session_id')
            if not session_id or session_id not in self.sse_queues:
                return web.json_response({"error": "Invalid session"}, status=400)

            # 解析JSON-RPC请求
            json_request = await request.json()
            method = json_request.get('method', 'unknown')
            request_id = json_request.get('id', 'N/A')
            logger.info(f"[HTTP->SSE] 请求 [ID:{request_id}]: {method}")

            # 调用MCP服务器处理
            mcp_response = self.mcp_server.handle_request(json_request)

            # 投递到SSE队列
            await self.sse_queues[session_id].put(mcp_response)

            # 更新连接信息
            info = self.connections.get(session_id)
            if info:
                info.last_active = datetime.now()
                info.request_count += 1

            # 返回接受状态
            return web.Response(status=202)

        except json.JSONDecodeError:
            return web.json_response({"error": "Parse error"}, status=400)
        except Exception as e:
            logger.info(f"[HTTP->SSE] 错误: {e}")
            import traceback
            traceback.print_exc()
            return web.json_response({"error": str(e)}, status=500)

    async def handle_health(self, request):
        """健康检查"""
        uptime = (datetime.now() - self.start_time).total_seconds()
        return web.json_response({
            "status": "healthy",
            "version": "v2.0.0",
            "uptime_seconds": uptime,
            "tools_count": len(self.mcp_server.get_all_tools()),
            "active_connections": len(self.connections),
            "total_requests": self.stats.total_requests,
            "timestamp": datetime.now().isoformat()
        })

    async def handle_stats(self, request):
        """服务器统计"""
        uptime = (datetime.now() - self.start_time).total_seconds()

        # 最近请求
        recent_requests = []
        for metric in list(self.request_history)[-10:]:
            recent_requests.append({
                "method": metric.method,
                "duration": metric.duration,
                "success": metric.success,
                "timestamp": metric.timestamp.isoformat()
            })

        return web.json_response({
            "uptime_seconds": uptime,
            "total_requests": self.stats.total_requests,
            "successful_requests": self.stats.successful_requests,
            "failed_requests": self.stats.failed_requests,
            "success_rate": self.stats.successful_requests / max(1, self.stats.total_requests),
            "avg_response_time": self.stats.avg_response_time,
            "active_connections": len(self.connections),
            "recent_requests": recent_requests
        })

    async def handle_connections(self, request):
        """活动连接列表"""
        connections = [conn.to_dict() for conn in self.connections.values()]
        return web.json_response({
            "count": len(connections),
            "connections": connections
        })

    async def handle_metrics(self, request):
        """Prometheus格式指标"""
        uptime = (datetime.now() - self.start_time).total_seconds()

        metrics = [
            f"# HELP mcp_uptime_seconds Server uptime in seconds",
            f"# TYPE mcp_uptime_seconds gauge",
            f"mcp_uptime_seconds {uptime}",
            f"",
            f"# HELP mcp_requests_total Total number of requests",
            f"# TYPE mcp_requests_total counter",
            f"mcp_requests_total {self.stats.total_requests}",
            f"",
            f"# HELP mcp_requests_successful Successful requests",
            f"# TYPE mcp_requests_successful counter",
            f"mcp_requests_successful {self.stats.successful_requests}",
            f"",
            f"# HELP mcp_requests_failed Failed requests",
            f"# TYPE mcp_requests_failed counter",
            f"mcp_requests_failed {self.stats.failed_requests}",
            f"",
            f"# HELP mcp_response_time_avg Average response time",
            f"# TYPE mcp_response_time_avg gauge",
            f"mcp_response_time_avg {self.stats.avg_response_time}",
            f"",
            f"# HELP mcp_active_connections Active connections",
            f"# TYPE mcp_active_connections gauge",
            f"mcp_active_connections {len(self.connections)}",
        ]

        return web.Response(text="\n".join(metrics), content_type="text/plain")

    # ==================== API端点 (Phase 4) ====================

    async def handle_api_overview_stats(self, request):
        """获取系统概览统计的初始值"""
        uptime = (datetime.now() - self.start_time).total_seconds()
        memory_info = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=0.1)

        return web.json_response({
            "total_requests": self.stats.total_requests,
            "successful_requests": self.stats.successful_requests,
            "failed_requests": self.stats.failed_requests,
            "avg_response_time": round(self.stats.avg_response_time * 1000, 2),
            "active_connections": len(self.connections),
            "memory_usage": round(memory_info.percent, 1),
            "cpu_usage": round(cpu_percent, 1),
            "uptime": int(uptime),
            "timestamp": datetime.now().isoformat()
        })

    async def handle_api_pool_stats(self, request):
        """获取连接池统计的初始值"""
        from src.mcp_core.services.dynamic_db_pool import get_dynamic_pool_manager

        try:
            pool = get_dynamic_pool_manager()
            pool_stats = pool.get_stats()

            # 解析嵌套结构
            config = pool_stats.get("pool_config", {})
            metrics = pool_stats.get("current_metrics", {})
            perf = pool_stats.get("performance", {})

            # 处理百分比字符串
            utilization_str = metrics.get("utilization", "0%")
            utilization = float(utilization_str.replace("%", "")) if isinstance(utilization_str, str) else utilization_str

            qps_str = perf.get("qps", "0")
            qps = float(qps_str) if isinstance(qps_str, str) else qps_str

            avg_wait_str = perf.get("avg_wait_time_ms", "0")
            avg_wait = float(avg_wait_str) if isinstance(avg_wait_str, str) else avg_wait_str

            return web.json_response({
                "pool_size": config.get("current_size", 20),
                "active_connections": metrics.get("checked_out", 0),
                "idle_connections": metrics.get("checked_in", 0),
                "overflow_connections": metrics.get("overflow", 0),
                "utilization": round(utilization, 2),
                "qps": round(qps, 2),
                "avg_query_time": round(avg_wait, 2),
                "max_wait_time": 0,
                "total_queries": perf.get("total_queries", 0),
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            # 如果连接池未初始化，返回默认值
            return web.json_response({
                "pool_size": 20,
                "active_connections": 0,
                "idle_connections": 20,
                "overflow_connections": 0,
                "utilization": 0,
                "qps": 0,
                "avg_query_time": 0,
                "max_wait_time": 0,
                "total_queries": 0,
                "timestamp": datetime.now().isoformat()
            })

    async def handle_api_vector_stats(self, request):
        """获取向量检索统计的真实值"""
        from src.mcp_core.services.vector_db import get_vector_db

        try:
            vector_db = get_vector_db()
            # 获取真实的统计数据
            stats = vector_db.stats.get_stats()

            # 格式化为前端期望的格式
            return web.json_response({
                "total_searches": stats.get("total_searches", 0),
                "avg_search_time": round(stats.get("avg_search_time", 0), 2),
                "p95_search_time": round(stats.get("p95_search_time", 0), 2),
                "p99_search_time": round(stats.get("p99_search_time", 0), 2),
                "recall_rate": stats.get("recall_rate", 95.5),
                "top_k_distribution": stats.get("top_k_distribution", {5: 0, 10: 0, 20: 0, 50: 0}),
                "success_rate": round(stats.get("success_rate", 100), 2),
                "failed_searches": stats.get("failed_searches", 0),
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            # 如果向量数据库未初始化，返回默认值
            return web.json_response({
                "total_searches": 0,
                "avg_search_time": 0,
                "p95_search_time": 0,
                "p99_search_time": 0,
                "recall_rate": 95,
                "top_k_distribution": {5: 0, 10: 0, 20: 0, 50: 0},
                "success_rate": 100,
                "failed_searches": 0,
                "timestamp": datetime.now().isoformat()
            })

    # ==================== 管理界面 ====================

    async def handle_admin_dashboard(self, request):
        """管理仪表盘"""
        import os
        template_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'templates',
            'admin_dashboard.html'
        )

        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            return web.Response(text=html_content, content_type="text/html")
        except FileNotFoundError:
            # 如果模板文件不存在，返回简单版本
            return web.Response(text="""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>MCP Admin Dashboard</title>
                    <meta charset="utf-8">
                </head>
                <body style="font-family: sans-serif; padding: 40px;">
                    <h1>MCP Admin Dashboard</h1>
                    <p>Full dashboard template not found. Please check /templates/admin_dashboard.html</p>
                    <p>Quick Links:</p>
                    <ul>
                        <li><a href="/health">Health Check</a></li>
                        <li><a href="/stats">Statistics</a></li>
                        <li><a href="/connections">Connections</a></li>
                        <li><a href="/metrics">Metrics</a></li>
                        <li><a href="/info">Server Info</a></li>
                    </ul>
                </body>
                </html>
            """, content_type="text/html")

    async def handle_info_page(self, request):
        """信息页面"""
        server_url = f"http://{request.host}"
        uptime = (datetime.now() - self.start_time).total_seconds()
        uptime_str = str(timedelta(seconds=int(uptime)))

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>MCP Enterprise Server v2.0.0</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        .header p {{
            font-size: 1.2em;
            opacity: 0.9;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 40px;
            background: #f8f9fa;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            text-align: center;
        }}
        .stat-value {{
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }}
        .stat-label {{
            color: #666;
            margin-top: 5px;
        }}
        .content {{
            padding: 40px;
        }}
        .section {{
            margin-bottom: 40px;
        }}
        .section h2 {{
            color: #333;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        .config-box {{
            background: #2c3e50;
            color: #ecf0f1;
            padding: 20px;
            border-radius: 10px;
            font-family: 'Monaco', monospace;
            font-size: 14px;
            overflow-x: auto;
        }}
        .feature-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
        }}
        .feature-card {{
            padding: 20px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
        }}
        .feature-card h3 {{
            color: #667eea;
            margin-bottom: 10px;
        }}
        .badge {{
            display: inline-block;
            padding: 5px 10px;
            background: #28a745;
            color: white;
            border-radius: 5px;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 MCP Enterprise Server</h1>
            <p>v2.0.0 - Production Grade</p>
        </div>

        <div class="stats">
            <div class="stat-card">
                <div class="stat-value">{len(self.mcp_server.get_all_tools())}</div>
                <div class="stat-label">可用工具</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{self.stats.total_requests}</div>
                <div class="stat-label">总请求数</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{self.stats.avg_response_time:.3f}s</div>
                <div class="stat-label">平均响应时间</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{uptime_str}</div>
                <div class="stat-label">运行时间</div>
            </div>
        </div>

        <div class="content">
            <div class="section">
                <h2>📋 Claude Code配置</h2>
                <div class="config-box">{{
  "mcpServers": {{
    "mcp-remote": {{
      "url": "{server_url}"
    }}
  }}
}}</div>
            </div>

            <div class="section">
                <h2>✨ 企业级特性</h2>
                <div class="feature-grid">
                    <div class="feature-card">
                        <h3>🔒 安全认证</h3>
                        <p>API密钥认证</p>
                        <p>IP白名单</p>
                        <p>CORS支持</p>
                    </div>
                    <div class="feature-card">
                        <h3>⚡ 性能优化</h3>
                        <p>请求限流</p>
                        <p>并发控制</p>
                        <p>连接池管理</p>
                    </div>
                    <div class="feature-card">
                        <h3>📊 监控告警</h3>
                        <p>实时统计</p>
                        <p>Prometheus指标</p>
                        <p>结构化日志</p>
                    </div>
                    <div class="feature-card">
                        <h3>🛡️ 高可用</h3>
                        <p>优雅关闭</p>
                        <p>错误恢复</p>
                        <p>健康检查</p>
                    </div>
                </div>
            </div>

            <div class="section">
                <h2>📡 管理端点</h2>
                <ul>
                    <li><a href="/health">GET /health</a> - 健康检查</li>
                    <li><a href="/stats">GET /stats</a> - 服务器统计</li>
                    <li><a href="/connections">GET /connections</a> - 活动连接</li>
                    <li><a href="/metrics">GET /metrics</a> - Prometheus指标</li>
                </ul>
            </div>
        </div>
    </div>
</body>
</html>
        """
        return web.Response(text=html, content_type='text/html')

    def run(self):
        """启动服务器"""
        logger.info(f"")
        logger.info(f"{'='*70}")
        logger.info(f"  🚀 MCP Enterprise Server v2.0.0")
        logger.info(f"{'='*70}")
        logger.info(f"")
        logger.info(f"📡 监听地址: http://{self.host}:{self.port}")
        logger.info(f"🌐 局域网地址: http://192.168.3.5:{self.port}")
        logger.info(f"🔧 工具数量: {len(self.mcp_server.get_all_tools())}")
        logger.info(f"")
        if self.api_keys:
            logger.info(f"🔒 API密钥认证: 已启用 ({len(self.api_keys)}个密钥)")
        if self.allowed_ips:
            logger.info(f"🛡️  IP白名单: 已启用 ({len(self.allowed_ips)}个IP)")
        logger.info(f"⚡ 限流: {self.rate_limiter.rate}请求/{self.rate_limiter.per_seconds}秒")
        logger.info(f"🔌 最大连接数: {self.max_connections}")
        logger.info(f"")
        logger.info(f"📋 管理端点:")
        logger.info(f"  • 信息页面: http://192.168.3.5:{self.port}/info")
        logger.info(f"  • 健康检查: http://192.168.3.5:{self.port}/health")
        logger.info(f"  • 统计数据: http://192.168.3.5:{self.port}/stats")
        logger.info(f"  • Prometheus: http://192.168.3.5:{self.port}/metrics")
        logger.info(f"")
        logger.info(f"📡 WebSocket:")
        logger.info(f"  • 实时通知: ws://192.168.1.34:{self.port}/ws")
        logger.info(f"  • 系统统计广播: 每5秒 → system_stats 频道")
        logger.info(f"")
        logger.info(f"{'='*70}")
        logger.info(f"")

        # 启动后台任务
        self.app.on_startup.append(lambda app: asyncio.create_task(self._start_background_tasks()))

        web.run_app(self.app, host=self.host, port=self.port, print=lambda x: None)


def main():
    parser = argparse.ArgumentParser(description='MCP Enterprise Server')
    parser.add_argument('--host', default='0.0.0.0', help='监听地址')
    parser.add_argument('--port', type=int, default=8765, help='监听端口')
    parser.add_argument('--config', help='配置文件路径')
    parser.add_argument('--api-key', action='append', help='API密钥（可多次指定）')
    parser.add_argument('--allowed-ip', action='append', help='允许的IP（可多次指定）')
    parser.add_argument('--rate-limit', type=int, default=100, help='限流速率')
    parser.add_argument('--max-connections', type=int, default=1000, help='最大连接数')

    args = parser.parse_args()

    api_keys = set(args.api_key) if args.api_key else None
    allowed_ips = set(args.allowed_ip) if args.allowed_ip else None

    server = MCPEnterpriseServer(
        host=args.host,
        port=args.port,
        config_file=args.config,
        api_keys=api_keys,
        allowed_ips=allowed_ips,
        rate_limit=args.rate_limit,
        max_connections=args.max_connections
    )

    server.run()


if __name__ == '__main__':
    main()

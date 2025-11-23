"""
统一的API路由管理器
消除重复端点，提供一致的API接口
"""

from typing import Dict, Any, Optional, Callable
from aiohttp import web
import json
from datetime import datetime

from ..common.logger import get_logger

logger = get_logger(__name__)


class UnifiedAPIRouter:
    """
    统一的API路由管理器

    特性：
    - 合并相似功能的端点
    - 统一响应格式
    - 自动错误处理
    - API版本管理
    """

    def __init__(self, version: str = "v1"):
        """
        初始化API路由器

        Args:
            version: API版本
        """
        self.version = version
        self.routes = []
        self.middleware = []

    def add_route(
        self,
        method: str,
        path: str,
        handler: Callable,
        name: Optional[str] = None,
        auth_required: bool = False
    ):
        """
        添加路由

        Args:
            method: HTTP方法
            path: 路径
            handler: 处理函数
            name: 路由名称
            auth_required: 是否需要认证
        """
        # 添加版本前缀
        versioned_path = f"/api/{self.version}{path}"

        self.routes.append({
            "method": method,
            "path": versioned_path,
            "handler": self._wrap_handler(handler, auth_required),
            "name": name or f"{method.lower()}_{path.replace('/', '_')}"
        })

        logger.debug(f"注册路由: {method} {versioned_path}")

    def _wrap_handler(self, handler: Callable, auth_required: bool) -> Callable:
        """
        包装处理函数，添加统一的错误处理和响应格式
        """
        async def wrapped(request: web.Request) -> web.Response:
            try:
                # 认证检查
                if auth_required and not await self._check_auth(request):
                    return self._error_response(401, "Unauthorized")

                # 调用原始处理函数
                result = await handler(request)

                # 如果返回的是Response对象，直接返回
                if isinstance(result, web.Response):
                    return result

                # 否则包装为统一格式
                return self._success_response(result)

            except web.HTTPException:
                raise  # 保持HTTP异常原样
            except Exception as e:
                logger.error(f"API处理错误: {e}", exc_info=True)
                return self._error_response(500, str(e))

        return wrapped

    async def _check_auth(self, request: web.Request) -> bool:
        """检查认证（可扩展）"""
        # 简单的Bearer Token检查
        auth_header = request.headers.get("Authorization", "")
        return auth_header.startswith("Bearer ")

    def _success_response(self, data: Any, message: str = "Success") -> web.Response:
        """统一的成功响应"""
        return web.json_response({
            "success": True,
            "message": message,
            "data": data,
            "timestamp": datetime.now().isoformat()
        })

    def _error_response(self, status: int, message: str, details: Any = None) -> web.Response:
        """统一的错误响应"""
        return web.json_response({
            "success": False,
            "message": message,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }, status=status)

    def setup_routes(self, app: web.Application):
        """设置所有路由到应用"""
        for route in self.routes:
            app.router.add_route(
                route["method"],
                route["path"],
                route["handler"],
                name=route["name"]
            )


class UnifiedStatsAPI:
    """
    统一的统计API
    合并 /stats, /api/overview/stats, /api/pool/stats, /api/vector/stats
    """

    def __init__(self, server_instance):
        """
        初始化统计API

        Args:
            server_instance: 企业服务器实例
        """
        self.server = server_instance

    async def get_all_stats(self, request: web.Request) -> Dict[str, Any]:
        """
        获取所有统计信息（合并的端点）

        Query Params:
            - include: 逗号分隔的统计类型（system,pool,vector,connections）
            - format: 响应格式（json,prometheus）
        """
        from src.mcp_core.services.dynamic_db_pool import get_dynamic_pool_manager
        from src.mcp_core.services.vector_db import get_vector_db
        import psutil

        # 解析查询参数
        include = request.query.get("include", "system,pool,vector").split(",")
        format_type = request.query.get("format", "json")

        stats = {}

        # 系统统计
        if "system" in include:
            uptime = (datetime.now() - self.server.start_time).total_seconds()
            memory_info = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=0.1)

            stats["system"] = {
                "total_requests": self.server.stats.total_requests,
                "successful_requests": self.server.stats.successful_requests,
                "failed_requests": self.server.stats.failed_requests,
                "avg_response_time": round(self.server.stats.avg_response_time * 1000, 2),
                "active_connections": len(self.server.connections),
                "memory_usage": round(memory_info.percent, 1),
                "cpu_usage": round(cpu_percent, 1),
                "uptime": int(uptime),
                "success_rate": round(
                    (self.server.stats.successful_requests / max(1, self.server.stats.total_requests)) * 100,
                    2
                ),
                "last_request_time": (
                    self.server.stats.last_request_time.isoformat()
                    if self.server.stats.last_request_time else None
                )
            }

        # 连接池统计
        if "pool" in include:
            try:
                pool = get_dynamic_pool_manager()
                pool_stats = pool.get_stats()

                config = pool_stats.get("pool_config", {})
                metrics = pool_stats.get("current_metrics", {})
                perf = pool_stats.get("performance", {})

                # 解析百分比字符串
                utilization_str = metrics.get("utilization", "0%")
                utilization = float(utilization_str.replace("%", "")) if isinstance(utilization_str, str) else utilization_str

                qps_str = perf.get("qps", "0")
                qps = float(qps_str) if isinstance(qps_str, str) else qps_str

                avg_wait_str = perf.get("avg_wait_time_ms", "0")
                avg_wait = float(avg_wait_str) if isinstance(avg_wait_str, str) else avg_wait_str

                stats["pool"] = {
                    "pool_size": config.get("current_size", 20),
                    "active_connections": metrics.get("checked_out", 0),
                    "idle_connections": metrics.get("checked_in", 0),
                    "overflow_connections": metrics.get("overflow", 0),
                    "utilization": round(utilization, 2),
                    "qps": round(qps, 2),
                    "avg_query_time": round(avg_wait, 2),
                    "total_queries": perf.get("total_queries", 0),
                }
            except Exception as e:
                logger.error(f"获取连接池统计失败: {e}")
                stats["pool"] = {"error": str(e)}

        # 向量检索统计
        if "vector" in include:
            try:
                vector_db = get_vector_db()
                vector_stats = vector_db.stats.get_stats()

                stats["vector"] = {
                    "total_searches": vector_stats.get("total_searches", 0),
                    "avg_search_time": round(vector_stats.get("avg_search_time", 0), 2),
                    "p50_search_time": round(vector_stats.get("p50_search_time", 0), 2),
                    "p95_search_time": round(vector_stats.get("p95_search_time", 0), 2),
                    "p99_search_time": round(vector_stats.get("p99_search_time", 0), 2),
                    "recall_rate": vector_stats.get("recall_rate", 95.5),
                    "success_rate": round(vector_stats.get("success_rate", 100), 2),
                    "failed_searches": vector_stats.get("failed_searches", 0),
                    "top_k_distribution": vector_stats.get("top_k_distribution", {}),
                }
            except Exception as e:
                logger.error(f"获取向量统计失败: {e}")
                stats["vector"] = {"error": str(e)}

        # 活动连接
        if "connections" in include:
            connections = []
            for conn in self.server.connections.values():
                connections.append({
                    "conn_id": conn.conn_id,
                    "client_ip": conn.client_ip,
                    "transport": conn.transport,
                    "request_count": conn.request_count,
                    "created_at": conn.created_at.isoformat(),
                    "last_active": conn.last_active.isoformat(),
                })

            stats["connections"] = {
                "count": len(connections),
                "list": connections[:20]  # 限制返回数量
            }

        # 根据格式返回
        if format_type == "prometheus":
            return self._format_prometheus(stats)
        else:
            return stats

    def _format_prometheus(self, stats: Dict[str, Any]) -> str:
        """格式化为Prometheus指标"""
        lines = []

        # 系统指标
        if "system" in stats:
            sys = stats["system"]
            lines.extend([
                f"# HELP mcp_requests_total Total number of requests",
                f"# TYPE mcp_requests_total counter",
                f"mcp_requests_total {sys.get('total_requests', 0)}",
                "",
                f"# HELP mcp_response_time_avg Average response time in ms",
                f"# TYPE mcp_response_time_avg gauge",
                f"mcp_response_time_avg {sys.get('avg_response_time', 0)}",
                "",
                f"# HELP mcp_memory_usage Memory usage percentage",
                f"# TYPE mcp_memory_usage gauge",
                f"mcp_memory_usage {sys.get('memory_usage', 0)}",
                "",
                f"# HELP mcp_cpu_usage CPU usage percentage",
                f"# TYPE mcp_cpu_usage gauge",
                f"mcp_cpu_usage {sys.get('cpu_usage', 0)}",
                ""
            ])

        # 连接池指标
        if "pool" in stats and "error" not in stats["pool"]:
            pool = stats["pool"]
            lines.extend([
                f"# HELP db_pool_size Current pool size",
                f"# TYPE db_pool_size gauge",
                f"db_pool_size {pool.get('pool_size', 0)}",
                "",
                f"# HELP db_pool_active Active connections",
                f"# TYPE db_pool_active gauge",
                f"db_pool_active {pool.get('active_connections', 0)}",
                "",
                f"# HELP db_pool_utilization Pool utilization percentage",
                f"# TYPE db_pool_utilization gauge",
                f"db_pool_utilization {pool.get('utilization', 0)}",
                ""
            ])

        # 向量检索指标
        if "vector" in stats and "error" not in stats["vector"]:
            vec = stats["vector"]
            lines.extend([
                f"# HELP vector_searches_total Total vector searches",
                f"# TYPE vector_searches_total counter",
                f"vector_searches_total {vec.get('total_searches', 0)}",
                "",
                f"# HELP vector_search_time_p95 P95 search time in ms",
                f"# TYPE vector_search_time_p95 gauge",
                f"vector_search_time_p95 {vec.get('p95_search_time', 0)}",
                ""
            ])

        return "\n".join(lines)


def setup_unified_routes(app: web.Application, server_instance):
    """
    设置统一的路由

    Args:
        app: aiohttp应用
        server_instance: 企业服务器实例
    """
    router = UnifiedAPIRouter(version="v1")
    stats_api = UnifiedStatsAPI(server_instance)

    # 统一的统计端点（替代多个重复端点）
    router.add_route("GET", "/stats", stats_api.get_all_stats, name="unified_stats")

    # 健康检查（简化版）
    async def health_check(request):
        return {
            "status": "healthy",
            "version": "v2.1.0",
            "timestamp": datetime.now().isoformat()
        }
    router.add_route("GET", "/health", health_check, name="health_check")

    # 设置路由
    router.setup_routes(app)

    logger.info("统一路由设置完成")
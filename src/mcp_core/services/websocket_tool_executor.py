"""
WebSocket工具执行器
实现MCP工具的异步执行和结果返回
"""

import json
import asyncio
from typing import Dict, Any, Optional, Callable, Awaitable
from datetime import datetime
import traceback

from ..mcp_server_unified import UnifiedMCPServer
from ..common.standard_logger import get_logger

logger = get_logger(__name__)


class WebSocketToolExecutor:
    """
    WebSocket工具执行器

    功能：
    1. 执行MCP工具
    2. 异步处理和结果返回
    3. 错误处理和恢复
    4. 执行状态追踪
    5. 结果缓存
    """

    def __init__(self, mcp_server: Optional[UnifiedMCPServer] = None):
        """
        初始化工具执行器

        Args:
            mcp_server: MCP服务器实例
        """
        self.mcp_server = mcp_server or self._create_mcp_server()
        self.executing_tasks: Dict[str, asyncio.Task] = {}
        self.execution_history: list = []
        self.result_cache: Dict[str, Any] = {}
        self.max_history = 100

    def _create_mcp_server(self) -> UnifiedMCPServer:
        """创建MCP服务器实例"""
        try:
            server = UnifiedMCPServer()
            logger.info("创建新的MCP服务器实例")
            return server
        except Exception as e:
            logger.error(f"创建MCP服务器失败: {e}")
            raise

    async def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        client_id: Optional[str] = None,
        callback: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None
    ) -> Dict[str, Any]:
        """
        异步执行MCP工具

        Args:
            tool_name: 工具名称
            arguments: 工具参数
            client_id: 客户端ID（用于跟踪）
            callback: 结果回调函数

        Returns:
            执行结果
        """
        execution_id = self._generate_execution_id(tool_name, client_id)
        start_time = datetime.now()

        # 记录执行开始
        execution_record = {
            "id": execution_id,
            "tool": tool_name,
            "arguments": arguments,
            "client_id": client_id,
            "status": "executing",
            "start_time": start_time.isoformat(),
            "end_time": None,
            "duration_ms": None,
            "result": None,
            "error": None
        }

        # 添加到历史记录
        self._add_to_history(execution_record)

        try:
            # 检查缓存
            cache_key = self._get_cache_key(tool_name, arguments)
            if cache_key in self.result_cache:
                logger.debug(f"使用缓存结果: {tool_name}")
                cached_result = self.result_cache[cache_key]
                execution_record["result"] = cached_result
                execution_record["status"] = "cached"
                execution_record["end_time"] = datetime.now().isoformat()
                execution_record["duration_ms"] = 0

                if callback:
                    await callback(self._create_response(execution_id, "cached", cached_result))

                return cached_result

            # 创建执行任务
            task = asyncio.create_task(self._execute_tool_async(tool_name, arguments))
            self.executing_tasks[execution_id] = task

            # 执行工具
            logger.info(f"执行工具: {tool_name} [ID: {execution_id}]")
            result = await task

            # 记录成功
            end_time = datetime.now()
            duration_ms = (end_time - start_time).total_seconds() * 1000

            execution_record.update({
                "status": "success",
                "result": result,
                "end_time": end_time.isoformat(),
                "duration_ms": duration_ms
            })

            # 缓存结果（只缓存成功的查询类工具）
            if self._is_cacheable(tool_name):
                self.result_cache[cache_key] = result
                logger.debug(f"缓存工具结果: {tool_name}")

            # 执行回调
            if callback:
                await callback(self._create_response(execution_id, "success", result))

            logger.info(f"工具执行成功: {tool_name} ({duration_ms:.2f}ms)")
            return result

        except asyncio.CancelledError:
            # 任务被取消
            execution_record.update({
                "status": "cancelled",
                "error": "Task cancelled",
                "end_time": datetime.now().isoformat()
            })

            if callback:
                await callback(self._create_response(execution_id, "cancelled", None, "Task cancelled"))

            logger.warning(f"工具执行被取消: {tool_name}")
            raise

        except Exception as e:
            # 记录错误
            error_message = str(e)
            error_trace = traceback.format_exc()

            execution_record.update({
                "status": "error",
                "error": error_message,
                "error_trace": error_trace,
                "end_time": datetime.now().isoformat(),
                "duration_ms": (datetime.now() - start_time).total_seconds() * 1000
            })

            if callback:
                await callback(self._create_response(execution_id, "error", None, error_message))

            logger.error(f"工具执行失败: {tool_name} - {error_message}")
            raise

        finally:
            # 清理执行任务
            self.executing_tasks.pop(execution_id, None)

    async def _execute_tool_async(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        异步执行工具的内部方法

        Args:
            tool_name: 工具名称
            arguments: 工具参数

        Returns:
            执行结果
        """
        # 构建MCP请求
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            },
            "id": f"ws_exec_{datetime.now().timestamp()}"
        }

        # 在异步上下文中执行
        loop = asyncio.get_event_loop()

        # 如果MCP服务器的handle_request是同步的，在线程池中执行
        if not asyncio.iscoroutinefunction(self.mcp_server.handle_request):
            response = await loop.run_in_executor(None, self.mcp_server.handle_request, request)
        else:
            response = await self.mcp_server.handle_request(request)

        # 检查响应
        if "error" in response:
            error = response["error"]
            raise Exception(f"Tool execution error: {error.get('message', 'Unknown error')}")

        # 提取结果
        result = response.get("result", {})
        content = result.get("content", [])

        # 解析内容
        if content and len(content) > 0:
            text_content = content[0].get("text", "")
            try:
                # 尝试解析为JSON
                return json.loads(text_content)
            except json.JSONDecodeError:
                # 返回原始文本
                return {"text": text_content}

        return result

    def cancel_execution(self, execution_id: str) -> bool:
        """
        取消正在执行的任务

        Args:
            execution_id: 执行ID

        Returns:
            是否成功取消
        """
        if execution_id in self.executing_tasks:
            task = self.executing_tasks[execution_id]
            if not task.done():
                task.cancel()
                logger.info(f"取消执行: {execution_id}")
                return True
        return False

    def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        获取执行状态

        Args:
            execution_id: 执行ID

        Returns:
            执行状态信息
        """
        # 从历史记录中查找
        for record in reversed(self.execution_history):
            if record["id"] == execution_id:
                return record
        return None

    def get_executing_tasks(self) -> list:
        """获取正在执行的任务列表"""
        return [
            {
                "id": exec_id,
                "is_running": not task.done(),
                "is_cancelled": task.cancelled()
            }
            for exec_id, task in self.executing_tasks.items()
        ]

    def clear_cache(self, tool_name: Optional[str] = None):
        """
        清除缓存

        Args:
            tool_name: 工具名称，如果为None则清除所有缓存
        """
        if tool_name:
            # 清除特定工具的缓存
            keys_to_remove = [
                key for key in self.result_cache.keys()
                if key.startswith(f"{tool_name}:")
            ]
            for key in keys_to_remove:
                del self.result_cache[key]
            logger.info(f"清除工具缓存: {tool_name} ({len(keys_to_remove)}项)")
        else:
            # 清除所有缓存
            count = len(self.result_cache)
            self.result_cache.clear()
            logger.info(f"清除所有缓存 ({count}项)")

    def get_statistics(self) -> Dict[str, Any]:
        """获取执行统计信息"""
        total = len(self.execution_history)
        if total == 0:
            return {
                "total_executions": 0,
                "success_rate": 0,
                "average_duration_ms": 0,
                "cached_results": 0,
                "executing_now": 0
            }

        success_count = sum(1 for r in self.execution_history if r["status"] == "success")
        cached_count = sum(1 for r in self.execution_history if r["status"] == "cached")
        error_count = sum(1 for r in self.execution_history if r["status"] == "error")

        durations = [
            r["duration_ms"] for r in self.execution_history
            if r["duration_ms"] is not None and r["status"] == "success"
        ]

        return {
            "total_executions": total,
            "success_count": success_count,
            "cached_count": cached_count,
            "error_count": error_count,
            "success_rate": (success_count / total) * 100 if total > 0 else 0,
            "average_duration_ms": sum(durations) / len(durations) if durations else 0,
            "cached_results": len(self.result_cache),
            "executing_now": len([t for t in self.executing_tasks.values() if not t.done()])
        }

    def _generate_execution_id(self, tool_name: str, client_id: Optional[str]) -> str:
        """生成执行ID"""
        timestamp = datetime.now().timestamp()
        if client_id:
            return f"{client_id}_{tool_name}_{timestamp}"
        return f"{tool_name}_{timestamp}"

    def _get_cache_key(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """生成缓存键"""
        # 对参数进行排序以确保一致性
        sorted_args = json.dumps(arguments, sort_keys=True)
        return f"{tool_name}:{sorted_args}"

    def _is_cacheable(self, tool_name: str) -> bool:
        """判断工具结果是否可缓存"""
        # 只缓存查询类工具
        cacheable_tools = [
            "retrieve_memory",
            "search_memories_by_vector",
            "list_projects",
            "get_project_context",
            "analyze_code_quality",
            "error_firewall_query",
            "error_firewall_stats"
        ]
        return tool_name in cacheable_tools

    def _add_to_history(self, record: Dict[str, Any]):
        """添加到历史记录"""
        self.execution_history.append(record)

        # 限制历史记录大小
        if len(self.execution_history) > self.max_history:
            self.execution_history = self.execution_history[-self.max_history:]

    def _create_response(
        self,
        execution_id: str,
        status: str,
        result: Any = None,
        error: str = None
    ) -> Dict[str, Any]:
        """创建响应消息"""
        return {
            "type": "tool_execution",
            "execution_id": execution_id,
            "status": status,
            "result": result,
            "error": error,
            "timestamp": datetime.now().isoformat()
        }


# 全局执行器实例
_global_executor: Optional[WebSocketToolExecutor] = None


def get_tool_executor(mcp_server: Optional[UnifiedMCPServer] = None) -> WebSocketToolExecutor:
    """
    获取工具执行器单例

    Args:
        mcp_server: MCP服务器实例

    Returns:
        工具执行器实例
    """
    global _global_executor
    if _global_executor is None:
        _global_executor = WebSocketToolExecutor(mcp_server)
    return _global_executor


# 便捷异步执行函数
async def execute_mcp_tool(
    tool_name: str,
    arguments: Dict[str, Any],
    client_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    便捷的工具执行函数

    Args:
        tool_name: 工具名称
        arguments: 工具参数
        client_id: 客户端ID

    Returns:
        执行结果
    """
    executor = get_tool_executor()
    return await executor.execute_tool(tool_name, arguments, client_id)
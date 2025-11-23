"""
WebSocket工具执行器测试套件
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.mcp_core.services.websocket_tool_executor import (
    WebSocketToolExecutor,
    get_tool_executor,
    execute_mcp_tool
)


class TestWebSocketToolExecutor:
    """WebSocket工具执行器测试"""

    @pytest.fixture
    def mock_mcp_server(self):
        """创建模拟的MCP服务器"""
        server = Mock()
        server.handle_request = Mock(return_value={
            "jsonrpc": "2.0",
            "id": "test_id",
            "result": {
                "content": [{
                    "type": "text",
                    "text": '{"status": "success", "data": "test_result"}'
                }]
            }
        })
        return server

    @pytest.fixture
    async def executor(self, mock_mcp_server):
        """创建执行器实例"""
        executor = WebSocketToolExecutor(mock_mcp_server)
        yield executor
        # 清理
        executor.clear_cache()

    @pytest.mark.asyncio
    async def test_execute_tool_success(self, executor, mock_mcp_server):
        """测试成功执行工具"""
        result = await executor.execute_tool(
            tool_name="test_tool",
            arguments={"param1": "value1"},
            client_id="test_client"
        )

        # 验证结果
        assert result["status"] == "success"
        assert result["data"] == "test_result"

        # 验证MCP服务器被调用
        mock_mcp_server.handle_request.assert_called_once()
        call_args = mock_mcp_server.handle_request.call_args[0][0]
        assert call_args["method"] == "tools/call"
        assert call_args["params"]["name"] == "test_tool"

        # 验证执行历史
        assert len(executor.execution_history) == 1
        history = executor.execution_history[0]
        assert history["tool"] == "test_tool"
        assert history["status"] == "success"

    @pytest.mark.asyncio
    async def test_execute_tool_with_error(self, executor, mock_mcp_server):
        """测试工具执行错误处理"""
        # 模拟错误响应
        mock_mcp_server.handle_request.return_value = {
            "jsonrpc": "2.0",
            "id": "test_id",
            "error": {
                "code": -32603,
                "message": "Tool execution failed"
            }
        }

        with pytest.raises(Exception) as exc_info:
            await executor.execute_tool(
                tool_name="failing_tool",
                arguments={},
                client_id="test_client"
            )

        assert "Tool execution error" in str(exc_info.value)

        # 验证执行历史记录了错误
        assert len(executor.execution_history) == 1
        history = executor.execution_history[0]
        assert history["status"] == "error"
        assert history["error"] is not None

    @pytest.mark.asyncio
    async def test_execute_tool_with_callback(self, executor, mock_mcp_server):
        """测试带回调的工具执行"""
        callback_called = False
        callback_result = None

        async def test_callback(response):
            nonlocal callback_called, callback_result
            callback_called = True
            callback_result = response

        result = await executor.execute_tool(
            tool_name="test_tool",
            arguments={},
            client_id="test_client",
            callback=test_callback
        )

        # 验证回调被调用
        assert callback_called
        assert callback_result["status"] == "success"
        assert callback_result["execution_id"] is not None

    @pytest.mark.asyncio
    async def test_tool_result_caching(self, executor, mock_mcp_server):
        """测试工具结果缓存"""
        # 第一次执行
        result1 = await executor.execute_tool(
            tool_name="retrieve_memory",  # 可缓存的工具
            arguments={"key": "test"},
            client_id="client1"
        )

        # 第二次执行相同参数
        result2 = await executor.execute_tool(
            tool_name="retrieve_memory",
            arguments={"key": "test"},
            client_id="client2"
        )

        # 验证结果相同
        assert result1 == result2

        # 验证MCP服务器只被调用一次（第二次使用缓存）
        assert mock_mcp_server.handle_request.call_count == 1

        # 验证缓存统计
        stats = executor.get_statistics()
        assert stats["cached_count"] == 1

    @pytest.mark.asyncio
    async def test_cancel_execution(self, executor):
        """测试取消执行"""
        # 创建一个慢速执行的mock
        slow_server = Mock()

        async def slow_handler(request):
            await asyncio.sleep(5)  # 模拟长时间执行
            return {"result": "slow_result"}

        slow_server.handle_request = AsyncMock(side_effect=slow_handler)
        executor.mcp_server = slow_server

        # 启动执行
        task = asyncio.create_task(executor.execute_tool(
            tool_name="slow_tool",
            arguments={},
            client_id="test"
        ))

        # 等待任务开始
        await asyncio.sleep(0.1)

        # 获取执行ID并取消
        exec_id = list(executor.executing_tasks.keys())[0]
        success = executor.cancel_execution(exec_id)
        assert success

        # 验证任务被取消
        with pytest.raises(asyncio.CancelledError):
            await task

    @pytest.mark.asyncio
    async def test_concurrent_executions(self, executor, mock_mcp_server):
        """测试并发执行"""
        # 启动多个并发执行
        tasks = []
        for i in range(5):
            task = executor.execute_tool(
                tool_name=f"tool_{i}",
                arguments={"index": i},
                client_id=f"client_{i}"
            )
            tasks.append(task)

        # 等待所有任务完成
        results = await asyncio.gather(*tasks)

        # 验证所有执行成功
        assert len(results) == 5
        for result in results:
            assert result["status"] == "success"

        # 验证执行历史
        assert len(executor.execution_history) == 5

    @pytest.mark.asyncio
    async def test_execution_status_tracking(self, executor, mock_mcp_server):
        """测试执行状态跟踪"""
        # 执行工具
        result = await executor.execute_tool(
            tool_name="test_tool",
            arguments={},
            client_id="test"
        )

        # 获取执行状态
        exec_id = executor.execution_history[-1]["id"]
        status = executor.get_execution_status(exec_id)

        assert status is not None
        assert status["status"] == "success"
        assert status["tool"] == "test_tool"
        assert status["duration_ms"] is not None

    def test_get_statistics(self, executor):
        """测试统计信息"""
        # 初始统计
        stats = executor.get_statistics()
        assert stats["total_executions"] == 0
        assert stats["success_rate"] == 0

        # 添加一些执行记录
        executor.execution_history.extend([
            {"status": "success", "duration_ms": 100},
            {"status": "success", "duration_ms": 200},
            {"status": "error", "duration_ms": 50},
            {"status": "cached", "duration_ms": 0},
        ])

        # 获取更新后的统计
        stats = executor.get_statistics()
        assert stats["total_executions"] == 4
        assert stats["success_count"] == 2
        assert stats["error_count"] == 1
        assert stats["cached_count"] == 1
        assert stats["success_rate"] == 50.0
        assert stats["average_duration_ms"] == 150.0  # (100+200)/2

    def test_clear_cache(self, executor):
        """测试清除缓存"""
        # 添加一些缓存
        executor.result_cache = {
            "tool1:args1": {"result": 1},
            "tool1:args2": {"result": 2},
            "tool2:args1": {"result": 3},
        }

        # 清除特定工具的缓存
        executor.clear_cache("tool1")
        assert len(executor.result_cache) == 1
        assert "tool2:args1" in executor.result_cache

        # 清除所有缓存
        executor.clear_cache()
        assert len(executor.result_cache) == 0

    @pytest.mark.asyncio
    async def test_async_mcp_server(self):
        """测试异步MCP服务器"""
        # 创建异步mock
        async_server = Mock()
        async_server.handle_request = AsyncMock(return_value={
            "jsonrpc": "2.0",
            "result": {
                "content": [{
                    "type": "text",
                    "text": '{"async": true}'
                }]
            }
        })

        executor = WebSocketToolExecutor(async_server)
        result = await executor.execute_tool("async_tool", {})

        assert result["async"] is True
        async_server.handle_request.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_execution_history_limit(self, executor):
        """测试执行历史限制"""
        executor.max_history = 5

        # 执行超过限制数量的任务
        for i in range(10):
            executor._add_to_history({
                "id": f"exec_{i}",
                "tool": f"tool_{i}",
                "status": "success"
            })

        # 验证历史记录被限制
        assert len(executor.execution_history) == 5
        # 验证保留的是最新的记录
        assert executor.execution_history[0]["id"] == "exec_5"
        assert executor.execution_history[-1]["id"] == "exec_9"


@pytest.mark.integration
class TestWebSocketToolExecutorIntegration:
    """WebSocket工具执行器集成测试"""

    @pytest.mark.asyncio
    async def test_with_real_mcp_server(self):
        """测试与真实MCP服务器集成"""
        from src.mcp_core.mcp_server_unified import UnifiedMCPServer

        # 创建真实的MCP服务器
        mcp_server = UnifiedMCPServer()
        executor = WebSocketToolExecutor(mcp_server)

        # 测试列出工具
        result = await executor.execute_tool(
            tool_name="list_projects",
            arguments={},
            client_id="integration_test"
        )

        # 基本验证（具体结果取决于实际数据）
        assert result is not None
        assert isinstance(result, (dict, list))

    @pytest.mark.asyncio
    async def test_with_bidirectional_websocket(self):
        """测试与双向WebSocket集成"""
        from src.mcp_core.services.bidirectional_websocket import BidirectionalWebSocket

        ws_service = BidirectionalWebSocket()

        # 模拟WebSocket消息
        test_message = {
            "type": "execute_tool",
            "data": {
                "tool": "test_tool",
                "arguments": {"test": "value"}
            }
        }

        # 处理消息（需要mock MCP服务器）
        with patch('src.mcp_core.services.websocket_tool_executor.get_tool_executor') as mock_get:
            mock_executor = Mock()
            mock_executor.execute_tool = AsyncMock(return_value={"result": "test"})
            mock_get.return_value = mock_executor

            response = await ws_service.handle_message("test_client", test_message)

            assert response["type"] == "execute_tool_response"
            assert response["data"]["status"] == "success"

    @pytest.mark.asyncio
    async def test_global_executor_singleton(self):
        """测试全局执行器单例"""
        executor1 = get_tool_executor()
        executor2 = get_tool_executor()

        assert executor1 is executor2

    @pytest.mark.asyncio
    async def test_convenience_function(self):
        """测试便捷执行函数"""
        with patch('src.mcp_core.services.websocket_tool_executor.get_tool_executor') as mock_get:
            mock_executor = Mock()
            mock_executor.execute_tool = AsyncMock(return_value={"convenience": True})
            mock_get.return_value = mock_executor

            result = await execute_mcp_tool(
                tool_name="test",
                arguments={},
                client_id="test"
            )

            assert result["convenience"] is True
            mock_executor.execute_tool.assert_awaited_once()
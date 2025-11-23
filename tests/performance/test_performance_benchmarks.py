"""
性能基准测试套件
测试系统关键组件的性能表现
"""

import pytest
import time
import asyncio
import numpy as np
from typing import List, Dict, Any
import json
import psutil
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# 性能测试标记
pytestmark = pytest.mark.performance


class PerformanceBenchmark:
    """性能基准测试基类"""

    def __init__(self, name: str):
        self.name = name
        self.results = []
        self.start_time = None
        self.end_time = None

    def start(self):
        """开始计时"""
        self.start_time = time.perf_counter()
        return self

    def stop(self):
        """停止计时"""
        self.end_time = time.perf_counter()
        if self.start_time:
            elapsed = self.end_time - self.start_time
            self.results.append(elapsed)
        return elapsed

    def get_stats(self) -> Dict[str, float]:
        """获取统计信息"""
        if not self.results:
            return {}

        return {
            "name": self.name,
            "samples": len(self.results),
            "min": min(self.results) * 1000,  # 转换为ms
            "max": max(self.results) * 1000,
            "mean": np.mean(self.results) * 1000,
            "median": np.median(self.results) * 1000,
            "p95": np.percentile(self.results, 95) * 1000,
            "p99": np.percentile(self.results, 99) * 1000,
            "std": np.std(self.results) * 1000,
            "throughput": len(self.results) / sum(self.results)  # ops/sec
        }

    def report(self):
        """生成报告"""
        stats = self.get_stats()
        if not stats:
            return "No data collected"

        return f"""
Performance Report: {self.name}
{'=' * 50}
Samples: {stats['samples']}
Min: {stats['min']:.2f}ms
Max: {stats['max']:.2f}ms
Mean: {stats['mean']:.2f}ms
Median: {stats['median']:.2f}ms
P95: {stats['p95']:.2f}ms
P99: {stats['p99']:.2f}ms
Std Dev: {stats['std']:.2f}ms
Throughput: {stats['throughput']:.2f} ops/sec
"""


class TestVectorSearchPerformance:
    """向量检索性能测试"""

    @pytest.fixture
    def vector_db(self):
        """获取向量数据库实例"""
        from src.mcp_core.services.vector_db import get_vector_db
        return get_vector_db()

    @pytest.fixture
    def sample_vectors(self):
        """生成测试向量"""
        return [np.random.rand(768).tolist() for _ in range(100)]

    @pytest.mark.benchmark
    def test_single_vector_search(self, vector_db, sample_vectors):
        """单向量检索性能测试"""
        benchmark = PerformanceBenchmark("Single Vector Search")

        # 预热
        for _ in range(5):
            vector_db.search_vectors(
                "mid_term_memories",
                [sample_vectors[0]],
                top_k=10,
                use_cache=False
            )

        # 正式测试
        for i in range(100):
            benchmark.start()
            result = vector_db.search_vectors(
                "mid_term_memories",
                [sample_vectors[i % len(sample_vectors)]],
                top_k=10,
                use_cache=False
            )
            benchmark.stop()

        print(benchmark.report())
        stats = benchmark.get_stats()

        # 性能断言
        assert stats['mean'] < 200, f"平均检索时间过长: {stats['mean']:.2f}ms"
        assert stats['p95'] < 500, f"P95延迟过高: {stats['p95']:.2f}ms"

    @pytest.mark.benchmark
    def test_batch_vector_search(self, vector_db, sample_vectors):
        """批量向量检索性能测试"""
        benchmark = PerformanceBenchmark("Batch Vector Search")

        batch_sizes = [1, 5, 10, 20]

        for batch_size in batch_sizes:
            batch = sample_vectors[:batch_size]
            for _ in range(10):
                benchmark.start()
                result = vector_db.search_vectors(
                    "mid_term_memories",
                    batch,
                    top_k=10,
                    use_cache=False
                )
                benchmark.stop()

        print(benchmark.report())

    @pytest.mark.benchmark
    def test_vector_search_with_cache(self, vector_db, sample_vectors):
        """缓存向量检索性能测试"""
        no_cache_benchmark = PerformanceBenchmark("Vector Search (No Cache)")
        cache_benchmark = PerformanceBenchmark("Vector Search (With Cache)")

        query_vector = sample_vectors[0]

        # 无缓存测试
        for _ in range(50):
            no_cache_benchmark.start()
            vector_db.search_vectors(
                "mid_term_memories",
                [query_vector],
                top_k=10,
                use_cache=False
            )
            no_cache_benchmark.stop()

        # 有缓存测试（第一次会miss）
        for _ in range(50):
            cache_benchmark.start()
            vector_db.search_vectors(
                "mid_term_memories",
                [query_vector],
                top_k=10,
                use_cache=True
            )
            cache_benchmark.stop()

        no_cache_stats = no_cache_benchmark.get_stats()
        cache_stats = cache_benchmark.get_stats()

        print(no_cache_benchmark.report())
        print(cache_benchmark.report())

        # 缓存应该显著提升性能
        assert cache_stats['mean'] < no_cache_stats['mean'] * 0.5, \
            "缓存没有显著提升性能"


class TestWebSocketPerformance:
    """WebSocket性能测试"""

    @pytest.fixture
    async def ws_client(self):
        """创建WebSocket客户端"""
        import aiohttp
        session = aiohttp.ClientSession()
        ws = await session.ws_connect('ws://localhost:8765/ws')
        yield ws
        await ws.close()
        await session.close()

    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_websocket_throughput(self, ws_client):
        """WebSocket吞吐量测试"""
        benchmark = PerformanceBenchmark("WebSocket Throughput")

        message = {
            "type": "ping",
            "data": {"timestamp": time.time()}
        }

        # 发送100条消息
        for _ in range(100):
            benchmark.start()
            await ws_client.send_json(message)
            response = await ws_client.receive_json()
            benchmark.stop()

        print(benchmark.report())
        stats = benchmark.get_stats()

        # 断言：延迟应该小于50ms
        assert stats['mean'] < 50, f"WebSocket平均延迟过高: {stats['mean']:.2f}ms"
        assert stats['throughput'] > 20, f"吞吐量过低: {stats['throughput']:.2f} msg/sec"

    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_websocket_broadcast(self):
        """WebSocket广播性能测试"""
        benchmark = PerformanceBenchmark("WebSocket Broadcast")

        # 创建多个客户端
        clients = []
        for _ in range(10):
            session = aiohttp.ClientSession()
            ws = await session.ws_connect('ws://localhost:8765/ws')
            clients.append((session, ws))

        # 订阅频道
        for _, ws in clients:
            await ws.send_json({
                "type": "subscribe",
                "data": {"channels": ["test_channel"]}
            })

        # 广播消息
        from src.mcp_core.services.unified_notifier import notify

        for i in range(50):
            benchmark.start()
            notify("test_channel", "test_event", {"index": i})
            # 等待所有客户端接收
            for _, ws in clients:
                await ws.receive_json()
            benchmark.stop()

        # 清理
        for session, ws in clients:
            await ws.close()
            await session.close()

        print(benchmark.report())


class TestDatabasePerformance:
    """数据库性能测试"""

    @pytest.fixture
    def db_pool(self):
        """获取数据库连接池"""
        from src.mcp_core.services.dynamic_db_pool import get_dynamic_pool_manager
        return get_dynamic_pool_manager()

    @pytest.mark.benchmark
    def test_connection_pool_performance(self, db_pool):
        """连接池性能测试"""
        benchmark = PerformanceBenchmark("Connection Pool")

        def execute_query():
            with db_pool.engine.connect() as conn:
                result = conn.execute("SELECT 1")
                return result.scalar()

        # 单线程测试
        for _ in range(100):
            benchmark.start()
            execute_query()
            benchmark.stop()

        single_thread_stats = benchmark.get_stats()
        print("Single Thread Performance:")
        print(benchmark.report())

        # 多线程测试
        benchmark = PerformanceBenchmark("Connection Pool (Multi-thread)")

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for _ in range(100):
                benchmark.start()
                future = executor.submit(execute_query)
                futures.append((benchmark, future))

            for bench, future in futures:
                future.result()
                bench.stop()

        multi_thread_stats = benchmark.get_stats()
        print("Multi Thread Performance:")
        print(benchmark.report())

        # 性能断言
        assert single_thread_stats['mean'] < 50, "单线程查询太慢"
        assert multi_thread_stats['throughput'] > 50, "多线程吞吐量太低"


class TestCachePerformance:
    """缓存性能测试"""

    @pytest.fixture
    def cache(self):
        """获取缓存实例"""
        from src.mcp_core.services.cache_integration import get_cache_integration
        return get_cache_integration()

    @pytest.mark.benchmark
    def test_cache_hit_performance(self, cache):
        """缓存命中性能测试"""
        l1_benchmark = PerformanceBenchmark("L1 Cache Hit")
        l2_benchmark = PerformanceBenchmark("L2 Cache Hit")

        # 准备测试数据
        test_data = {"key": "value", "data": list(range(1000))}

        # L1缓存测试
        cache.cache.l1_cache.set("test_key", test_data)
        for _ in range(1000):
            l1_benchmark.start()
            result = cache.cache.l1_cache.get("test_key")
            l1_benchmark.stop()

        # L2缓存测试（Redis）
        if cache.cache.redis_client:
            cache.cache.set("test_key_l2", test_data, l2_ttl=60)
            for _ in range(100):
                l2_benchmark.start()
                result = cache.cache.get("test_key_l2")
                l2_benchmark.stop()

        print(l1_benchmark.report())
        print(l2_benchmark.report())

        l1_stats = l1_benchmark.get_stats()
        assert l1_stats['mean'] < 1, "L1缓存访问太慢"
        assert l1_stats['throughput'] > 1000, "L1缓存吞吐量太低"


class TestSystemPerformance:
    """系统整体性能测试"""

    @pytest.mark.benchmark
    @pytest.mark.slow
    def test_memory_usage(self):
        """内存使用测试"""
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # 执行一些操作
        from src.mcp_core.services.vector_db import get_vector_db
        from src.mcp_core.services.cache_integration import get_cache_integration

        vector_db = get_vector_db()
        cache = get_cache_integration()

        # 模拟负载
        for i in range(100):
            cache.cache.set(f"key_{i}", {"data": list(range(1000))})

        current_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = current_memory - initial_memory

        print(f"Initial Memory: {initial_memory:.2f}MB")
        print(f"Current Memory: {current_memory:.2f}MB")
        print(f"Memory Increase: {memory_increase:.2f}MB")

        # 内存增长不应超过100MB
        assert memory_increase < 100, f"内存增长过大: {memory_increase:.2f}MB"

    @pytest.mark.benchmark
    @pytest.mark.slow
    def test_cpu_usage(self):
        """CPU使用率测试"""
        benchmark = PerformanceBenchmark("CPU Usage")

        # 监控CPU使用率
        cpu_samples = []

        def monitor_cpu():
            while len(cpu_samples) < 10:
                cpu_samples.append(psutil.cpu_percent(interval=1))

        monitor_thread = threading.Thread(target=monitor_cpu)
        monitor_thread.start()

        # 执行负载
        from src.mcp_core.services.embedding_service import get_embedding_service
        embedding_service = get_embedding_service()

        texts = ["Test text " * 100 for _ in range(10)]
        for text in texts:
            embedding_service.generate_embedding(text)

        monitor_thread.join()

        avg_cpu = np.mean(cpu_samples)
        max_cpu = max(cpu_samples)

        print(f"Average CPU: {avg_cpu:.2f}%")
        print(f"Max CPU: {max_cpu:.2f}%")

        # CPU使用率不应超过80%
        assert avg_cpu < 80, f"平均CPU使用率过高: {avg_cpu:.2f}%"


def generate_performance_report(results: List[Dict[str, Any]]):
    """生成性能测试报告"""
    report = """
    ====================================
    性能测试报告
    ====================================

    """

    for result in results:
        report += f"""
    {result['name']}
    ----------------------------------
    平均响应时间: {result['mean']:.2f}ms
    P95延迟: {result['p95']:.2f}ms
    P99延迟: {result['p99']:.2f}ms
    吞吐量: {result['throughput']:.2f} ops/sec

    """

    return report


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
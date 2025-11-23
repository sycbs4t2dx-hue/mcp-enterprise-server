"""
性能优化引擎
提供代码优化、查询优化、缓存优化等全方位性能提升方案
"""

import os
import sys
import time
import asyncio
import psutil
import cProfile
import pstats
import io
import gc
import tracemalloc
from typing import Dict, List, Optional, Any, Callable, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict, deque
import json
import numpy as np
from functools import lru_cache, wraps
import aioredis
import aiomysql
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

from ..common.logger import get_logger
from ..common.config import get_settings
from ..models import db_manager, PerformanceMetrics, OptimizationResult
from ..services.redis_client import get_redis_client
from ..services.ai_model_manager import get_model_manager, ModelCapability

logger = get_logger(__name__)
settings = get_settings()

# ============================================
# 性能配置
# ============================================

class OptimizationType(Enum):
    """优化类型"""
    CODE = "code"
    QUERY = "query"
    CACHE = "cache"
    MEMORY = "memory"
    IO = "io"
    CPU = "cpu"
    NETWORK = "network"
    ALGORITHM = "algorithm"

class PerformanceLevel(Enum):
    """性能级别"""
    CRITICAL = "critical"  # <100ms
    HIGH = "high"         # <500ms
    MEDIUM = "medium"     # <1000ms
    LOW = "low"          # >1000ms

@dataclass
class PerformanceConfig:
    """性能配置"""
    enable_profiling: bool = True
    enable_caching: bool = True
    enable_async: bool = True
    cache_ttl: int = 3600
    max_cache_size: int = 10000
    connection_pool_size: int = 20
    thread_pool_size: int = 10
    process_pool_size: int = 4
    batch_size: int = 100
    memory_limit_mb: int = 1024
    cpu_threshold: float = 80.0
    response_time_threshold_ms: int = 1000
    slow_query_threshold_ms: int = 100
    optimization_interval_minutes: int = 30

@dataclass
class PerformanceMetric:
    """性能指标"""
    name: str
    value: float
    unit: str
    timestamp: datetime = field(default_factory=datetime.now)
    tags: Dict[str, str] = field(default_factory=dict)

@dataclass
class OptimizationSuggestion:
    """优化建议"""
    type: OptimizationType
    title: str
    description: str
    expected_improvement: float  # 百分比
    implementation: str
    priority: int  # 1-5, 1最高
    estimated_effort: str  # "low", "medium", "high"

# ============================================
# 性能分析器
# ============================================

class PerformanceProfiler:
    """性能分析器"""

    def __init__(self, config: PerformanceConfig):
        self.config = config
        self.profiles = {}
        self.metrics = defaultdict(deque)
        self.max_metrics = 1000

    def profile_function(self, func: Callable) -> Callable:
        """装饰器：分析函数性能"""
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            if not self.config.enable_profiling:
                return await func(*args, **kwargs)

            start_time = time.perf_counter()
            start_memory = psutil.Process().memory_info().rss / 1024 / 1024

            try:
                result = await func(*args, **kwargs)
                status = "success"
            except Exception as e:
                result = None
                status = "error"
                raise e
            finally:
                end_time = time.perf_counter()
                end_memory = psutil.Process().memory_info().rss / 1024 / 1024

                self._record_metric(
                    func.__name__,
                    {
                        "duration_ms": (end_time - start_time) * 1000,
                        "memory_mb": end_memory - start_memory,
                        "status": status,
                        "timestamp": datetime.now().isoformat()
                    }
                )

            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            if not self.config.enable_profiling:
                return func(*args, **kwargs)

            profiler = cProfile.Profile()
            profiler.enable()

            start_time = time.perf_counter()
            start_memory = psutil.Process().memory_info().rss / 1024 / 1024

            try:
                result = func(*args, **kwargs)
                status = "success"
            except Exception as e:
                result = None
                status = "error"
                raise e
            finally:
                profiler.disable()
                end_time = time.perf_counter()
                end_memory = psutil.Process().memory_info().rss / 1024 / 1024

                # 保存性能数据
                self._save_profile(func.__name__, profiler)
                self._record_metric(
                    func.__name__,
                    {
                        "duration_ms": (end_time - start_time) * 1000,
                        "memory_mb": end_memory - start_memory,
                        "status": status
                    }
                )

            return result

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    def _save_profile(self, name: str, profiler: cProfile.Profile):
        """保存性能分析数据"""
        s = io.StringIO()
        ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
        ps.print_stats(20)
        self.profiles[name] = s.getvalue()

    def _record_metric(self, name: str, metric: Dict):
        """记录性能指标"""
        if len(self.metrics[name]) >= self.max_metrics:
            self.metrics[name].popleft()
        self.metrics[name].append(metric)

    def get_profile(self, name: str) -> Optional[str]:
        """获取性能分析结果"""
        return self.profiles.get(name)

    def get_metrics(self, name: str) -> List[Dict]:
        """获取性能指标"""
        return list(self.metrics.get(name, []))

    def get_statistics(self, name: str) -> Dict:
        """获取统计信息"""
        metrics = self.metrics.get(name, [])
        if not metrics:
            return {}

        durations = [m["duration_ms"] for m in metrics]
        memories = [m["memory_mb"] for m in metrics]

        return {
            "count": len(metrics),
            "avg_duration_ms": np.mean(durations),
            "p50_duration_ms": np.percentile(durations, 50),
            "p95_duration_ms": np.percentile(durations, 95),
            "p99_duration_ms": np.percentile(durations, 99),
            "max_duration_ms": max(durations),
            "min_duration_ms": min(durations),
            "avg_memory_mb": np.mean(memories),
            "max_memory_mb": max(memories)
        }

# ============================================
# 查询优化器
# ============================================

class QueryOptimizer:
    """查询优化器"""

    def __init__(self):
        self.query_cache = {}
        self.slow_queries = []
        self.index_suggestions = {}

    async def analyze_query(self, query: str, execution_time_ms: float) -> Dict:
        """分析查询"""
        analysis = {
            "query": query,
            "execution_time_ms": execution_time_ms,
            "is_slow": execution_time_ms > 100,
            "suggestions": []
        }

        # 检查是否使用了SELECT *
        if "SELECT *" in query.upper():
            analysis["suggestions"].append({
                "type": "select_specific_columns",
                "description": "Avoid SELECT *, specify needed columns",
                "impact": "high"
            })

        # 检查是否缺少索引
        if "WHERE" in query.upper() and "INDEX" not in query.upper():
            analysis["suggestions"].append({
                "type": "add_index",
                "description": "Consider adding index for WHERE clause columns",
                "impact": "high"
            })

        # 检查JOIN操作
        join_count = query.upper().count("JOIN")
        if join_count > 3:
            analysis["suggestions"].append({
                "type": "reduce_joins",
                "description": f"Query has {join_count} JOINs, consider denormalization",
                "impact": "medium"
            })

        # 检查是否有子查询
        if "SELECT" in query[10:].upper():  # 跳过第一个SELECT
            analysis["suggestions"].append({
                "type": "optimize_subquery",
                "description": "Consider replacing subquery with JOIN",
                "impact": "medium"
            })

        # 检查LIMIT
        if "LIMIT" not in query.upper() and "SELECT" in query.upper():
            analysis["suggestions"].append({
                "type": "add_limit",
                "description": "Consider adding LIMIT clause",
                "impact": "low"
            })

        return analysis

    async def optimize_query(self, query: str) -> str:
        """优化查询"""
        optimized = query

        # 基础优化规则
        optimizations = [
            # 移除不必要的DISTINCT
            (r'\bDISTINCT\b(?=.*\bGROUP BY\b)', ''),
            # 使用EXISTS替代IN
            (r'\bWHERE\s+\w+\s+IN\s*\(SELECT', 'WHERE EXISTS (SELECT 1'),
            # 避免在WHERE子句中使用函数
            (r'WHERE\s+YEAR\((\w+)\)\s*=\s*(\d+)', r'WHERE \1 BETWEEN "\2-01-01" AND "\2-12-31"'),
        ]

        for pattern, replacement in optimizations:
            import re
            optimized = re.sub(pattern, replacement, optimized, flags=re.IGNORECASE)

        return optimized

    def suggest_indexes(self, table_name: str, query_patterns: List[str]) -> List[str]:
        """建议索引"""
        suggestions = []

        # 分析查询模式
        column_usage = defaultdict(int)
        for pattern in query_patterns:
            # 提取WHERE子句中的列
            import re
            where_match = re.search(r'WHERE\s+(.*?)(?:ORDER|GROUP|LIMIT|$)', pattern, re.IGNORECASE)
            if where_match:
                conditions = where_match.group(1)
                columns = re.findall(r'(\w+)\s*[=<>]', conditions)
                for col in columns:
                    column_usage[col] += 1

        # 根据使用频率建议索引
        for column, count in column_usage.items():
            if count > 5:  # 使用超过5次
                suggestions.append(f"CREATE INDEX idx_{table_name}_{column} ON {table_name}({column});")

        return suggestions

# ============================================
# 缓存优化器
# ============================================

class CacheOptimizer:
    """缓存优化器"""

    def __init__(self, config: PerformanceConfig):
        self.config = config
        self.redis_client = get_redis_client()
        self.cache_stats = defaultdict(lambda: {"hits": 0, "misses": 0})
        self.memory_cache = {}
        self.cache_sizes = {}

    def cached(self, ttl: Optional[int] = None):
        """缓存装饰器"""
        def decorator(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                if not self.config.enable_caching:
                    return await func(*args, **kwargs)

                cache_key = self._generate_cache_key(func.__name__, args, kwargs)

                # 尝试从内存缓存获取
                if cache_key in self.memory_cache:
                    self.cache_stats[func.__name__]["hits"] += 1
                    return self.memory_cache[cache_key]

                # 尝试从Redis获取
                cached_value = await self.redis_client.get(cache_key)
                if cached_value:
                    self.cache_stats[func.__name__]["hits"] += 1
                    value = json.loads(cached_value)
                    self.memory_cache[cache_key] = value
                    return value

                # 缓存未命中，执行函数
                self.cache_stats[func.__name__]["misses"] += 1
                result = await func(*args, **kwargs)

                # 存储到缓存
                cache_ttl = ttl or self.config.cache_ttl
                await self.redis_client.setex(
                    cache_key,
                    cache_ttl,
                    json.dumps(result, default=str)
                )

                # 存储到内存缓存（LRU）
                if len(self.memory_cache) >= self.config.max_cache_size:
                    self._evict_lru()
                self.memory_cache[cache_key] = result

                return result

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                if not self.config.enable_caching:
                    return func(*args, **kwargs)

                cache_key = self._generate_cache_key(func.__name__, args, kwargs)

                # 使用内置LRU缓存
                return func(*args, **kwargs)

            return async_wrapper if asyncio.iscoroutinefunction(func) else lru_cache(maxsize=128)(func)

        return decorator

    def _generate_cache_key(self, name: str, args: tuple, kwargs: dict) -> str:
        """生成缓存键"""
        import hashlib
        key_parts = [name]
        key_parts.extend(str(arg) for arg in args)
        key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
        key_str = ":".join(key_parts)
        return f"cache:{hashlib.md5(key_str.encode()).hexdigest()}"

    def _evict_lru(self):
        """LRU淘汰"""
        if self.memory_cache:
            # 简单的FIFO实现，实际应该用OrderedDict或专门的LRU实现
            first_key = next(iter(self.memory_cache))
            del self.memory_cache[first_key]

    async def warm_cache(self, keys: List[str]):
        """预热缓存"""
        for key in keys:
            # 这里应该根据key类型调用相应的函数来预热
            pass

    def get_cache_statistics(self) -> Dict:
        """获取缓存统计"""
        total_hits = sum(stats["hits"] for stats in self.cache_stats.values())
        total_misses = sum(stats["misses"] for stats in self.cache_stats.values())
        hit_rate = total_hits / (total_hits + total_misses) if total_hits + total_misses > 0 else 0

        return {
            "total_hits": total_hits,
            "total_misses": total_misses,
            "hit_rate": hit_rate,
            "memory_cache_size": len(self.memory_cache),
            "function_stats": dict(self.cache_stats)
        }

    async def optimize_cache_strategy(self) -> List[OptimizationSuggestion]:
        """优化缓存策略"""
        suggestions = []
        stats = self.get_cache_statistics()

        # 低命中率优化
        if stats["hit_rate"] < 0.5:
            suggestions.append(OptimizationSuggestion(
                type=OptimizationType.CACHE,
                title="Increase cache TTL",
                description=f"Cache hit rate is {stats['hit_rate']:.2%}, consider increasing TTL",
                expected_improvement=30,
                implementation="Increase cache_ttl in configuration",
                priority=2,
                estimated_effort="low"
            ))

        # 检查热点数据
        for func_name, func_stats in stats["function_stats"].items():
            if func_stats["misses"] > func_stats["hits"] * 2:
                suggestions.append(OptimizationSuggestion(
                    type=OptimizationType.CACHE,
                    title=f"Pre-warm cache for {func_name}",
                    description=f"Function {func_name} has high miss rate",
                    expected_improvement=20,
                    implementation=f"Implement cache warming for {func_name}",
                    priority=3,
                    estimated_effort="medium"
                ))

        return suggestions

# ============================================
# 内存优化器
# ============================================

class MemoryOptimizer:
    """内存优化器"""

    def __init__(self, config: PerformanceConfig):
        self.config = config
        tracemalloc.start()
        self.snapshots = []

    def analyze_memory(self) -> Dict:
        """分析内存使用"""
        process = psutil.Process()
        memory_info = process.memory_info()

        # 获取详细内存信息
        snapshot = tracemalloc.take_snapshot()
        self.snapshots.append(snapshot)

        # 获取top内存使用
        top_stats = snapshot.statistics('lineno')[:10]

        return {
            "total_memory_mb": memory_info.rss / 1024 / 1024,
            "available_memory_mb": psutil.virtual_memory().available / 1024 / 1024,
            "memory_percent": process.memory_percent(),
            "top_memory_usage": [
                {
                    "file": stat.traceback.format()[0],
                    "size_mb": stat.size / 1024 / 1024,
                    "count": stat.count
                }
                for stat in top_stats
            ]
        }

    def optimize_memory(self) -> List[OptimizationSuggestion]:
        """优化内存使用"""
        suggestions = []
        memory_analysis = self.analyze_memory()

        # 高内存使用警告
        if memory_analysis["memory_percent"] > 80:
            suggestions.append(OptimizationSuggestion(
                type=OptimizationType.MEMORY,
                title="High memory usage detected",
                description=f"Memory usage is {memory_analysis['memory_percent']:.1f}%",
                expected_improvement=30,
                implementation="1. Use generators instead of lists\n2. Clear unused objects\n3. Use weak references",
                priority=1,
                estimated_effort="medium"
            ))

        # 检查内存泄漏
        if len(self.snapshots) > 1:
            diff = self.snapshots[-1].compare_to(self.snapshots[-2], 'lineno')
            for stat in diff[:5]:
                if stat.size_diff > 10 * 1024 * 1024:  # 10MB增长
                    suggestions.append(OptimizationSuggestion(
                        type=OptimizationType.MEMORY,
                        title="Potential memory leak",
                        description=f"Memory increased by {stat.size_diff / 1024 / 1024:.1f}MB in {stat.traceback}",
                        expected_improvement=40,
                        implementation="Review and fix memory leak in the identified location",
                        priority=1,
                        estimated_effort="high"
                    ))

        return suggestions

    def force_gc(self) -> Dict:
        """强制垃圾回收"""
        before = psutil.Process().memory_info().rss / 1024 / 1024
        collected = gc.collect()
        after = psutil.Process().memory_info().rss / 1024 / 1024

        return {
            "collected_objects": collected,
            "memory_freed_mb": before - after,
            "memory_after_mb": after
        }

# ============================================
# 算法优化器
# ============================================

class AlgorithmOptimizer:
    """算法优化器"""

    def __init__(self):
        self.model_manager = get_model_manager()

    async def analyze_algorithm_complexity(self, code: str) -> Dict:
        """分析算法复杂度"""
        prompt = f"""
        Analyze the time and space complexity of this code:

        {code}

        Provide:
        1. Time complexity (Big O notation)
        2. Space complexity (Big O notation)
        3. Bottlenecks
        4. Optimization suggestions

        Format as JSON.
        """

        response = await self.model_manager.generate(
            prompt=prompt,
            capability=ModelCapability.OPTIMIZATION
        )

        try:
            return json.loads(response.content)
        except:
            return {
                "time_complexity": "Unknown",
                "space_complexity": "Unknown",
                "bottlenecks": [],
                "suggestions": []
            }

    def optimize_algorithm(self, algorithm_type: str) -> Dict:
        """优化算法"""
        optimizations = {
            "sorting": {
                "current": "bubble_sort",
                "optimized": "quick_sort",
                "improvement": "From O(n²) to O(n log n)"
            },
            "searching": {
                "current": "linear_search",
                "optimized": "binary_search",
                "improvement": "From O(n) to O(log n)"
            },
            "graph": {
                "current": "dfs",
                "optimized": "bfs_with_pruning",
                "improvement": "Reduced search space"
            }
        }

        return optimizations.get(algorithm_type, {})

# ============================================
# 并发优化器
# ============================================

class ConcurrencyOptimizer:
    """并发优化器"""

    def __init__(self, config: PerformanceConfig):
        self.config = config
        self.thread_pool = ThreadPoolExecutor(max_workers=config.thread_pool_size)
        self.process_pool = ProcessPoolExecutor(max_workers=config.process_pool_size)
        self.semaphore = asyncio.Semaphore(config.connection_pool_size)

    async def run_parallel(self, tasks: List[Callable], max_workers: int = None) -> List[Any]:
        """并行运行任务"""
        max_workers = max_workers or self.config.thread_pool_size

        if all(asyncio.iscoroutinefunction(task) for task in tasks):
            # 异步任务
            return await asyncio.gather(*[task() for task in tasks])
        else:
            # 同步任务
            loop = asyncio.get_event_loop()
            futures = [
                loop.run_in_executor(self.thread_pool, task)
                for task in tasks
            ]
            return await asyncio.gather(*futures)

    async def batch_process(self, items: List[Any], processor: Callable, batch_size: int = None) -> List[Any]:
        """批处理"""
        batch_size = batch_size or self.config.batch_size
        results = []

        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]

            if asyncio.iscoroutinefunction(processor):
                batch_results = await asyncio.gather(*[processor(item) for item in batch])
            else:
                loop = asyncio.get_event_loop()
                batch_results = await asyncio.gather(*[
                    loop.run_in_executor(self.thread_pool, processor, item)
                    for item in batch
                ])

            results.extend(batch_results)

        return results

    async def rate_limit(self, func: Callable, rate: int = 10):
        """速率限制装饰器"""
        async with self.semaphore:
            return await func()

    def optimize_concurrency(self, current_threads: int, cpu_usage: float) -> OptimizationSuggestion:
        """优化并发设置"""
        if cpu_usage < 50 and current_threads < psutil.cpu_count():
            return OptimizationSuggestion(
                type=OptimizationType.CPU,
                title="Increase thread pool size",
                description=f"CPU usage is {cpu_usage}%, can increase threads",
                expected_improvement=25,
                implementation=f"Increase thread_pool_size to {psutil.cpu_count()}",
                priority=3,
                estimated_effort="low"
            )

        if cpu_usage > 90:
            return OptimizationSuggestion(
                type=OptimizationType.CPU,
                title="Reduce thread contention",
                description=f"CPU usage is {cpu_usage}%, reduce parallel operations",
                expected_improvement=20,
                implementation="Implement task queuing and throttling",
                priority=2,
                estimated_effort="medium"
            )

        return None

# ============================================
# 性能优化引擎
# ============================================

class PerformanceOptimizationEngine:
    """性能优化引擎"""

    def __init__(self, config: Optional[PerformanceConfig] = None):
        """初始化优化引擎"""
        self.config = config or PerformanceConfig()
        self.profiler = PerformanceProfiler(self.config)
        self.query_optimizer = QueryOptimizer()
        self.cache_optimizer = CacheOptimizer(self.config)
        self.memory_optimizer = MemoryOptimizer(self.config)
        self.algorithm_optimizer = AlgorithmOptimizer()
        self.concurrency_optimizer = ConcurrencyOptimizer(self.config)
        self.redis_client = get_redis_client()
        self.optimization_history = []

    async def analyze_system_performance(self) -> Dict:
        """分析系统性能"""
        # CPU信息
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()

        # 内存信息
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_available = memory.available / 1024 / 1024 / 1024  # GB

        # 磁盘信息
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent

        # 网络信息
        network = psutil.net_io_counters()
        network_sent_mb = network.bytes_sent / 1024 / 1024
        network_recv_mb = network.bytes_recv / 1024 / 1024

        # 进程信息
        process = psutil.Process()
        process_memory = process.memory_info().rss / 1024 / 1024  # MB
        process_threads = process.num_threads()

        return {
            "timestamp": datetime.now().isoformat(),
            "cpu": {
                "usage_percent": cpu_percent,
                "count": cpu_count,
                "level": self._get_performance_level(cpu_percent, [90, 70, 50])
            },
            "memory": {
                "usage_percent": memory_percent,
                "available_gb": memory_available,
                "process_mb": process_memory,
                "level": self._get_performance_level(memory_percent, [90, 70, 50])
            },
            "disk": {
                "usage_percent": disk_percent,
                "level": self._get_performance_level(disk_percent, [90, 70, 50])
            },
            "network": {
                "sent_mb": network_sent_mb,
                "received_mb": network_recv_mb
            },
            "process": {
                "threads": process_threads,
                "memory_mb": process_memory
            }
        }

    def _get_performance_level(self, value: float, thresholds: List[float]) -> str:
        """获取性能级别"""
        if value >= thresholds[0]:
            return PerformanceLevel.CRITICAL.value
        elif value >= thresholds[1]:
            return PerformanceLevel.HIGH.value
        elif value >= thresholds[2]:
            return PerformanceLevel.MEDIUM.value
        else:
            return PerformanceLevel.LOW.value

    async def generate_optimization_plan(self) -> List[OptimizationSuggestion]:
        """生成优化计划"""
        suggestions = []

        # 分析系统性能
        perf = await self.analyze_system_performance()

        # CPU优化
        if perf["cpu"]["usage_percent"] > self.config.cpu_threshold:
            suggestions.append(OptimizationSuggestion(
                type=OptimizationType.CPU,
                title="High CPU usage",
                description=f"CPU usage is {perf['cpu']['usage_percent']}%",
                expected_improvement=30,
                implementation="1. Profile CPU-intensive operations\n2. Optimize algorithms\n3. Use caching",
                priority=1,
                estimated_effort="medium"
            ))

        # 内存优化
        memory_suggestions = self.memory_optimizer.optimize_memory()
        suggestions.extend(memory_suggestions)

        # 缓存优化
        cache_suggestions = await self.cache_optimizer.optimize_cache_strategy()
        suggestions.extend(cache_suggestions)

        # 并发优化
        concurrency_suggestion = self.concurrency_optimizer.optimize_concurrency(
            perf["process"]["threads"],
            perf["cpu"]["usage_percent"]
        )
        if concurrency_suggestion:
            suggestions.append(concurrency_suggestion)

        # 排序建议（按优先级）
        suggestions.sort(key=lambda x: x.priority)

        return suggestions

    async def auto_optimize(self) -> Dict:
        """自动优化"""
        results = {
            "optimizations_applied": [],
            "improvements": {},
            "status": "success"
        }

        # 获取优化建议
        suggestions = await self.generate_optimization_plan()

        for suggestion in suggestions[:5]:  # 只应用前5个建议
            if suggestion.estimated_effort == "low":
                # 自动应用低成本优化
                if suggestion.type == OptimizationType.CACHE:
                    # 增加缓存TTL
                    self.config.cache_ttl *= 2
                    results["optimizations_applied"].append("Increased cache TTL")

                elif suggestion.type == OptimizationType.MEMORY:
                    # 强制垃圾回收
                    gc_result = self.memory_optimizer.force_gc()
                    results["optimizations_applied"].append(f"Forced GC, freed {gc_result['memory_freed_mb']:.1f}MB")

        # 记录优化历史
        self.optimization_history.append({
            "timestamp": datetime.now().isoformat(),
            "suggestions": len(suggestions),
            "applied": len(results["optimizations_applied"]),
            "results": results
        })

        return results

    async def benchmark(self, func: Callable, iterations: int = 100) -> Dict:
        """基准测试"""
        results = {
            "function": func.__name__,
            "iterations": iterations,
            "measurements": []
        }

        for _ in range(iterations):
            start = time.perf_counter()

            if asyncio.iscoroutinefunction(func):
                await func()
            else:
                func()

            duration = (time.perf_counter() - start) * 1000
            results["measurements"].append(duration)

        # 计算统计
        measurements = results["measurements"]
        results["statistics"] = {
            "mean_ms": np.mean(measurements),
            "median_ms": np.median(measurements),
            "std_ms": np.std(measurements),
            "min_ms": min(measurements),
            "max_ms": max(measurements),
            "p95_ms": np.percentile(measurements, 95),
            "p99_ms": np.percentile(measurements, 99)
        }

        return results

    async def monitor_performance(self, duration_seconds: int = 60) -> List[Dict]:
        """监控性能"""
        metrics = []
        end_time = time.time() + duration_seconds

        while time.time() < end_time:
            metric = await self.analyze_system_performance()
            metrics.append(metric)

            # 发送到Redis
            await self.redis_client.publish(
                "performance:metrics",
                json.dumps(metric)
            )

            await asyncio.sleep(1)

        return metrics

    def get_optimization_report(self) -> Dict:
        """获取优化报告"""
        return {
            "cache_statistics": self.cache_optimizer.get_cache_statistics(),
            "memory_analysis": self.memory_optimizer.analyze_memory(),
            "optimization_history": self.optimization_history[-10:],  # 最近10次
            "current_config": {
                "cache_ttl": self.config.cache_ttl,
                "thread_pool_size": self.config.thread_pool_size,
                "process_pool_size": self.config.process_pool_size,
                "batch_size": self.config.batch_size
            }
        }

# ============================================
# 单例实例
# ============================================

_performance_engine_instance: Optional[PerformanceOptimizationEngine] = None

def get_performance_engine() -> PerformanceOptimizationEngine:
    """获取性能优化引擎单例"""
    global _performance_engine_instance
    if _performance_engine_instance is None:
        _performance_engine_instance = PerformanceOptimizationEngine()
    return _performance_engine_instance
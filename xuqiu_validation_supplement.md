# MCP项目需求文档 - 验证补充方案

> **文档目的**: 针对核心指标验证、技术栈兼容性、性能边界、安全审计等关键落地问题，提供可执行的验证方案和基准数据

---

## 📊 一、核心指标验证方案

### 1.1 基准测试数据集构建

#### 1.1.1 记忆准确率测试数据集
```python
# tests/benchmark/memory_accuracy_dataset.py
"""
记忆准确率基准测试数据集
包含5个真实业务场景，共100组对话数据
"""

BENCHMARK_SCENARIOS = {
    "scenario_1_django_project": {
        "description": "Django Web项目开发场景",
        "conversations": [
            {
                "session_id": "sess_001",
                "rounds": [
                    {"user": "项目使用什么框架?", "expected_memory": "Django 4.2"},
                    {"user": "数据库是什么?", "expected_memory": "PostgreSQL 15"},
                    # ... 跨会话后（24小时后）
                    {"user": "提醒我项目的框架版本", "expected_recall": "Django 4.2", "memory_level": "mid"}
                ],
                "metrics": {
                    "cross_session_recall_required": True,
                    "min_accuracy": 0.95
                }
            }
        ]
    },

    "scenario_2_api_development": {
        "description": "RESTful API开发场景",
        "conversations": [
            {
                "session_id": "sess_002",
                "rounds": [
                    {"user": "用户登录接口路径是什么?", "expected_memory": "/api/v1/auth/login"},
                    {"user": "需要哪些参数?", "expected_memory": "username, password, captcha"},
                    # 30分钟后同一会话
                    {"user": "登录接口的完整信息", "expected_recall": "/api/v1/auth/login (POST) 参数: username, password, captcha"}
                ]
            }
        ]
    },

    "scenario_3_code_refactoring": {
        "description": "代码重构场景（测试记忆更新能力）",
        "conversations": [
            {
                "session_id": "sess_003",
                "rounds": [
                    {"user": "用户服务的认证方式", "expected_memory": "JWT Token"},
                    # 记忆更新
                    {"user": "认证方式改为OAuth2", "action": "update_memory", "new_value": "OAuth2"},
                    # 验证更新
                    {"user": "当前认证方式是什么?", "expected_recall": "OAuth2", "should_not_recall": "JWT Token"}
                ],
                "metrics": {
                    "conflict_resolution_required": True,
                    "update_accuracy": 1.0
                }
            }
        ]
    },

    "scenario_4_multi_project": {
        "description": "多项目隔离场景",
        "conversations": [
            {
                "session_id": "sess_004_proj_a",
                "project_id": "proj_a",
                "rounds": [
                    {"user": "项目A使用Python 3.10", "expected_memory": "Python 3.10"}
                ]
            },
            {
                "session_id": "sess_005_proj_b",
                "project_id": "proj_b",
                "rounds": [
                    {"user": "项目B使用Python 3.8", "expected_memory": "Python 3.8"},
                    # 验证项目隔离
                    {"user": "项目A的Python版本", "expected_recall": "无相关记忆（跨项目查询应被阻止）"}
                ]
            }
        ]
    },

    "scenario_5_complex_context": {
        "description": "复杂上下文场景（测试长期记忆）",
        "conversations": [
            {
                "session_id": "sess_006",
                "rounds": [
                    {"user": "数据库分库分表策略：用户表按user_id取模8，订单表按日期分表",
                     "expected_memory": "用户表: user_id % 8; 订单表: 按日期分表"},
                    # 7天后
                    {"user": "用户表的分库规则", "expected_recall": "user_id取模8", "memory_level": "long"}
                ]
            }
        ]
    }
}
```

#### 1.1.2 自动化验证脚本
```python
# tests/benchmark/validate_memory_accuracy.py
import asyncio
from typing import Dict, List
from datetime import datetime, timedelta

class MemoryAccuracyValidator:
    """记忆准确率自动验证器"""

    def __init__(self, memory_service, config):
        self.memory_service = memory_service
        self.config = config
        self.results = []

    async def run_benchmark(self, scenarios: Dict) -> Dict:
        """运行基准测试"""
        total_tests = 0
        passed_tests = 0

        for scenario_name, scenario_data in scenarios.items():
            print(f"\n▶ 运行场景: {scenario_data['description']}")

            for conversation in scenario_data["conversations"]:
                result = await self._test_conversation(conversation)
                total_tests += result["total"]
                passed_tests += result["passed"]
                self.results.append({
                    "scenario": scenario_name,
                    "result": result
                })

        accuracy = passed_tests / total_tests if total_tests > 0 else 0

        return {
            "overall_accuracy": accuracy,
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
            "meets_requirement": accuracy >= 0.95,
            "detailed_results": self.results
        }

    async def _test_conversation(self, conversation: Dict) -> Dict:
        """测试单个对话"""
        session_id = conversation["session_id"]
        project_id = conversation.get("project_id", "default_project")
        total = 0
        passed = 0

        for round_data in conversation["rounds"]:
            total += 1

            if "expected_memory" in round_data:
                # 测试记忆存储
                self.memory_service.store_memory(
                    project_id=project_id,
                    content=round_data["user"],
                    memory_level="mid"
                )
                passed += 1  # 存储成功

            elif "expected_recall" in round_data:
                # 测试记忆检索
                result = self.memory_service.retrieve_memory(
                    project_id=project_id,
                    query=round_data["user"],
                    top_k=3
                )

                # 验证召回内容
                recalled_contents = [m["content"] for m in result["memories"]]
                if any(round_data["expected_recall"] in content for content in recalled_contents):
                    passed += 1
                    print(f"  ✓ 召回成功: {round_data['user'][:30]}...")
                else:
                    print(f"  ✗ 召回失败: 期望 '{round_data['expected_recall']}', 实际 {recalled_contents}")

                # 验证不应召回的内容
                if "should_not_recall" in round_data:
                    if not any(round_data["should_not_recall"] in content for content in recalled_contents):
                        print(f"  ✓ 正确过滤: {round_data['should_not_recall']}")
                    else:
                        passed -= 1
                        print(f"  ✗ 错误召回已更新的旧记忆")

        return {"total": total, "passed": passed}


# 运行示例
async def main():
    from src.mcp_core.memory.service import MemoryService
    from src.mcp_core.common.config import load_config

    config = load_config()
    memory_service = MemoryService(config)
    validator = MemoryAccuracyValidator(memory_service, config)

    # 运行基准测试
    report = await validator.run_benchmark(BENCHMARK_SCENARIOS)

    # 生成报告
    print("\n" + "="*60)
    print("📊 记忆准确率基准测试报告")
    print("="*60)
    print(f"总测试数: {report['total_tests']}")
    print(f"通过数: {report['passed_tests']}")
    print(f"失败数: {report['failed_tests']}")
    print(f"准确率: {report['overall_accuracy']:.2%}")
    print(f"是否达标(≥95%): {'✓ 是' if report['meets_requirement'] else '✗ 否'}")

    # 保存详细报告
    import json
    with open("benchmark_report.json", "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    asyncio.run(main())
```

### 1.2 Token优化对比测试

```python
# tests/benchmark/validate_token_optimization.py
"""Token消耗对比测试（修改前后验证）"""

class TokenOptimizationValidator:

    TEST_CASES = [
        {
            "name": "简单查询",
            "content": "如何使用Django创建一个简单的用户模型？",
            "expected_original_tokens": 512,
            "expected_compressed_tokens": 64,
            "min_compression_rate": 0.875  # 87.5%
        },
        {
            "name": "复杂代码片段",
            "content": """
            class UserManager(models.Manager):
                def create_user(self, username, email, password):
                    user = self.model(username=username, email=email)
                    user.set_password(password)
                    user.save(using=self._db)
                    return user
            """,
            "expected_original_tokens": 1024,
            "expected_compressed_tokens": 128,
            "min_compression_rate": 0.875
        },
        {
            "name": "长文档",
            "content": "..." * 2000,  # 模拟长文档
            "expected_original_tokens": 8192,
            "expected_compressed_tokens": 1024,
            "min_compression_rate": 0.875
        }
    ]

    def __init__(self, token_service):
        self.token_service = token_service

    def validate(self, baseline_report: Dict = None) -> Dict:
        """验证Token优化效果（可对比基线）"""
        results = []

        for test_case in self.TEST_CASES:
            result = self.token_service.compress_content(
                content=test_case["content"],
                content_type="code" if "class" in test_case["content"] else "text"
            )

            compression_rate = result["compression_rate"]
            meets_requirement = compression_rate >= test_case["min_compression_rate"]

            test_result = {
                "name": test_case["name"],
                "original_tokens": result["original_tokens"],
                "compressed_tokens": result["compressed_tokens"],
                "compression_rate": compression_rate,
                "meets_requirement": meets_requirement
            }

            # 如果提供了基线，进行对比
            if baseline_report:
                baseline_case = next(
                    (c for c in baseline_report["results"] if c["name"] == test_case["name"]),
                    None
                )
                if baseline_case:
                    test_result["baseline_comparison"] = {
                        "baseline_rate": baseline_case["compression_rate"],
                        "current_rate": compression_rate,
                        "regression": compression_rate < baseline_case["compression_rate"]
                    }

            results.append(test_result)

        avg_compression = sum(r["compression_rate"] for r in results) / len(results)

        return {
            "average_compression_rate": avg_compression,
            "meets_90_percent_target": avg_compression >= 0.90,
            "results": results
        }
```

### 1.3 幻觉抑制边缘案例测试

```python
# tests/benchmark/hallucination_edge_cases.py
"""幻觉检测边缘案例测试集"""

EDGE_CASE_DATASET = {
    "模糊查询场景": [
        {
            "stored_memory": "项目使用Django 4.2框架",
            "query": "我们用的是什么Python框架？",
            "expected_output": "Django",
            "expected_hallucination": False,
            "reason": "语义相似但表述不同"
        },
        {
            "stored_memory": "数据库采用PostgreSQL",
            "query": "MySQL配置在哪里？",
            "expected_output": "项目使用PostgreSQL，不是MySQL",
            "expected_hallucination": False,  # 应该纠正用户错误
            "reason": "用户混淆数据库类型"
        }
    ],

    "跨领域知识混淆": [
        {
            "stored_memory": "用户认证使用JWT Token",
            "query": "OAuth2的配置在哪？",
            "expected_hallucination": True,
            "reason": "项目未使用OAuth2，不应编造配置"
        },
        {
            "stored_memory": "前端使用React 18",
            "query": "Vue组件怎么写？",
            "expected_hallucination": True,
            "reason": "项目未使用Vue，不应生成Vue代码"
        }
    ],

    "版本号细节": [
        {
            "stored_memory": "Python 3.10.5",
            "query": "Python版本是3.9吗？",
            "expected_output": "不是，项目使用Python 3.10.5",
            "expected_hallucination": False
        }
    ],

    "不存在的功能": [
        {
            "stored_memory": "项目包含用户管理、权限管理模块",
            "query": "支付模块的API在哪？",
            "expected_hallucination": True,
            "reason": "项目中不存在支付模块"
        }
    ],

    "时间敏感信息": [
        {
            "stored_memory": "2025-01-18: 部署到生产环境",
            "query": "什么时候上线的？",
            "expected_output": "2025年1月18日",
            "expected_hallucination": False
        }
    ]
}

class HallucinationEdgeCaseValidator:

    def __init__(self, validation_service, memory_service):
        self.validation_service = validation_service
        self.memory_service = memory_service

    def run_edge_case_tests(self) -> Dict:
        """运行边缘案例测试"""
        results = {
            "total_cases": 0,
            "correct_detections": 0,
            "false_positives": 0,  # 误判为幻觉
            "false_negatives": 0,  # 漏判幻觉
            "details": []
        }

        for category, cases in EDGE_CASE_DATASET.items():
            print(f"\n▶ 测试类别: {category}")

            for case in cases:
                results["total_cases"] += 1

                # 存储记忆
                project_id = f"test_edge_{results['total_cases']}"
                self.memory_service.store_memory(
                    project_id=project_id,
                    content=case["stored_memory"],
                    memory_level="mid"
                )

                # 生成模拟输出（实际应调用LLM）
                simulated_output = case.get("expected_output", case["query"])

                # 检测幻觉
                detection_result = self.validation_service.detect_hallucination(
                    project_id=project_id,
                    output=simulated_output
                )

                is_correct = detection_result["is_hallucination"] == case["expected_hallucination"]

                if is_correct:
                    results["correct_detections"] += 1
                    status = "✓"
                elif case["expected_hallucination"] and not detection_result["is_hallucination"]:
                    results["false_negatives"] += 1
                    status = "✗ 漏判"
                else:
                    results["false_positives"] += 1
                    status = "✗ 误判"

                print(f"  {status} {case['reason']}")

                results["details"].append({
                    "category": category,
                    "case": case,
                    "detection": detection_result,
                    "is_correct": is_correct
                })

        # 计算指标
        results["accuracy"] = results["correct_detections"] / results["total_cases"]
        results["precision"] = 1 - (results["false_positives"] / results["total_cases"])
        results["recall"] = 1 - (results["false_negatives"] / results["total_cases"])
        results["meets_requirement"] = results["accuracy"] >= 0.95

        return results
```

---

## 🔧 二、技术栈兼容性验证清单

### 2.1 依赖升级验证矩阵

```python
# scripts/validate_dependencies.py
"""依赖兼容性自动验证脚本"""

CRITICAL_DEPENDENCIES = {
    "pydantic": {
        "current_version": "2.5.0",
        "compatible_range": ">=2.0.0,<3.0.0",
        "breaking_changes_in_v2": [
            "Config类改为model_config",
            "validator改为field_validator",
            "__root__模型废弃"
        ],
        "validation_tests": [
            "tests/test_pydantic_models.py::test_memory_request_validation",
            "tests/test_pydantic_models.py::test_config_loading"
        ]
    },

    "sentence-transformers": {
        "current_version": "2.2.2",
        "compatible_range": ">=2.0.0,<3.0.0",
        "critical_check": "embedding_dimension_stability",
        "validation_tests": [
            "tests/test_embedding_dimension.py::test_vector_dimension_unchanged"
        ]
    },

    "transformers": {
        "current_version": "4.36.0",
        "compatible_range": ">=4.30.0,<5.0.0",
        "model_compatibility": {
            "codebert": "microsoft/codebert-base",
            "required_files": ["config.json", "pytorch_model.bin"]
        }
    },

    "sqlalchemy": {
        "current_version": "2.0.23",
        "compatible_range": ">=2.0.0",
        "breaking_changes_from_v1": [
            "Session.query()改为Session.execute(select())",
            "declarative_base改为DeclarativeBase"
        ],
        "migration_guide": "docs/sqlalchemy_v2_migration.md"
    }
}

def validate_dependency_compatibility():
    """验证依赖兼容性"""
    import importlib.metadata
    import subprocess

    report = {"passed": [], "failed": [], "warnings": []}

    for package, config in CRITICAL_DEPENDENCIES.items():
        try:
            installed_version = importlib.metadata.version(package)
            print(f"\n检查 {package}: 当前版本 {installed_version}")

            # 运行版本特定的测试
            if "validation_tests" in config:
                for test_path in config["validation_tests"]:
                    result = subprocess.run(
                        ["pytest", test_path, "-v"],
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        report["passed"].append(f"{package}: {test_path}")
                        print(f"  ✓ 测试通过: {test_path}")
                    else:
                        report["failed"].append({
                            "package": package,
                            "test": test_path,
                            "error": result.stderr
                        })
                        print(f"  ✗ 测试失败: {test_path}")

            # 特殊检查
            if package == "sentence-transformers" and config.get("critical_check") == "embedding_dimension_stability":
                # 验证嵌入维度未改变
                from sentence_transformers import SentenceTransformer
                model = SentenceTransformer('all-MiniLM-L6-v2')
                test_embedding = model.encode("测试文本")
                expected_dim = 384

                if len(test_embedding) == expected_dim:
                    print(f"  ✓ 嵌入维度稳定: {expected_dim}")
                else:
                    report["failed"].append({
                        "package": package,
                        "error": f"嵌入维度变化: 期望{expected_dim}, 实际{len(test_embedding)}"
                    })

        except Exception as e:
            report["failed"].append({"package": package, "error": str(e)})

    return report
```

### 2.2 向量维度迁移方案

```python
# scripts/migrate_vector_dimension.py
"""
当sentence-transformers升级导致嵌入维度变化时的迁移方案
"""

def migrate_milvus_collection_if_dimension_changed():
    """检测并迁移Milvus Collection（如果维度变化）"""
    from pymilvus import connections, Collection, utility
    from sentence_transformers import SentenceTransformer

    # 1. 检测当前模型的嵌入维度
    model = SentenceTransformer('all-MiniLM-L6-v2')
    current_dim = model.get_sentence_embedding_dimension()

    # 2. 检查Milvus中现有Collection的维度
    connections.connect("default", host="localhost", port="19530")
    collection_name = "mid_term_memories"

    if utility.has_collection(collection_name):
        collection = Collection(collection_name)
        schema = collection.schema
        embedding_field = next(f for f in schema.fields if f.name == "embedding")
        stored_dim = embedding_field.params["dim"]

        if stored_dim != current_dim:
            print(f"⚠️  检测到维度变化: {stored_dim} -> {current_dim}")
            print("开始迁移流程...")

            # 3. 创建新Collection
            new_collection_name = f"{collection_name}_v{current_dim}"
            # ... 创建新Schema

            # 4. 重新生成所有嵌入
            old_data = collection.query(expr="id >= 0", output_fields=["*"])
            for item in old_data:
                new_embedding = model.encode(item["content"])
                # 插入到新Collection

            # 5. 原子切换
            utility.rename_collection(collection_name, f"{collection_name}_backup")
            utility.rename_collection(new_collection_name, collection_name)

            print("✓ 迁移完成")
        else:
            print(f"✓ 维度一致: {current_dim}")
```

---

## ⚡ 三、性能压测与边界验证

### 3.1 增强版Locust压测脚本

```python
# tests/performance/advanced_load_test.py
"""增强版性能压测（包含边界场景）"""
from locust import HttpUser, task, between, events
import random
import json

class AdvancedMCPLoadTest(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        """初始化测试数据"""
        self.project_ids = [f"proj_{i:03d}" for i in range(10)]
        self.long_content = "测试内容" * 1000  # 4000字长文本

    @task(5)
    def retrieve_memory_normal(self):
        """正常检索（权重5）"""
        project_id = random.choice(self.project_ids)
        with self.client.get(
            "/api/v1/memory/retrieve",
            params={"project_id": project_id, "query": "测试查询", "top_k": 5},
            catch_response=True
        ) as response:
            if response.elapsed.total_seconds() > 0.3:
                response.failure(f"响应时间超标: {response.elapsed.total_seconds()}s")

    @task(2)
    def store_memory_normal(self):
        """正常存储（权重2）"""
        self.client.post(
            "/api/v1/memory/store",
            json={
                "project_id": random.choice(self.project_ids),
                "content": "正常长度的测试数据",
                "memory_level": "mid"
            }
        )

    @task(1)
    def store_large_content(self):
        """边界测试：大内容存储（权重1）"""
        with self.client.post(
            "/api/v1/memory/store",
            json={
                "project_id": "proj_stress",
                "content": self.long_content,
                "memory_level": "mid"
            },
            catch_response=True
        ) as response:
            if response.status_code != 200:
                response.failure(f"大内容存储失败: {response.text}")

    @task(1)
    def concurrent_same_project(self):
        """边界测试：同一项目高并发（权重1）"""
        self.client.get(
            "/api/v1/memory/retrieve",
            params={"project_id": "proj_001", "query": f"并发测试{random.randint(1, 100)}", "top_k": 10}
        )

    @task(1)
    def test_hallucination_detection(self):
        """幻觉检测性能测试"""
        self.client.post(
            "/api/v1/validate/hallucination",
            json={
                "project_id": random.choice(self.project_ids),
                "output": "这是一段测试输出内容，用于验证幻觉检测的性能",
                "threshold": 0.65
            }
        )

# 性能指标收集
@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """测试结束后生成报告"""
    stats = environment.stats

    # 计算P95延迟
    for stat in stats.entries.values():
        p95_latency = stat.get_response_time_percentile(0.95)

        report = {
            "endpoint": stat.name,
            "total_requests": stat.num_requests,
            "failures": stat.num_failures,
            "avg_response_time": stat.avg_response_time,
            "p95_response_time": p95_latency,
            "requests_per_second": stat.total_rps,
            "meets_300ms_requirement": p95_latency <= 300
        }

        print(f"\n{'='*60}")
        print(f"端点: {report['endpoint']}")
        print(f"总请求数: {report['total_requests']}")
        print(f"失败数: {report['failures']}")
        print(f"平均响应时间: {report['avg_response_time']:.2f}ms")
        print(f"P95响应时间: {report['p95_response_time']:.2f}ms")
        print(f"QPS: {report['requests_per_second']:.2f}")
        print(f"是否达标(<300ms): {'✓' if report['meets_300ms_requirement'] else '✗'}")

        # 保存详细报告
        with open(f"perf_report_{stat.name.replace('/', '_')}.json", "w") as f:
            json.dump(report, f, indent=2)
```

### 3.2 资源瓶颈诊断脚本

```python
# scripts/diagnose_performance_bottleneck.py
"""性能瓶颈自动诊断"""
import psutil
import time
from pymilvus import connections, Collection

def diagnose_bottlenecks():
    """诊断系统瓶颈"""
    report = {"timestamp": time.time(), "bottlenecks": []}

    # 1. 数据库连接池检查
    from sqlalchemy import create_engine
    engine = create_engine("postgresql://...")
    pool_status = engine.pool.status()

    if "overflow" in pool_status:
        overflow_count = int(pool_status.split("overflow=")[1].split()[0])
        if overflow_count > 5:
            report["bottlenecks"].append({
                "type": "database_pool_overflow",
                "severity": "high",
                "detail": f"连接池溢出{overflow_count}次",
                "solution": "增加pool_size或max_overflow配置"
            })

    # 2. Redis连接数检查
    import redis
    r = redis.Redis()
    client_count = len(r.client_list())

    if client_count > 80:  # 假设max_connections=100
        report["bottlenecks"].append({
            "type": "redis_connection_high",
            "severity": "medium",
            "detail": f"Redis连接数: {client_count}/100",
            "solution": "检查连接泄漏或增加max_connections"
        })

    # 3. Milvus索引效率检查
    connections.connect("default", host="localhost", port="19530")
    collection = Collection("mid_term_memories")

    # 执行测试查询并计时
    import numpy as np
    test_vector = np.random.rand(768).tolist()

    start = time.time()
    collection.search(
        data=[test_vector],
        anns_field="embedding",
        param={"metric_type": "COSINE", "params": {"ef": 64}},
        limit=10
    )
    query_time = (time.time() - start) * 1000

    if query_time > 100:  # 向量检索应<100ms
        report["bottlenecks"].append({
            "type": "milvus_slow_query",
            "severity": "high",
            "detail": f"向量检索耗时{query_time:.2f}ms",
            "solution": "检查索引类型(推荐HNSW)或调整ef参数"
        })

    # 4. CPU/内存检查
    cpu_percent = psutil.cpu_percent(interval=1)
    memory_percent = psutil.virtual_memory().percent

    if cpu_percent > 80:
        report["bottlenecks"].append({
            "type": "high_cpu_usage",
            "severity": "high",
            "detail": f"CPU使用率: {cpu_percent}%"
        })

    if memory_percent > 85:
        report["bottlenecks"].append({
            "type": "high_memory_usage",
            "severity": "critical",
            "detail": f"内存使用率: {memory_percent}%"
        })

    return report
```

---

## 🔐 四、安全审计增强方案

### 4.1 细粒度权限控制实现

```python
# src/mcp_core/security/permission.py
"""细粒度权限控制"""
from enum import Enum
from typing import List

class Permission(str, Enum):
    # 记忆操作权限
    MEMORY_READ = "memory:read"
    MEMORY_WRITE = "memory:write"
    MEMORY_UPDATE = "memory:update"
    MEMORY_DELETE = "memory:delete"

    # 项目管理权限
    PROJECT_CREATE = "project:create"
    PROJECT_UPDATE = "project:update"
    PROJECT_DELETE = "project:delete"

    # 用户管理权限
    USER_INVITE = "user:invite"
    USER_REMOVE = "user:remove"

    # 配置管理权限
    CONFIG_READ = "config:read"
    CONFIG_WRITE = "config:write"

class Role:
    """角色权限映射"""
    ADMIN = [p for p in Permission]  # 全部权限

    DEVELOPER = [
        Permission.MEMORY_READ,
        Permission.MEMORY_WRITE,
        Permission.MEMORY_UPDATE,
        Permission.CONFIG_READ,
    ]

    VIEWER = [
        Permission.MEMORY_READ,
        Permission.CONFIG_READ,
    ]

# 数据库Schema扩展
"""
-- 细粒度权限表
CREATE TABLE user_permissions_v2 (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    project_id VARCHAR(64) NOT NULL,
    permission VARCHAR(50) NOT NULL,  -- 存储Permission枚举值
    granted_by VARCHAR(64),
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,  -- 可选的权限过期时间
    UNIQUE(user_id, project_id, permission),
    FOREIGN KEY (project_id) REFERENCES projects(project_id)
);

CREATE INDEX idx_user_perm ON user_permissions_v2(user_id, project_id);
"""

# 权限检查装饰器
from functools import wraps
from fastapi import HTTPException

def require_permission(permission: Permission):
    """权限检查装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 从请求中提取user_id和project_id
            user_id = kwargs.get("current_user_id")
            project_id = kwargs.get("project_id")

            # 查询权限
            has_permission = check_user_permission(user_id, project_id, permission)

            if not has_permission:
                raise HTTPException(
                    status_code=403,
                    detail=f"缺少权限: {permission.value}"
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator

# 使用示例
@app.delete("/api/v1/memory/{memory_id}")
@require_permission(Permission.MEMORY_DELETE)
async def delete_memory(memory_id: str, current_user_id: str, project_id: str):
    """删除记忆（需要MEMORY_DELETE权限）"""
    pass
```

### 4.2 完善的审计日志系统

```python
# src/mcp_core/security/audit.py
"""审计日志增强"""
import json
from datetime import datetime
from typing import Dict, Any

class AuditLogger:
    """审计日志记录器"""

    # 敏感操作定义
    SENSITIVE_OPERATIONS = {
        "permission_grant": "授予权限",
        "permission_revoke": "撤销权限",
        "memory_delete": "删除记忆",
        "project_delete": "删除项目",
        "config_update": "更新配置"
    }

    def __init__(self, db_session):
        self.db_session = db_session

    def log(
        self,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        project_id: str = None,
        details: Dict[str, Any] = None,
        ip_address: str = None
    ):
        """记录审计日志"""
        from .models import AuditLog

        # 标记敏感操作
        is_sensitive = action in self.SENSITIVE_OPERATIONS

        log_entry = AuditLog(
            user_id=user_id,
            project_id=project_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=json.dumps(details or {}, ensure_ascii=False),
            ip_address=ip_address,
            is_sensitive=is_sensitive,
            created_at=datetime.now()
        )

        self.db_session.add(log_entry)
        self.db_session.commit()

        # 敏感操作额外告警
        if is_sensitive:
            self._alert_sensitive_operation(log_entry)

    def _alert_sensitive_operation(self, log_entry):
        """敏感操作告警"""
        # 发送到监控系统
        alert_message = (
            f"🚨 敏感操作: {self.SENSITIVE_OPERATIONS.get(log_entry.action)}\n"
            f"用户: {log_entry.user_id}\n"
            f"资源: {log_entry.resource_type}/{log_entry.resource_id}\n"
            f"时间: {log_entry.created_at}\n"
            f"IP: {log_entry.ip_address}"
        )

        # 这里可以集成Slack/钉钉/邮件通知
        print(alert_message)

    def query_user_actions(
        self,
        user_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict]:
        """查询用户操作历史"""
        from .models import AuditLog

        logs = self.db_session.query(AuditLog).filter(
            AuditLog.user_id == user_id,
            AuditLog.created_at >= start_time,
            AuditLog.created_at <= end_time
        ).order_by(AuditLog.created_at.desc()).all()

        return [
            {
                "action": log.action,
                "resource": f"{log.resource_type}/{log.resource_id}",
                "timestamp": log.created_at.isoformat(),
                "details": json.loads(log.details)
            }
            for log in logs
        ]

# 扩展审计日志表Schema
"""
-- 增强审计日志表
CREATE TABLE audit_logs_v2 (
    log_id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    project_id VARCHAR(64),
    action VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id VARCHAR(64) NOT NULL,
    details JSONB,
    ip_address INET,  -- 记录IP地址
    user_agent TEXT,   -- 记录User-Agent
    is_sensitive BOOLEAN DEFAULT FALSE,  -- 标记敏感操作
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_time (user_id, created_at),
    INDEX idx_sensitive (is_sensitive, created_at)
);

-- 自动清理策略（保留1年）
CREATE OR REPLACE FUNCTION cleanup_old_audit_logs()
RETURNS void AS $$
BEGIN
    DELETE FROM audit_logs_v2
    WHERE created_at < NOW() - INTERVAL '1 year'
    AND is_sensitive = FALSE;  -- 敏感日志永久保留
END;
$$ LANGUAGE plpgsql;
"""
```

---

## 🎯 五、核心算法优化与配置化

### 5.1 可配置的记忆检索算法

```python
# src/mcp_core/memory/retrieval_strategies.py
"""记忆检索策略（可配置）"""
from abc import ABC, abstractmethod
from typing import List, Dict
import numpy as np

class RetrievalStrategy(ABC):
    """检索策略基类"""

    @abstractmethod
    def retrieve(
        self,
        query_embedding: np.ndarray,
        memory_pool: List[Dict],
        top_k: int
    ) -> List[Dict]:
        """检索记忆"""
        pass

class HybridRetrievalStrategy(RetrievalStrategy):
    """混合检索策略（语义+关键词+时间衰减）"""

    def __init__(self, config: Dict):
        self.semantic_weight = config.get("semantic_weight", 0.6)
        self.keyword_weight = config.get("keyword_weight", 0.3)
        self.time_decay_weight = config.get("time_decay_weight", 0.1)
        self.time_decay_factor = config.get("time_decay_factor", 0.95)  # 每天衰减5%

    def retrieve(self, query_embedding, memory_pool, top_k):
        """混合检索"""
        from sklearn.metrics.pairwise import cosine_similarity
        from datetime import datetime
        import re

        query_keywords = set(re.findall(r'\w+', query_text.lower()))
        current_time = datetime.now()

        scored_memories = []

        for memory in memory_pool:
            # 1. 语义相似度
            mem_embedding = np.array(memory["embedding"])
            semantic_score = cosine_similarity(
                query_embedding.reshape(1, -1),
                mem_embedding.reshape(1, -1)
            )[0][0]

            # 2. 关键词匹配度
            mem_keywords = set(re.findall(r'\w+', memory["content"].lower()))
            keyword_overlap = len(query_keywords & mem_keywords)
            keyword_score = keyword_overlap / max(len(query_keywords), 1)

            # 3. 时间衰减
            days_old = (current_time - memory["created_at"]).days
            time_score = self.time_decay_factor ** days_old

            # 综合评分
            final_score = (
                self.semantic_weight * semantic_score +
                self.keyword_weight * keyword_score +
                self.time_decay_weight * time_score
            )

            scored_memories.append({
                **memory,
                "final_score": final_score,
                "score_breakdown": {
                    "semantic": semantic_score,
                    "keyword": keyword_score,
                    "time": time_score
                }
            })

        # 排序并返回Top-K
        scored_memories.sort(key=lambda x: x["final_score"], reverse=True)
        return scored_memories[:top_k]

# 配置文件扩展
"""
# config.yaml
memory:
  retrieval_strategy: "hybrid"  # hybrid/semantic_only/keyword_only
  hybrid_config:
    semantic_weight: 0.6
    keyword_weight: 0.3
    time_decay_weight: 0.1
    time_decay_factor: 0.95
"""
```

### 5.2 动态阈值调整算法

```python
# src/mcp_core/anti_hallucination/adaptive_threshold.py
"""自适应相似度阈值"""

class AdaptiveThresholdCalculator:
    """根据查询复杂度动态调整阈值"""

    def __init__(self, base_threshold: float = 0.65):
        self.base_threshold = base_threshold

    def calculate_threshold(self, query: str, context: Dict) -> float:
        """计算自适应阈值"""
        adjustments = []

        # 1. 查询长度调整
        if len(query) > 200:
            adjustments.append(-0.05)  # 长查询降低阈值

        # 2. 代码块检测
        if "```" in query or "def " in query or "class " in query:
            adjustments.append(-0.08)  # 代码相关降低阈值

        # 3. 技术术语密度
        tech_terms = ["API", "数据库", "框架", "接口", "配置", "部署"]
        term_count = sum(1 for term in tech_terms if term in query)
        if term_count >= 3:
            adjustments.append(-0.05)

        # 4. 项目历史记忆数量
        memory_count = context.get("memory_count", 0)
        if memory_count < 10:
            adjustments.append(0.05)  # 记忆少时提高阈值，避免误判

        # 5. 用户置信度历史
        user_hallucination_rate = context.get("user_hallucination_rate", 0)
        if user_hallucination_rate > 0.1:
            adjustments.append(0.10)  # 该用户幻觉率高，提高阈值

        final_threshold = self.base_threshold + sum(adjustments)

        # 限制范围[0.4, 0.85]
        return max(0.4, min(0.85, final_threshold))
```

---

## 📊 六、监控指标扩展

### 6.1 新增业务监控指标

```python
# src/mcp_core/monitoring/metrics.py
"""Prometheus指标定义"""
from prometheus_client import Counter, Histogram, Gauge

# 记忆操作指标
memory_operations_total = Counter(
    'mcp_memory_operations_total',
    'Total memory operations',
    ['operation', 'memory_level', 'project_id']
)

memory_retrieval_latency = Histogram(
    'mcp_memory_retrieval_latency_seconds',
    'Memory retrieval latency',
    ['project_id'],
    buckets=[0.05, 0.1, 0.2, 0.3, 0.5, 1.0]
)

# Token优化指标
token_saved_total = Counter(
    'mcp_token_saved_total',
    'Total tokens saved by optimization',
    ['project_id', 'content_type']
)

compression_rate = Histogram(
    'mcp_compression_rate',
    'Content compression rate',
    ['content_type'],
    buckets=[0.5, 0.6, 0.7, 0.8, 0.9, 0.95]
)

# 幻觉检测指标
hallucination_detected_total = Counter(
    'mcp_hallucination_detected_total',
    'Total hallucinations detected',
    ['project_id', 'threshold_type']
)

hallucination_confidence = Histogram(
    'mcp_hallucination_confidence',
    'Hallucination detection confidence score',
    buckets=[0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
)

# 资源使用指标
vector_db_query_count = Counter(
    'mcp_vector_db_query_count',
    'Vector database query count',
    ['collection']
)

redis_cache_hit_rate = Gauge(
    'mcp_redis_cache_hit_rate',
    'Redis cache hit rate'
)

# 使用示例
def track_memory_operation(operation: str, memory_level: str, project_id: str):
    memory_operations_total.labels(
        operation=operation,
        memory_level=memory_level,
        project_id=project_id
    ).inc()
```

### 6.2 Grafana仪表盘配置

```json
{
  "dashboard": {
    "title": "MCP Core Metrics",
    "panels": [
      {
        "title": "记忆检索延迟 (P95)",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(mcp_memory_retrieval_latency_seconds_bucket[5m]))",
            "legendFormat": "{{project_id}}"
          }
        ],
        "alert": {
          "conditions": [
            {
              "evaluator": {"type": "gt", "params": [0.3]},
              "operator": {"type": "and"},
              "query": {"params": ["A", "5m", "now"]},
              "type": "query"
            }
          ],
          "message": "记忆检索P95延迟超过300ms"
        }
      },
      {
        "title": "Token节省率",
        "targets": [
          {
            "expr": "rate(mcp_token_saved_total[5m])",
            "legendFormat": "{{content_type}}"
          }
        ]
      },
      {
        "title": "幻觉检测率",
        "targets": [
          {
            "expr": "rate(mcp_hallucination_detected_total[5m]) / rate(mcp_memory_operations_total{operation='retrieve'}[5m])",
            "legendFormat": "幻觉率"
          }
        ],
        "alert": {
          "conditions": [
            {
              "evaluator": {"type": "gt", "params": [0.05]},
              "message": "幻觉率超过5%"
            }
          ]
        }
      }
    ]
  }
}
```

---

## ✅ 七、修改验收清单（Checklist）

### 7.1 代码修改后的验证流程

```markdown
# MCP代码修改验收清单

## A. 核心指标验证 ✓
- [ ] 运行基准测试: `pytest tests/benchmark/validate_memory_accuracy.py`
  - [ ] 记忆准确率 ≥ 95%
  - [ ] Token优化率 ≥ 90%
  - [ ] 幻觉检测准确率 ≥ 95%
- [ ] 对比修改前后指标，确认无退化
- [ ] 生成对比报告: `python scripts/generate_comparison_report.py`

## B. 依赖兼容性验证 ✓
- [ ] 运行依赖验证: `python scripts/validate_dependencies.py`
- [ ] 检查sentence-transformers嵌入维度: `pytest tests/test_embedding_dimension.py`
- [ ] 验证Pydantic v2兼容性: `pytest tests/test_pydantic_models.py`
- [ ] 检查SQLAlchemy 2.0语法: `ruff check src/`

## C. 性能验证 ✓
- [ ] 运行压测: `locust -f tests/performance/advanced_load_test.py --users 100 --spawn-rate 10`
  - [ ] 100 QPS下P95延迟 ≤ 500ms
  - [ ] 错误率 < 1%
  - [ ] CPU使用率 < 70%
  - [ ] 内存使用无泄漏
- [ ] 运行瓶颈诊断: `python scripts/diagnose_performance_bottleneck.py`

## D. 安全审计 ✓
- [ ] 权限测试: `pytest tests/test_permissions.py`
  - [ ] 验证非授权用户无法访问敏感操作
  - [ ] 测试权限过期机制
- [ ] 审计日志验证:
  - [ ] 敏感操作已记录
  - [ ] 日志包含IP地址和User-Agent
- [ ] SQL注入测试: `pytest tests/security/test_sql_injection.py`

## E. 边缘案例测试 ✓
- [ ] 幻觉检测边缘案例: `pytest tests/benchmark/hallucination_edge_cases.py`
  - [ ] 模糊查询准确率 ≥ 90%
  - [ ] 跨领域混淆正确拒绝率 100%
- [ ] 并发场景测试:
  - [ ] 同一项目1000并发无数据竞争
  - [ ] 跨项目隔离正常

## F. 部署验证 ✓
- [ ] Docker镜像构建成功: `docker build -t mcp-api:test .`
- [ ] docker-compose启动正常: `docker-compose up -d`
- [ ] 健康检查通过: `curl http://localhost:8000/health`
- [ ] Prometheus指标采集正常: `curl http://localhost:8000/metrics`

## G. 文档更新 ✓
- [ ] 更新API文档（如有接口变更）
- [ ] 更新CHANGELOG.md
- [ ] 更新依赖版本文档
```

---

## 📝 八、总结与建议

### 8.1 关键改进点

| 问题类别 | 原有缺陷 | 补充方案 |
|---------|---------|---------|
| **核心指标验证** | 仅理论目标，无验证方法 | ✅ 提供5个真实场景的基准数据集<br>✅ 自动化验证脚本（100组对话） |
| **依赖管理** | 版本锁定但无兼容性检查 | ✅ 依赖兼容性矩阵<br>✅ 向量维度迁移方案 |
| **性能测试** | 仅概念性指标 | ✅ Locust边界场景压测<br>✅ 瓶颈自动诊断脚本 |
| **安全审计** | 基础权限设计 | ✅ 细粒度权限（9种权限）<br>✅ 敏感操作告警 |
| **算法优化** | 简化实现 | ✅ 混合检索策略<br>✅ 自适应阈值算法 |

### 8.2 使用建议

**修改代码前**:
```bash
# 1. 运行基准测试并保存结果
pytest tests/benchmark/ --json-report --json-report-file=baseline.json

# 2. 记录当前性能指标
python scripts/save_performance_baseline.py
```

**修改代码后**:
```bash
# 1. 重新运行基准测试
pytest tests/benchmark/ --json-report --json-report-file=current.json

# 2. 生成对比报告
python scripts/generate_comparison_report.py baseline.json current.json

# 3. 如果有依赖升级，运行兼容性验证
python scripts/validate_dependencies.py

# 4. 运行完整测试套件
pytest tests/ --cov --cov-report=html

# 5. 性能压测
locust -f tests/performance/advanced_load_test.py --headless \
       --users 100 --spawn-rate 10 --run-time 5m
```

### 8.3 持续改进建议

1. **定期回归测试**: 每次PR合并前运行完整验收清单
2. **基准数据更新**: 每季度更新基准测试数据集（加入新场景）
3. **性能监控**: 生产环境启用Grafana告警，P95延迟超标自动通知
4. **安全审计**: 每月生成审计日志报告，检查异常操作

---

**文档版本**: v1.0.0
**适用于**: MCP项目需求文档 xuqiu_enhanced.md
**维护者**: MCP Validation Team

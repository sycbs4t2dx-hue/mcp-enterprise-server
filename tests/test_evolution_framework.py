#!/usr/bin/env python3
"""
智能进化系统自动化测试框架
提供单元测试、集成测试、端到端测试
"""

import os
import sys
import json
import time
import asyncio
import unittest
from datetime import datetime
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, patch, MagicMock
import numpy as np

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.mcp_core.services.learning_system import get_learning_system, CodingSession
from src.mcp_core.services.pattern_recognizer import get_pattern_recognizer
from src.mcp_core.services.experience_manager import get_experience_manager, Experience
from src.mcp_core.services.graph_generator import get_graph_generator
from src.mcp_core.services.collaboration_controller import (
    get_collaboration_controller,
    AIAgent,
    Task,
    LockType,
    LockLevel
)

# ============================================
# 测试基类
# ============================================

class EvolutionTestBase(unittest.TestCase):
    """测试基类"""

    @classmethod
    def setUpClass(cls):
        """设置测试类"""
        cls.test_project_id = "test_evolution_auto"
        cls.test_data_path = "/tmp/test_evolution_data"

        # 创建测试目录
        os.makedirs(cls.test_data_path, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        """清理测试类"""
        # 清理测试数据
        import shutil
        if os.path.exists(cls.test_data_path):
            shutil.rmtree(cls.test_data_path)

    def create_test_session(self, **kwargs) -> CodingSession:
        """创建测试会话"""
        defaults = {
            "session_id": f"test_session_{time.time()}",
            "project_id": self.test_project_id,
            "context_type": "test",
            "problem_description": "Test problem",
            "solution_description": "Test solution",
            "code_before": "def test(): pass",
            "code_after": "def test(): return True",
            "files_modified": ["test.py"],
            "time_spent": 100,
            "lines_changed": 1,
            "bugs_fixed": 0,
            "bugs_introduced": 0
        }
        defaults.update(kwargs)
        return CodingSession(**defaults)

    def create_test_experience(self, **kwargs) -> Experience:
        """创建测试经验"""
        defaults = {
            "experience_id": f"test_exp_{time.time()}",
            "experience_type": "solution",
            "category": "test",
            "title": "Test Experience",
            "description": "Test description",
            "problem": "Test problem",
            "solution": "Test solution"
        }
        defaults.update(kwargs)
        return Experience(**defaults)

# ============================================
# 单元测试
# ============================================

class TestLearningSystem(EvolutionTestBase):
    """学习系统单元测试"""

    def setUp(self):
        """设置测试"""
        self.learning_system = get_learning_system()

    def test_learn_from_session(self):
        """测试从会话学习"""
        session = self.create_test_session()
        result = self.learning_system.learn_from_session(session)

        self.assertIsNotNone(result)
        self.assertIn("patterns_extracted", result)
        self.assertIn("experience_id", result)
        self.assertGreaterEqual(result["patterns_extracted"], 0)

    def test_suggest_solution(self):
        """测试建议解决方案"""
        # 先学习一些经验
        for i in range(3):
            session = self.create_test_session(
                session_id=f"learn_{i}",
                problem_description=f"Problem {i}",
                solution_description=f"Solution {i}"
            )
            self.learning_system.learn_from_session(session)

        # 获取建议
        context = {
            "type": "test",
            "problem": "Similar problem",
            "files": ["test.py"]
        }
        suggestions = self.learning_system.suggest_solution(context, top_k=2)

        self.assertIsInstance(suggestions, list)
        self.assertLessEqual(len(suggestions), 2)

        if suggestions:
            suggestion = suggestions[0]
            self.assertGreater(suggestion.confidence, 0)
            self.assertIsNotNone(suggestion.solution)

    def test_extract_patterns(self):
        """测试模式提取"""
        session = self.create_test_session(
            code_before="def old(): return []",
            code_after="@lru_cache\ndef new(): return []"
        )
        patterns = self.learning_system.extract_patterns(session)

        self.assertIsInstance(patterns, list)
        # 应该检测到装饰器模式
        pattern_names = [p.pattern_name for p in patterns]
        self.assertTrue(any("decorator" in name.lower() for name in pattern_names))

    def test_evaluate_experience_value(self):
        """测试经验价值评估"""
        session = self.create_test_session(
            bugs_fixed=5,
            bugs_introduced=0,
            time_spent=300
        )
        value = self.learning_system.evaluate_experience_value(session, [])

        self.assertIsInstance(value, float)
        self.assertGreaterEqual(value, 0)
        self.assertLessEqual(value, 1)

class TestPatternRecognizer(EvolutionTestBase):
    """模式识别器单元测试"""

    def setUp(self):
        """设置测试"""
        self.recognizer = get_pattern_recognizer()

    def test_recognize_singleton_pattern(self):
        """测试单例模式识别"""
        code = """
class Singleton:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
        """

        patterns = self.recognizer.recognize_patterns(code, {}, deep_analysis=True)

        self.assertIsInstance(patterns, list)
        self.assertGreater(len(patterns), 0)

        # 应该识别到单例模式
        pattern_names = [p.pattern_name for p in patterns]
        self.assertTrue(any("singleton" in name.lower() for name in pattern_names))

    def test_detect_anti_patterns(self):
        """测试反模式检测"""
        code = """
def complex_function(data):
    result = []
    for item in data:
        if item > 0:
            if item < 10:
                if item % 2 == 0:
                    if item > 5:
                        result.append(item * 2)
                    else:
                        result.append(item)
                else:
                    result.append(item + 1)
    return result
        """

        patterns = self.recognizer.recognize_patterns(code, {}, deep_analysis=True)

        # 应该检测到深度嵌套或高复杂度
        anti_patterns = [p for p in patterns if p.pattern_type == "anti_pattern"]
        self.assertGreater(len(anti_patterns), 0)

    def test_feature_extraction(self):
        """测试特征提取"""
        code = "def test(): return cache.get('key', default_value)"
        preprocessed = self.recognizer.preprocess_code(code)
        features = self.recognizer.extract_all_features(preprocessed, {})

        self.assertIn("structural", features)
        self.assertIn("semantic", features)
        self.assertIn("behavioral", features)
        self.assertIn("quality", features)

        # 应该有一些特征被提取
        total_features = sum(len(f) for f in features.values())
        self.assertGreater(total_features, 0)

class TestExperienceManager(EvolutionTestBase):
    """经验管理器单元测试"""

    def setUp(self):
        """设置测试"""
        self.manager = get_experience_manager()

    def test_store_and_retrieve_experience(self):
        """测试存储和检索经验"""
        experience = self.create_test_experience()

        # 存储经验
        exp_id = self.manager.store_experience(experience)
        self.assertIsNotNone(exp_id)

        # 检索经验
        recommendations = self.manager.retrieve_experience(
            "test problem",
            {"type": "test"},
            top_k=5
        )

        self.assertIsInstance(recommendations, list)

    def test_experience_evolution(self):
        """测试经验演化"""
        experience = self.create_test_experience()
        exp_id = self.manager.store_experience(experience)

        # 提供反馈
        feedback = {
            "success": True,
            "rating": 4.5,
            "comment": "Very helpful",
            "improvement": "Could add more examples"
        }

        self.manager.evolve_experience(exp_id, feedback)

        # 获取更新后的经验
        updated_exp = self.manager.get_experience(exp_id)
        self.assertIsNotNone(updated_exp)
        self.assertEqual(updated_exp.usage_count, 1)
        self.assertEqual(updated_exp.success_count, 1)

    def test_experience_sharing(self):
        """测试经验共享"""
        experience = self.create_test_experience()
        exp_id = self.manager.store_experience(experience)

        # 共享到另一个项目
        target_project = "target_project"
        new_id = self.manager.share_experience(exp_id, target_project, adapt=True)

        self.assertIsNotNone(new_id)
        self.assertNotEqual(new_id, exp_id)

        # 检查新经验
        shared_exp = self.manager.get_experience(new_id)
        self.assertIsNotNone(shared_exp)
        self.assertEqual(shared_exp.project_id, target_project)

class TestCollaborationController(EvolutionTestBase):
    """协作控制器单元测试"""

    def setUp(self):
        """设置测试"""
        self.controller = get_collaboration_controller()

    def test_task_assignment(self):
        """测试任务分配"""
        # 创建代理
        agents = [
            AIAgent("agent1", "Agent 1", ["coding", "testing"]),
            AIAgent("agent2", "Agent 2", ["coding", "review"])
        ]

        for agent in agents:
            self.controller.agents[agent.agent_id] = agent

        # 创建任务
        task = Task(
            task_id="test_task",
            task_type="coding",
            description="Test task",
            files=["file1.py", "file2.py"],
            estimated_time=100
        )

        # 分配任务
        result = self.controller.assign_task(task, agents)

        self.assertTrue(result["success"])
        self.assertIn("assignments", result)
        self.assertGreater(result["total_subtasks"], 0)

    def test_lock_mechanism(self):
        """测试锁机制"""
        # 请求锁
        lock1 = self.controller.request_lock(
            agent_id="agent1",
            lock_type=LockType.FILE,
            resource_id="test_file.py",
            resource_path="test_file.py",
            intent="testing"
        )

        self.assertIsNotNone(lock1)
        self.assertEqual(lock1.agent_id, "agent1")

        # 同一代理请求同一资源应该等待
        lock2 = self.controller.request_lock(
            agent_id="agent2",
            lock_type=LockType.FILE,
            resource_id="test_file.py",
            resource_path="test_file.py",
            intent="testing"
        )

        self.assertIsNotNone(lock2)
        self.assertEqual(lock2.status.value, "waiting")

        # 释放第一个锁
        success = self.controller.release_lock(lock1.lock_id)
        self.assertTrue(success)

        # 清理
        if lock2:
            self.controller.release_lock(lock2.lock_id)

    def test_conflict_detection(self):
        """测试冲突检测"""
        # 设置锁
        lock = self.controller.request_lock(
            agent_id="agent1",
            lock_type=LockType.FILE,
            resource_id="conflict_file.py",
            resource_path="conflict_file.py",
            intent="editing"
        )

        # 另一个代理尝试修改同一文件
        changes = {
            "agent_id": "agent2",
            "files": ["conflict_file.py"],
            "description": "Conflicting change"
        }

        result = self.controller.prevent_conflicts("agent2", changes)

        self.assertEqual(result["status"], "conflicts_detected")
        self.assertGreater(len(result["conflicts"]), 0)

        # 清理
        if lock:
            self.controller.release_lock(lock.lock_id)

# ============================================
# 集成测试
# ============================================

class TestIntegration(EvolutionTestBase):
    """集成测试"""

    def test_learning_and_pattern_integration(self):
        """测试学习系统和模式识别集成"""
        learning_system = get_learning_system()
        recognizer = get_pattern_recognizer()

        # 创建包含模式的会话
        code_with_pattern = """
@lru_cache(maxsize=128)
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
        """

        session = self.create_test_session(
            code_before="def fibonacci(n): return n",
            code_after=code_with_pattern
        )

        # 学习会话
        result = learning_system.learn_from_session(session)

        # 验证模式被识别和存储
        self.assertGreater(result["patterns_extracted"], 0)

        # 识别模式
        patterns = recognizer.recognize_patterns(code_with_pattern, {})
        pattern_names = [p.pattern_name for p in patterns]

        # 应该识别到缓存和递归模式
        self.assertTrue(any("cache" in name.lower() or "recursion" in name.lower()
                          for name in pattern_names))

    def test_experience_and_suggestion_integration(self):
        """测试经验管理和建议集成"""
        learning_system = get_learning_system()
        manager = get_experience_manager()

        # 学习多个会话
        for i in range(5):
            session = self.create_test_session(
                session_id=f"integration_{i}",
                problem_description=f"Integration problem {i}",
                solution_description=f"Integration solution {i}",
                bugs_fixed=i,
                time_spent=100 * (i + 1)
            )
            learning_system.learn_from_session(session)

        # 请求建议
        context = {
            "type": "test",
            "problem": "Similar integration problem",
            "files": ["integration.py"]
        }

        suggestions = learning_system.suggest_solution(context, top_k=3)

        self.assertGreater(len(suggestions), 0)

        # 验证建议质量
        best_suggestion = suggestions[0]
        self.assertGreater(best_suggestion.confidence, 0.3)
        self.assertIsNotNone(best_suggestion.reasoning)

    async def test_websocket_communication(self):
        """测试WebSocket通信"""
        from src.mcp_core.services.websocket_server import WebSocketServer

        # 启动测试服务器
        server = WebSocketServer("localhost", 8767)

        # 模拟客户端连接和消息
        # 这需要实际的WebSocket客户端连接
        # 在单元测试中我们只验证服务器初始化
        self.assertIsNotNone(server)
        self.assertEqual(server.port, 8767)

# ============================================
# 性能测试
# ============================================

class TestPerformance(EvolutionTestBase):
    """性能测试"""

    def test_learning_performance(self):
        """测试学习系统性能"""
        learning_system = get_learning_system()

        start_time = time.time()
        sessions_processed = 0

        # 处理100个会话
        for i in range(100):
            session = self.create_test_session(
                session_id=f"perf_{i}",
                code_before=f"def func_{i}(): pass",
                code_after=f"def func_{i}(): return {i}"
            )
            learning_system.learn_from_session(session)
            sessions_processed += 1

        elapsed = time.time() - start_time
        throughput = sessions_processed / elapsed

        print(f"\n学习系统性能:")
        print(f"  处理会话数: {sessions_processed}")
        print(f"  总耗时: {elapsed:.2f}秒")
        print(f"  吞吐量: {throughput:.2f} sessions/秒")

        # 性能基准
        self.assertGreater(throughput, 5)  # 至少5个会话/秒

    def test_pattern_recognition_performance(self):
        """测试模式识别性能"""
        recognizer = get_pattern_recognizer()

        # 生成测试代码
        test_codes = []
        for i in range(50):
            code = f"""
class TestClass_{i}:
    def __init__(self):
        self.value = {i}

    def method_{i}(self):
        for j in range(10):
            if j > 5:
                return j * 2
        return 0
            """
            test_codes.append(code)

        start_time = time.time()
        patterns_found = 0

        for code in test_codes:
            patterns = recognizer.recognize_patterns(code, {}, deep_analysis=False)
            patterns_found += len(patterns)

        elapsed = time.time() - start_time
        throughput = len(test_codes) / elapsed

        print(f"\n模式识别性能:")
        print(f"  分析代码数: {len(test_codes)}")
        print(f"  发现模式数: {patterns_found}")
        print(f"  总耗时: {elapsed:.2f}秒")
        print(f"  吞吐量: {throughput:.2f} codes/秒")

        # 性能基准
        self.assertGreater(throughput, 10)  # 至少10个代码/秒

    def test_lock_contention_performance(self):
        """测试锁竞争性能"""
        controller = get_collaboration_controller()

        # 创建多个代理
        agents = []
        for i in range(10):
            agent = AIAgent(f"perf_agent_{i}", f"Agent {i}", ["coding"])
            controller.agents[agent.agent_id] = agent
            agents.append(agent)

        start_time = time.time()
        locks_acquired = 0
        locks_waited = 0

        # 模拟并发锁请求
        for i in range(100):
            agent_id = f"perf_agent_{i % 10}"
            resource_id = f"file_{i % 5}.py"  # 5个文件，造成竞争

            lock = controller.request_lock(
                agent_id=agent_id,
                lock_type=LockType.FILE,
                resource_id=resource_id,
                resource_path=resource_id,
                intent=f"operation_{i}"
            )

            if lock:
                if lock.status.value == "active":
                    locks_acquired += 1
                else:
                    locks_waited += 1

                # 快速释放锁
                controller.release_lock(lock.lock_id)

        elapsed = time.time() - start_time
        throughput = 100 / elapsed

        print(f"\n锁管理性能:")
        print(f"  锁请求数: 100")
        print(f"  立即获得: {locks_acquired}")
        print(f"  等待获得: {locks_waited}")
        print(f"  总耗时: {elapsed:.2f}秒")
        print(f"  吞吐量: {throughput:.2f} locks/秒")

        # 性能基准
        self.assertGreater(throughput, 50)  # 至少50个锁/秒

# ============================================
# 测试套件
# ============================================

def create_test_suite():
    """创建测试套件"""
    suite = unittest.TestSuite()

    # 添加单元测试
    suite.addTest(unittest.makeSuite(TestLearningSystem))
    suite.addTest(unittest.makeSuite(TestPatternRecognizer))
    suite.addTest(unittest.makeSuite(TestExperienceManager))
    suite.addTest(unittest.makeSuite(TestCollaborationController))

    # 添加集成测试
    suite.addTest(unittest.makeSuite(TestIntegration))

    # 添加性能测试
    suite.addTest(unittest.makeSuite(TestPerformance))

    return suite

def run_tests(verbosity=2):
    """运行所有测试"""
    print("=" * 60)
    print("智能进化系统自动化测试")
    print("=" * 60)
    print(f"测试时间: {datetime.now()}")
    print()

    # 创建测试套件
    suite = create_test_suite()

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)

    # 输出结果摘要
    print("\n" + "=" * 60)
    print("测试结果摘要")
    print("=" * 60)
    print(f"运行测试数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")

    if result.failures:
        print("\n失败的测试:")
        for test, trace in result.failures:
            print(f"  - {test}: {trace.split(chr(10))[0]}")

    if result.errors:
        print("\n错误的测试:")
        for test, trace in result.errors:
            print(f"  - {test}: {trace.split(chr(10))[0]}")

    # 计算通过率
    success_rate = (result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100

    print(f"\n通过率: {success_rate:.1f}%")

    if success_rate == 100:
        print("\n✅ 所有测试通过！系统运行正常。")
    else:
        print(f"\n⚠️ 有 {len(result.failures) + len(result.errors)} 个测试失败，请检查。")

    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
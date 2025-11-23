#!/usr/bin/env python3
"""
智能进化系统集成测试
测试学习系统、图谱生成、协同控制的完整功能
"""

import os
import sys
import json
import time
from datetime import datetime
import asyncio

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.mcp_core.services.learning_system import get_learning_system, CodingSession
from src.mcp_core.services.graph_generator import get_graph_generator
from src.mcp_core.services.collaboration_controller import (
    get_collaboration_controller,
    AIAgent,
    Task,
    TaskStatus,
    LockType,
    LockLevel
)

# ============================================
# 测试配置
# ============================================

TEST_PROJECT_PATH = "/Users/mac/Downloads/MCP"
TEST_PROJECT_ID = "test_evolution_project"

# ============================================
# 测试学习系统
# ============================================

def test_learning_system():
    """测试编码学习系统"""
    print("\n" + "=" * 60)
    print("测试编码学习系统")
    print("=" * 60)

    learning_system = get_learning_system()

    # 创建测试会话
    session = CodingSession(
        session_id="test_session_001",
        project_id=TEST_PROJECT_ID,
        context_type="bug_fix",
        problem_description="修复空指针异常",
        solution_description="添加空值检查",
        code_before="""
def process_data(data):
    return data.upper()
        """,
        code_after="""
def process_data(data):
    if data is None:
        return ""
    return data.upper()
        """,
        files_modified=["test.py"],
        time_spent=300,
        lines_changed=3,
        bugs_fixed=1,
        bugs_introduced=0,
        test_coverage_change=0.05
    )

    # 测试学习
    print("\n1. 测试从会话学习...")
    result = learning_system.learn_from_session(session)
    print(f"   ✅ 学习完成:")
    print(f"      - 提取模式: {result.get('patterns_extracted', 0)}")
    print(f"      - 最佳实践: {result.get('best_practices', 0)}")
    print(f"      - 经验ID: {result.get('experience_id', 'N/A')}")

    # 测试推荐
    print("\n2. 测试获取建议...")
    context = {
        "type": "bug_fix",
        "problem": "处理可能的空值输入",
        "files": ["test2.py"]
    }

    suggestions = learning_system.suggest_solution(context, top_k=3)
    print(f"   ✅ 获得 {len(suggestions)} 个建议")
    for i, suggestion in enumerate(suggestions, 1):
        print(f"      建议{i}: 置信度 {suggestion.confidence:.2f}")

    return True

# ============================================
# 测试图谱生成
# ============================================

def test_graph_generator():
    """测试项目图谱生成"""
    print("\n" + "=" * 60)
    print("测试项目图谱生成")
    print("=" * 60)

    graph_generator = get_graph_generator()

    print("\n1. 生成项目图谱...")
    start_time = time.time()

    try:
        # 使用测试目录的子目录以减少处理时间
        test_path = os.path.join(TEST_PROJECT_PATH, "src/mcp_core/services")
        graph, visualization = graph_generator.generate_graph(
            test_path,
            TEST_PROJECT_ID
        )

        elapsed = time.time() - start_time
        print(f"   ✅ 图谱生成完成 (耗时: {elapsed:.2f}秒)")
        print(f"      - 节点数: {len(graph.nodes)}")
        print(f"      - 边数: {len(graph.edges)}")
        print(f"      - 聚类数: {len(graph.clusters)}")
        print(f"      - 层级数: {len(graph.layers)}")

        # 显示统计信息
        if graph.statistics:
            print(f"\n2. 统计信息:")
            print(f"      - 平均复杂度: {graph.statistics.get('avg_complexity', 0):.2f}")
            print(f"      - 平均重要性: {graph.statistics.get('avg_importance', 0):.2f}")
            print(f"      - 最大入度: {graph.statistics.get('max_in_degree', 0)}")
            print(f"      - 最大出度: {graph.statistics.get('max_out_degree', 0)}")

        # 显示节点类型分布
        if graph.statistics.get('node_types'):
            print(f"\n3. 节点类型分布:")
            for node_type, count in graph.statistics['node_types'].items():
                print(f"      - {node_type}: {count}")

        return True

    except Exception as e:
        print(f"   ❌ 图谱生成失败: {e}")
        return False

# ============================================
# 测试协同控制
# ============================================

def test_collaboration_controller():
    """测试多AI协同控制"""
    print("\n" + "=" * 60)
    print("测试多AI协同控制")
    print("=" * 60)

    controller = get_collaboration_controller()

    # 创建测试代理
    print("\n1. 创建AI代理...")
    agents = [
        AIAgent(
            agent_id="agent_001",
            name="Python专家",
            capabilities=["python", "refactor", "optimization"]
        ),
        AIAgent(
            agent_id="agent_002",
            name="测试专家",
            capabilities=["testing", "validation", "coverage"]
        ),
        AIAgent(
            agent_id="agent_003",
            name="文档专家",
            capabilities=["documentation", "api", "comments"]
        )
    ]

    for agent in agents:
        controller.agents[agent.agent_id] = agent
        print(f"   ✅ 创建代理: {agent.name}")

    # 创建测试任务
    print("\n2. 创建测试任务...")
    task = Task(
        task_id="task_001",
        task_type="refactor",
        description="重构代码并添加测试",
        files=[
            "src/module1.py",
            "src/module2.py",
            "tests/test_module1.py"
        ],
        priority=1,
        estimated_time=600
    )
    print(f"   ✅ 任务创建: {task.task_id}")

    # 测试任务分配
    print("\n3. 分配任务...")
    assignment_result = controller.assign_task(task, agents)

    if assignment_result["success"]:
        print(f"   ✅ 任务分配成功:")
        print(f"      - 并行组: {assignment_result.get('parallel_groups', 0)}")
        print(f"      - 子任务: {assignment_result.get('total_subtasks', 0)}")

        for agent_id, assignment in assignment_result.get("assignments", {}).items():
            agent = controller.agents[agent_id]
            print(f"      - {agent.name}: 任务 {assignment['task'].task_id}")
    else:
        print(f"   ❌ 任务分配失败")

    # 测试锁机制
    print("\n4. 测试锁机制...")

    # Agent 1请求锁
    lock1 = controller.request_lock(
        agent_id="agent_001",
        lock_type=LockType.FILE,
        resource_id="src/module1.py",
        resource_path="src/module1.py",
        intent="重构代码"
    )

    if lock1:
        print(f"   ✅ Agent 1获得锁: {lock1.lock_id}")
        print(f"      状态: {lock1.status.value}")

    # Agent 2请求同一资源的锁（应该等待）
    lock2 = controller.request_lock(
        agent_id="agent_002",
        lock_type=LockType.FILE,
        resource_id="src/module1.py",
        resource_path="src/module1.py",
        intent="添加测试"
    )

    if lock2:
        print(f"   ✅ Agent 2请求锁: {lock2.lock_id}")
        print(f"      状态: {lock2.status.value}")

    # 释放锁
    if lock1:
        success = controller.release_lock(lock1.lock_id)
        if success:
            print(f"   ✅ 锁已释放: {lock1.lock_id}")

    # 测试冲突检测
    print("\n5. 测试冲突检测...")
    changes1 = {
        "agent_id": "agent_001",
        "files": ["src/module1.py"],
        "description": "重构函数"
    }

    result = controller.prevent_conflicts("agent_001", changes1)
    print(f"   ✅ 冲突检测完成:")
    print(f"      - 状态: {result['status']}")
    print(f"      - 冲突数: {len(result.get('conflicts', []))}")

    return True

# ============================================
# 端到端测试
# ============================================

async def test_end_to_end():
    """端到端集成测试"""
    print("\n" + "=" * 60)
    print("端到端集成测试")
    print("=" * 60)

    # 模拟完整工作流
    print("\n1. 初始化系统...")
    learning_system = get_learning_system()
    graph_generator = get_graph_generator()
    controller = get_collaboration_controller()
    print("   ✅ 系统初始化完成")

    # 模拟编码会话
    print("\n2. 模拟编码会话...")
    sessions = [
        CodingSession(
            session_id=f"e2e_session_{i}",
            project_id=TEST_PROJECT_ID,
            context_type="feature" if i % 2 == 0 else "bug_fix",
            problem_description=f"问题 {i}",
            solution_description=f"解决方案 {i}",
            code_before=f"# 原始代码 {i}",
            code_after=f"# 修改后代码 {i}",
            files_modified=[f"file_{i}.py"],
            time_spent=300 + i * 100,
            lines_changed=10 + i * 5,
            bugs_fixed=i % 3,
            bugs_introduced=0
        )
        for i in range(3)
    ]

    for session in sessions:
        result = learning_system.learn_from_session(session)
        print(f"   ✅ 会话 {session.session_id} 学习完成")

    # 生成项目见解
    print("\n3. 生成项目见解...")
    context = {
        "type": "feature",
        "problem": "需要添加新功能",
        "files": ["new_feature.py"]
    }

    suggestions = learning_system.suggest_solution(context, top_k=2)
    print(f"   ✅ 获得 {len(suggestions)} 个智能建议")

    # 协同开发模拟
    print("\n4. 模拟协同开发...")
    agents = [
        AIAgent(f"e2e_agent_{i}", f"Agent_{i}", ["coding"])
        for i in range(2)
    ]

    for agent in agents:
        controller.agents[agent.agent_id] = agent

    task = Task(
        task_id="e2e_task",
        task_type="coding",
        description="协同开发任务",
        files=["shared_file.py"],
        estimated_time=300
    )

    assignment = controller.assign_task(task, agents)
    if assignment["success"]:
        print(f"   ✅ 协同任务分配成功")

    print("\n✅ 端到端测试完成!")
    return True

# ============================================
# 性能测试
# ============================================

def test_performance():
    """性能测试"""
    print("\n" + "=" * 60)
    print("性能测试")
    print("=" * 60)

    import time
    import random

    # 测试学习系统性能
    print("\n1. 学习系统性能测试...")
    learning_system = get_learning_system()

    start_time = time.time()
    for i in range(10):
        session = CodingSession(
            session_id=f"perf_session_{i}",
            project_id=TEST_PROJECT_ID,
            context_type=random.choice(["bug_fix", "feature", "refactor"]),
            problem_description=f"性能测试问题 {i}",
            solution_description=f"性能测试解决方案 {i}",
            code_before=f"# 代码 {i}" * 100,  # 较长的代码
            code_after=f"# 修改后代码 {i}" * 100,
            files_modified=[f"perf_file_{i}.py"],
            time_spent=random.randint(100, 1000),
            lines_changed=random.randint(10, 100),
            bugs_fixed=random.randint(0, 5),
            bugs_introduced=0
        )
        learning_system.learn_from_session(session)

    elapsed = time.time() - start_time
    print(f"   ✅ 处理10个会话耗时: {elapsed:.2f}秒")
    print(f"      平均每会话: {elapsed/10:.2f}秒")

    # 测试锁性能
    print("\n2. 锁机制性能测试...")
    controller = get_collaboration_controller()

    start_time = time.time()
    locks = []
    for i in range(100):
        lock = controller.request_lock(
            agent_id=f"perf_agent_{i % 5}",
            lock_type=LockType.FILE,
            resource_id=f"file_{i % 20}.py",
            resource_path=f"file_{i % 20}.py",
            intent=f"操作 {i}"
        )
        if lock:
            locks.append(lock)

    elapsed = time.time() - start_time
    print(f"   ✅ 请求100个锁耗时: {elapsed:.2f}秒")
    print(f"      成功获取: {len(locks)}个")

    # 释放锁
    for lock in locks:
        controller.release_lock(lock.lock_id)

    return True

# ============================================
# 主测试函数
# ============================================

def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("智能进化系统集成测试")
    print("=" * 60)
    print(f"测试时间: {datetime.now()}")
    print(f"项目路径: {TEST_PROJECT_PATH}")

    # 运行测试
    tests = [
        ("学习系统", test_learning_system),
        ("图谱生成", test_graph_generator),
        ("协同控制", test_collaboration_controller),
        ("性能测试", test_performance)
    ]

    results = []
    for test_name, test_func in tests:
        try:
            print(f"\n开始测试: {test_name}")
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"\n❌ 测试失败: {test_name}")
            print(f"   错误: {e}")
            results.append((test_name, False))

    # 运行异步测试
    try:
        print(f"\n开始测试: 端到端集成")
        asyncio.run(test_end_to_end())
        results.append(("端到端集成", True))
    except Exception as e:
        print(f"\n❌ 测试失败: 端到端集成")
        print(f"   错误: {e}")
        results.append(("端到端集成", False))

    # 输出测试结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    success_count = 0
    for test_name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{test_name:20} {status}")
        if success:
            success_count += 1

    print("-" * 60)
    print(f"通过率: {success_count}/{len(results)} ({success_count/len(results)*100:.1f}%)")

    if success_count == len(results):
        print("\n🎉 所有测试通过！智能进化系统已就绪！")
    else:
        print(f"\n⚠️  有 {len(results) - success_count} 个测试失败，请检查。")

    return success_count == len(results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
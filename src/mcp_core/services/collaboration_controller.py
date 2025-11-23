"""
多AI协同控制器 - 实现多个AI无冲突并行开发
智能任务分配、锁管理、冲突检测与解决
"""

import os
import json
import hashlib
import asyncio
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass, asdict, field
from enum import Enum
import numpy as np
from sqlalchemy import create_engine, select, and_, or_, desc, func
from sqlalchemy.orm import Session, sessionmaker

from ..models.base import Base
from ..common.config import get_settings
from ..common.logger import get_logger
from ..services.redis_client import get_redis_client

logger = get_logger(__name__)

# ============================================
# 枚举类型
# ============================================

class LockType(Enum):
    """锁类型"""
    FILE = "file"          # 文件级锁
    FUNCTION = "function"  # 函数级锁
    CLASS = "class"       # 类级锁
    REGION = "region"     # 区域锁
    SEMANTIC = "semantic" # 语义锁

class LockLevel(Enum):
    """锁级别"""
    READ = "read"         # 读锁
    WRITE = "write"       # 写锁
    EXCLUSIVE = "exclusive"  # 排他锁

class LockStatus(Enum):
    """锁状态"""
    WAITING = "waiting"     # 等待中
    ACQUIRED = "acquired"   # 已获取
    RELEASING = "releasing" # 释放中
    RELEASED = "released"   # 已释放

class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"       # 待处理
    ASSIGNED = "assigned"     # 已分配
    IN_PROGRESS = "in_progress"  # 进行中
    COMPLETED = "completed"   # 已完成
    FAILED = "failed"        # 失败
    BLOCKED = "blocked"      # 阻塞

class ConflictStrategy(Enum):
    """冲突策略"""
    WAIT = "wait"           # 等待
    MERGE = "merge"         # 合并
    ABORT = "abort"         # 中止
    NEGOTIATE = "negotiate" # 协商

# ============================================
# 数据模型
# ============================================

@dataclass
class AIAgent:
    """AI代理"""
    agent_id: str
    name: str
    capabilities: List[str]
    current_task: Optional[str] = None
    status: str = "idle"
    performance_score: float = 1.0
    lock_count: int = 0

@dataclass
class Task:
    """任务"""
    task_id: str
    task_type: str
    description: str
    files: List[str]
    dependencies: List[str] = field(default_factory=list)
    priority: int = 0
    estimated_time: int = 0  # 秒
    status: TaskStatus = TaskStatus.PENDING
    assigned_agent: Optional[str] = None
    required_locks: List[str] = field(default_factory=list)

@dataclass
class Lock:
    """锁"""
    lock_id: str
    agent_id: str
    lock_type: LockType
    lock_level: LockLevel
    resource_id: str
    resource_path: str
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    status: LockStatus = LockStatus.WAITING
    priority: int = 0
    intent: str = ""
    requested_at: datetime = field(default_factory=datetime.now)
    acquired_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

@dataclass
class Conflict:
    """冲突"""
    conflict_id: str
    agent1_id: str
    agent2_id: str
    resource_id: str
    conflict_type: str
    description: str
    suggested_resolution: str
    strategy: ConflictStrategy = ConflictStrategy.WAIT

@dataclass
class CollaborationSession:
    """协作会话"""
    session_id: str
    project_id: str
    agents: List[AIAgent]
    tasks: List[Task]
    goal: str
    status: str = "planning"
    start_time: datetime = field(default_factory=datetime.now)

# ============================================
# 多AI协同控制器
# ============================================

class MultiAICollaborationController:
    """多AI协同控制器 - 无冲突并行开发"""

    def __init__(self):
        """初始化协同控制器"""
        settings = get_settings()
        self.db_engine = create_engine(settings.database.url)
        self.SessionLocal = sessionmaker(bind=self.db_engine)

        # Redis客户端
        self.redis_client = get_redis_client()

        # 锁管理
        self.locks: Dict[str, Lock] = {}
        self.lock_mutex = threading.Lock()

        # 任务队列
        self.task_queue: List[Task] = []
        self.task_assignments: Dict[str, str] = {}  # task_id -> agent_id

        # 活跃代理
        self.agents: Dict[str, AIAgent] = {}

        # 会话管理
        self.current_session: Optional[CollaborationSession] = None

        # 配置参数
        self.max_wait_time = 60  # 最大等待时间(秒)
        self.lock_expiry_time = 300  # 锁过期时间(秒)
        self.conflict_threshold = 0.8  # 冲突阈值

        logger.info("多AI协同控制器初始化完成")

    # ============================================
    # 任务分配
    # ============================================

    def assign_task(
        self,
        task: Task,
        available_agents: List[AIAgent]
    ) -> Dict[str, Any]:
        """
        智能任务分配

        Args:
            task: 任务
            available_agents: 可用代理列表

        Returns:
            分配结果
        """
        try:
            logger.info(f"开始分配任务: {task.task_id}")

            # 1. 分解任务
            subtasks = self.decompose_task(task)
            logger.info(f"任务分解为 {len(subtasks)} 个子任务")

            # 2. 分析依赖关系
            dependency_graph = self.analyze_dependencies(subtasks)

            # 3. 识别可并行组
            parallel_groups = self.identify_parallel_groups(subtasks, dependency_graph)
            logger.info(f"识别到 {len(parallel_groups)} 个并行组")

            # 4. 分配任务给代理
            assignments = {}
            for group_idx, group in enumerate(parallel_groups):
                logger.info(f"处理并行组 {group_idx + 1}")

                for subtask in group:
                    # 选择最佳代理
                    agent = self.select_best_agent(subtask, available_agents)

                    if agent:
                        # 获取所需锁
                        locks = self.acquire_locks_for_task(subtask, agent)

                        # 记录分配
                        assignments[agent.agent_id] = {
                            "task": subtask,
                            "locks": locks,
                            "dependencies": dependency_graph.get(subtask.task_id, []),
                            "estimated_start": self.estimate_start_time(subtask, group_idx)
                        }

                        # 更新代理状态
                        agent.current_task = subtask.task_id
                        agent.status = "assigned"

                        # 更新任务状态
                        subtask.status = TaskStatus.ASSIGNED
                        subtask.assigned_agent = agent.agent_id

                        logger.info(f"任务 {subtask.task_id} 分配给 {agent.name}")
                    else:
                        logger.warning(f"无法为任务 {subtask.task_id} 找到合适的代理")

            # 5. 存储分配结果
            self.store_assignments(assignments)

            return {
                "success": True,
                "assignments": assignments,
                "parallel_groups": len(parallel_groups),
                "total_subtasks": len(subtasks)
            }

        except Exception as e:
            logger.error(f"任务分配失败: {e}")
            return {"success": False, "error": str(e)}

    def decompose_task(self, task: Task) -> List[Task]:
        """分解任务"""
        subtasks = []

        # 基于文件分解
        if len(task.files) > 1:
            for file in task.files:
                subtask = Task(
                    task_id=f"{task.task_id}_file_{os.path.basename(file)}",
                    task_type=task.task_type,
                    description=f"{task.description} - {file}",
                    files=[file],
                    priority=task.priority,
                    estimated_time=task.estimated_time // len(task.files)
                )
                subtasks.append(subtask)
        else:
            # 如果只有一个文件，尝试基于功能分解
            subtasks = self.decompose_by_functionality(task)

        if not subtasks:
            # 无法分解，返回原任务
            subtasks = [task]

        return subtasks

    def decompose_by_functionality(self, task: Task) -> List[Task]:
        """基于功能分解任务"""
        subtasks = []

        # 分析任务描述，识别功能点
        functionalities = self.extract_functionalities(task.description)

        for idx, func in enumerate(functionalities):
            subtask = Task(
                task_id=f"{task.task_id}_func_{idx}",
                task_type=task.task_type,
                description=func,
                files=task.files,
                priority=task.priority,
                estimated_time=task.estimated_time // len(functionalities)
            )
            subtasks.append(subtask)

        return subtasks

    def analyze_dependencies(self, tasks: List[Task]) -> Dict[str, List[str]]:
        """分析任务依赖关系"""
        dependencies = {}

        for task in tasks:
            task_deps = []

            # 分析文件依赖
            for other_task in tasks:
                if other_task.task_id == task.task_id:
                    continue

                # 检查文件依赖
                if self.has_file_dependency(task, other_task):
                    task_deps.append(other_task.task_id)

                # 检查逻辑依赖
                if self.has_logical_dependency(task, other_task):
                    task_deps.append(other_task.task_id)

            dependencies[task.task_id] = task_deps

        return dependencies

    def identify_parallel_groups(
        self,
        tasks: List[Task],
        dependencies: Dict[str, List[str]]
    ) -> List[List[Task]]:
        """识别可并行任务组"""
        # 拓扑排序
        sorted_tasks = self.topological_sort(tasks, dependencies)

        # 分组
        groups = []
        current_group = []
        processed = set()

        for task in sorted_tasks:
            # 检查是否可以并行
            can_parallel = True
            for dep in dependencies.get(task.task_id, []):
                if dep not in processed:
                    can_parallel = False
                    break

            if can_parallel and current_group and not self.has_resource_conflict(task, current_group):
                current_group.append(task)
            else:
                if current_group:
                    groups.append(current_group)
                    for t in current_group:
                        processed.add(t.task_id)
                current_group = [task]

        if current_group:
            groups.append(current_group)

        return groups

    def select_best_agent(
        self,
        task: Task,
        available_agents: List[AIAgent]
    ) -> Optional[AIAgent]:
        """选择最佳代理"""
        best_agent = None
        best_score = 0

        for agent in available_agents:
            # 检查代理是否可用
            if agent.status not in ["idle", "ready"]:
                continue

            # 计算匹配分数
            score = self.calculate_agent_task_score(agent, task)

            if score > best_score:
                best_score = score
                best_agent = agent

        return best_agent

    def calculate_agent_task_score(self, agent: AIAgent, task: Task) -> float:
        """计算代理-任务匹配分数"""
        score = 0.0

        # 能力匹配
        task_keywords = self.extract_keywords(task.description)
        for capability in agent.capabilities:
            if any(kw in capability.lower() for kw in task_keywords):
                score += 0.3

        # 性能分数
        score += agent.performance_score * 0.3

        # 负载均衡
        load_factor = 1.0 / (1.0 + agent.lock_count)
        score += load_factor * 0.2

        # 任务类型匹配
        if task.task_type in agent.capabilities:
            score += 0.2

        return min(score, 1.0)

    # ============================================
    # 锁管理
    # ============================================

    def acquire_locks_for_task(
        self,
        task: Task,
        agent: AIAgent
    ) -> List[Lock]:
        """为任务获取锁"""
        locks = []

        for file in task.files:
            # 尝试获取文件锁
            lock = self.request_lock(
                agent_id=agent.agent_id,
                lock_type=LockType.FILE,
                resource_id=file,
                resource_path=file,
                intent=task.description
            )

            if lock:
                locks.append(lock)
                task.required_locks.append(lock.lock_id)

        return locks

    def request_lock(
        self,
        agent_id: str,
        lock_type: LockType,
        resource_id: str,
        resource_path: str,
        lock_level: LockLevel = LockLevel.WRITE,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
        intent: str = "",
        priority: int = 0
    ) -> Optional[Lock]:
        """
        请求锁

        Args:
            agent_id: 代理ID
            lock_type: 锁类型
            resource_id: 资源ID
            resource_path: 资源路径
            lock_level: 锁级别
            start_line: 起始行
            end_line: 结束行
            intent: 操作意图
            priority: 优先级

        Returns:
            锁对象或None
        """
        with self.lock_mutex:
            try:
                # 生成锁ID
                lock_id = self.generate_lock_id(agent_id, resource_id, lock_type.value)

                # 检查冲突
                conflicts = self.check_lock_conflicts(
                    resource_id,
                    lock_type,
                    lock_level,
                    start_line,
                    end_line
                )

                if conflicts:
                    # 处理冲突
                    resolution = self.handle_lock_conflicts(
                        agent_id,
                        conflicts,
                        priority
                    )

                    if resolution["action"] == "wait":
                        # 加入等待队列
                        lock = self.create_waiting_lock(
                            lock_id,
                            agent_id,
                            lock_type,
                            lock_level,
                            resource_id,
                            resource_path,
                            start_line,
                            end_line,
                            intent,
                            priority
                        )
                    elif resolution["action"] == "abort":
                        return None
                    else:
                        # 协商成功，获取锁
                        lock = self.create_acquired_lock(
                            lock_id,
                            agent_id,
                            lock_type,
                            lock_level,
                            resource_id,
                            resource_path,
                            start_line,
                            end_line,
                            intent,
                            priority
                        )
                else:
                    # 无冲突，直接获取锁
                    lock = self.create_acquired_lock(
                        lock_id,
                        agent_id,
                        lock_type,
                        lock_level,
                        resource_id,
                        resource_path,
                        start_line,
                        end_line,
                        intent,
                        priority
                    )

                # 存储锁
                self.locks[lock_id] = lock
                self.store_lock(lock)

                # 更新代理锁计数
                if agent_id in self.agents:
                    self.agents[agent_id].lock_count += 1

                logger.info(f"锁请求: {lock_id} - {lock.status.value}")

                return lock

            except Exception as e:
                logger.error(f"请求锁失败: {e}")
                return None

    def check_lock_conflicts(
        self,
        resource_id: str,
        lock_type: LockType,
        lock_level: LockLevel,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None
    ) -> List[Lock]:
        """检查锁冲突"""
        conflicts = []

        for lock_id, lock in self.locks.items():
            if lock.status not in [LockStatus.ACQUIRED, LockStatus.WAITING]:
                continue

            # 检查资源冲突
            if lock.resource_id == resource_id:
                # 检查锁级别兼容性
                if not self.are_locks_compatible(lock_level, lock.lock_level):
                    # 检查区域重叠(如果是区域锁)
                    if lock_type == LockType.REGION and start_line and end_line:
                        if self.regions_overlap(
                            start_line, end_line,
                            lock.start_line, lock.end_line
                        ):
                            conflicts.append(lock)
                    else:
                        conflicts.append(lock)

        return conflicts

    def are_locks_compatible(self, level1: LockLevel, level2: LockLevel) -> bool:
        """检查锁级别兼容性"""
        # 读锁之间兼容
        if level1 == LockLevel.READ and level2 == LockLevel.READ:
            return True

        # 写锁和排他锁不兼容
        return False

    def regions_overlap(
        self,
        start1: int,
        end1: int,
        start2: Optional[int],
        end2: Optional[int]
    ) -> bool:
        """检查区域是否重叠"""
        if not start2 or not end2:
            return True  # 如果没有指定区域，认为是全文件锁

        return not (end1 < start2 or start1 > end2)

    def handle_lock_conflicts(
        self,
        agent_id: str,
        conflicts: List[Lock],
        priority: int
    ) -> Dict[str, Any]:
        """处理锁冲突"""
        # 检查优先级
        for conflict_lock in conflicts:
            if priority > conflict_lock.priority:
                # 高优先级，尝试抢占
                if self.can_preempt(conflict_lock):
                    self.preempt_lock(conflict_lock)
                    return {"action": "acquire"}

        # 检查等待时间
        total_wait_time = self.estimate_wait_time(conflicts)
        if total_wait_time > self.max_wait_time:
            # 等待时间过长，中止
            return {"action": "abort", "reason": "wait_time_exceeded"}

        # 默认等待
        return {"action": "wait", "estimated_wait": total_wait_time}

    def release_lock(self, lock_id: str) -> bool:
        """
        释放锁

        Args:
            lock_id: 锁ID

        Returns:
            是否成功
        """
        with self.lock_mutex:
            try:
                if lock_id not in self.locks:
                    logger.warning(f"锁不存在: {lock_id}")
                    return False

                lock = self.locks[lock_id]

                # 更新锁状态
                lock.status = LockStatus.RELEASED

                # 从内存中移除
                del self.locks[lock_id]

                # 更新数据库
                self.update_lock_status(lock_id, LockStatus.RELEASED)

                # 更新代理锁计数
                if lock.agent_id in self.agents:
                    self.agents[lock.agent_id].lock_count -= 1

                # 通知等待者
                self.notify_waiters(lock.resource_id)

                logger.info(f"锁释放: {lock_id}")

                return True

            except Exception as e:
                logger.error(f"释放锁失败: {e}")
                return False

    def release_expired_locks(self) -> int:
        """释放过期锁"""
        expired_count = 0
        current_time = datetime.now()

        with self.lock_mutex:
            expired_locks = []
            for lock_id, lock in self.locks.items():
                if lock.expires_at and lock.expires_at < current_time:
                    expired_locks.append(lock_id)

            for lock_id in expired_locks:
                if self.release_lock(lock_id):
                    expired_count += 1

        if expired_count > 0:
            logger.info(f"释放 {expired_count} 个过期锁")

        return expired_count

    # ============================================
    # 冲突检测与解决
    # ============================================

    def prevent_conflicts(
        self,
        agent_id: str,
        intended_changes: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        预防冲突

        Args:
            agent_id: 代理ID
            intended_changes: 计划的更改

        Returns:
            预防结果
        """
        try:
            # 1. 检查文件锁冲突
            file_conflicts = self.check_file_conflicts(intended_changes)

            # 2. 检查语义冲突
            semantic_conflicts = self.check_semantic_conflicts(intended_changes)

            # 3. 合并冲突列表
            all_conflicts = file_conflicts + semantic_conflicts

            if all_conflicts:
                # 4. 协商解决
                resolution = self.negotiate_resolution(agent_id, all_conflicts)
                return resolution

            # 5. 无冲突，获取必要的锁
            locks = self.acquire_locks_for_changes(agent_id, intended_changes)

            return {
                "status": "clear",
                "locks": locks,
                "conflicts": []
            }

        except Exception as e:
            logger.error(f"冲突预防失败: {e}")
            return {"status": "error", "error": str(e)}

    def check_file_conflicts(self, changes: Dict[str, Any]) -> List[Conflict]:
        """检查文件级冲突"""
        conflicts = []

        for file_path in changes.get("files", []):
            # 检查文件是否被锁定
            for lock_id, lock in self.locks.items():
                if lock.resource_path == file_path and lock.status == LockStatus.ACQUIRED:
                    conflict = Conflict(
                        conflict_id=self.generate_conflict_id(file_path),
                        agent1_id=changes.get("agent_id"),
                        agent2_id=lock.agent_id,
                        resource_id=file_path,
                        conflict_type="file_lock",
                        description=f"文件 {file_path} 被 {lock.agent_id} 锁定",
                        suggested_resolution="等待锁释放或协商"
                    )
                    conflicts.append(conflict)

        return conflicts

    def check_semantic_conflicts(self, changes: Dict[str, Any]) -> List[Conflict]:
        """检查语义级冲突"""
        conflicts = []

        # 分析更改的语义影响
        semantic_impact = self.analyze_semantic_impact(changes)

        # 检查与其他代理的工作是否有语义冲突
        for agent_id, agent in self.agents.items():
            if agent_id == changes.get("agent_id"):
                continue

            if agent.current_task:
                # 获取代理任务的语义信息
                task_semantics = self.get_task_semantics(agent.current_task)

                # 计算语义相似度
                similarity = self.calculate_semantic_similarity(
                    semantic_impact,
                    task_semantics
                )

                if similarity > self.conflict_threshold:
                    conflict = Conflict(
                        conflict_id=self.generate_conflict_id(f"semantic_{agent_id}"),
                        agent1_id=changes.get("agent_id"),
                        agent2_id=agent_id,
                        resource_id="semantic",
                        conflict_type="semantic",
                        description=f"语义冲突: 相似度 {similarity:.2f}",
                        suggested_resolution="协调任务范围"
                    )
                    conflicts.append(conflict)

        return conflicts

    def negotiate_resolution(
        self,
        agent_id: str,
        conflicts: List[Conflict]
    ) -> Dict[str, Any]:
        """协商冲突解决"""
        resolutions = []

        for conflict in conflicts:
            if conflict.strategy == ConflictStrategy.WAIT:
                # 等待策略
                wait_time = self.estimate_conflict_resolution_time(conflict)
                resolutions.append({
                    "conflict_id": conflict.conflict_id,
                    "action": "wait",
                    "wait_time": wait_time
                })

            elif conflict.strategy == ConflictStrategy.MERGE:
                # 合并策略
                merge_plan = self.create_merge_plan(conflict)
                resolutions.append({
                    "conflict_id": conflict.conflict_id,
                    "action": "merge",
                    "merge_plan": merge_plan
                })

            elif conflict.strategy == ConflictStrategy.NEGOTIATE:
                # 协商策略
                negotiation_result = self.negotiate_with_agent(
                    agent_id,
                    conflict.agent2_id,
                    conflict
                )
                resolutions.append({
                    "conflict_id": conflict.conflict_id,
                    "action": "negotiate",
                    "result": negotiation_result
                })

            else:
                # 中止策略
                resolutions.append({
                    "conflict_id": conflict.conflict_id,
                    "action": "abort",
                    "reason": conflict.description
                })

        return {
            "status": "conflicts_found",
            "conflicts": conflicts,
            "resolutions": resolutions
        }

    def auto_merge_changes(
        self,
        changes1: Dict[str, Any],
        changes2: Dict[str, Any]
    ) -> Dict[str, Any]:
        """自动合并更改"""
        merged = {
            "files": list(set(changes1.get("files", []) + changes2.get("files", []))),
            "modifications": []
        }

        # 合并修改
        for mod1 in changes1.get("modifications", []):
            conflict = False
            for mod2 in changes2.get("modifications", []):
                if self.modifications_conflict(mod1, mod2):
                    conflict = True
                    # 尝试智能合并
                    merged_mod = self.smart_merge_modifications(mod1, mod2)
                    if merged_mod:
                        merged["modifications"].append(merged_mod)
                    break

            if not conflict:
                merged["modifications"].append(mod1)

        # 添加不冲突的修改
        for mod2 in changes2.get("modifications", []):
            if not any(self.modifications_conflict(mod2, m) for m in merged["modifications"]):
                merged["modifications"].append(mod2)

        return merged

    # ============================================
    # 通信与协调
    # ============================================

    async def broadcast_intent(self, agent_id: str, intent: Dict[str, Any]) -> None:
        """
        广播意图

        Args:
            agent_id: 代理ID
            intent: 意图信息
        """
        message = {
            "type": "intent_broadcast",
            "agent_id": agent_id,
            "intent": intent,
            "timestamp": datetime.now().isoformat()
        }

        # 发布到Redis
        await self.redis_client.publish(
            "collaboration:intents",
            json.dumps(message)
        )

        logger.info(f"意图广播: {agent_id} - {intent.get('action')}")

    async def synchronize_progress(self) -> Dict[str, Any]:
        """同步进度"""
        progress = {
            "agents": {},
            "tasks": {},
            "locks": {}
        }

        # 收集代理进度
        for agent_id, agent in self.agents.items():
            progress["agents"][agent_id] = {
                "status": agent.status,
                "current_task": agent.current_task,
                "lock_count": agent.lock_count
            }

        # 收集任务进度
        for task in self.task_queue:
            progress["tasks"][task.task_id] = {
                "status": task.status.value,
                "assigned_to": task.assigned_agent,
                "progress": self.get_task_progress(task)
            }

        # 收集锁状态
        for lock_id, lock in self.locks.items():
            progress["locks"][lock_id] = {
                "status": lock.status.value,
                "agent": lock.agent_id,
                "resource": lock.resource_id
            }

        return progress

    def coordinate_agents(self, agents: List[AIAgent]) -> Dict[str, Any]:
        """
        协调多个代理

        Args:
            agents: 代理列表

        Returns:
            协调结果
        """
        coordination = {
            "task_distribution": {},
            "resource_allocation": {},
            "timeline": []
        }

        # 1. 任务分配优化
        task_distribution = self.optimize_task_distribution(agents)
        coordination["task_distribution"] = task_distribution

        # 2. 资源分配
        resource_allocation = self.allocate_resources(agents)
        coordination["resource_allocation"] = resource_allocation

        # 3. 时间线规划
        timeline = self.create_timeline(agents, task_distribution)
        coordination["timeline"] = timeline

        return coordination

    # ============================================
    # 辅助功能
    # ============================================

    def generate_lock_id(self, agent_id: str, resource_id: str, lock_type: str) -> str:
        """生成锁ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        content = f"{agent_id}_{resource_id}_{lock_type}_{timestamp}"
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def generate_conflict_id(self, content: str) -> str:
        """生成冲突ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"conflict_{hashlib.md5(content.encode()).hexdigest()[:8]}_{timestamp}"

    def create_waiting_lock(
        self,
        lock_id: str,
        agent_id: str,
        lock_type: LockType,
        lock_level: LockLevel,
        resource_id: str,
        resource_path: str,
        start_line: Optional[int],
        end_line: Optional[int],
        intent: str,
        priority: int
    ) -> Lock:
        """创建等待状态的锁"""
        return Lock(
            lock_id=lock_id,
            agent_id=agent_id,
            lock_type=lock_type,
            lock_level=lock_level,
            resource_id=resource_id,
            resource_path=resource_path,
            start_line=start_line,
            end_line=end_line,
            status=LockStatus.WAITING,
            priority=priority,
            intent=intent
        )

    def create_acquired_lock(
        self,
        lock_id: str,
        agent_id: str,
        lock_type: LockType,
        lock_level: LockLevel,
        resource_id: str,
        resource_path: str,
        start_line: Optional[int],
        end_line: Optional[int],
        intent: str,
        priority: int
    ) -> Lock:
        """创建已获取状态的锁"""
        now = datetime.now()
        return Lock(
            lock_id=lock_id,
            agent_id=agent_id,
            lock_type=lock_type,
            lock_level=lock_level,
            resource_id=resource_id,
            resource_path=resource_path,
            start_line=start_line,
            end_line=end_line,
            status=LockStatus.ACQUIRED,
            priority=priority,
            intent=intent,
            acquired_at=now,
            expires_at=now + timedelta(seconds=self.lock_expiry_time)
        )

    def store_lock(self, lock: Lock) -> None:
        """存储锁到数据库"""
        with self.SessionLocal() as session:
            session.execute(
                """
                INSERT INTO collaboration_locks (
                    lock_id, agent_id, project_id,
                    lock_type, lock_level, resource_id, resource_path,
                    start_line, end_line,
                    status, priority,
                    intent_description, operation_type,
                    requested_at, acquired_at, expires_at
                ) VALUES (
                    :lock_id, :agent_id, :project_id,
                    :lock_type, :lock_level, :resource_id, :resource_path,
                    :start_line, :end_line,
                    :status, :priority,
                    :intent, :operation,
                    :requested_at, :acquired_at, :expires_at
                )
                """,
                {
                    "lock_id": lock.lock_id,
                    "agent_id": lock.agent_id,
                    "project_id": self.current_session.project_id if self.current_session else "default",
                    "lock_type": lock.lock_type.value,
                    "lock_level": lock.lock_level.value,
                    "resource_id": lock.resource_id,
                    "resource_path": lock.resource_path,
                    "start_line": lock.start_line,
                    "end_line": lock.end_line,
                    "status": lock.status.value,
                    "priority": lock.priority,
                    "intent": lock.intent,
                    "operation": "modify",
                    "requested_at": lock.requested_at,
                    "acquired_at": lock.acquired_at,
                    "expires_at": lock.expires_at
                }
            )
            session.commit()

    def update_lock_status(self, lock_id: str, status: LockStatus) -> None:
        """更新锁状态"""
        with self.SessionLocal() as session:
            session.execute(
                """
                UPDATE collaboration_locks
                SET status = :status,
                    released_at = CASE WHEN :status = 'released' THEN NOW() ELSE NULL END
                WHERE lock_id = :lock_id
                """,
                {
                    "lock_id": lock_id,
                    "status": status.value
                }
            )
            session.commit()

    def store_assignments(self, assignments: Dict[str, Any]) -> None:
        """存储任务分配"""
        # 存储到Redis以便快速访问
        for agent_id, assignment in assignments.items():
            key = f"assignment:{agent_id}"
            self.redis_client.set(
                key,
                json.dumps({
                    "task_id": assignment["task"].task_id,
                    "locks": [lock.lock_id for lock in assignment["locks"]],
                    "dependencies": assignment["dependencies"],
                    "timestamp": datetime.now().isoformat()
                }),
                ex=3600  # 1小时过期
            )

    def notify_waiters(self, resource_id: str) -> None:
        """通知等待者"""
        # 查找等待该资源的锁
        waiting_locks = [
            lock for lock in self.locks.values()
            if lock.resource_id == resource_id and lock.status == LockStatus.WAITING
        ]

        # 按优先级排序
        waiting_locks.sort(key=lambda x: (-x.priority, x.requested_at))

        # 尝试获取锁
        for lock in waiting_locks:
            if not self.check_lock_conflicts(
                lock.resource_id,
                lock.lock_type,
                lock.lock_level,
                lock.start_line,
                lock.end_line
            ):
                # 无冲突，获取锁
                lock.status = LockStatus.ACQUIRED
                lock.acquired_at = datetime.now()
                lock.expires_at = lock.acquired_at + timedelta(seconds=self.lock_expiry_time)
                self.update_lock_status(lock.lock_id, LockStatus.ACQUIRED)
                logger.info(f"等待者获取锁: {lock.lock_id}")
                break

    def extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        import re
        words = re.findall(r'\b\w+\b', text.lower())
        stopwords = {'the', 'is', 'at', 'which', 'on', 'and', 'a', 'an', 'to', 'for', 'of', 'in'}
        keywords = [w for w in words if w not in stopwords and len(w) > 2]
        return list(set(keywords))[:10]

    def extract_functionalities(self, description: str) -> List[str]:
        """提取功能点"""
        # 简化实现
        functionalities = []
        sentences = description.split('.')
        for sentence in sentences:
            if sentence.strip():
                functionalities.append(sentence.strip())
        return functionalities[:5]

    def has_file_dependency(self, task1: Task, task2: Task) -> bool:
        """检查文件依赖"""
        # 简化实现：如果任务修改相同文件，则有依赖
        return bool(set(task1.files) & set(task2.files))

    def has_logical_dependency(self, task1: Task, task2: Task) -> bool:
        """检查逻辑依赖"""
        # 简化实现：基于任务描述相似度
        return False  # 需要更复杂的逻辑分析

    def topological_sort(
        self,
        tasks: List[Task],
        dependencies: Dict[str, List[str]]
    ) -> List[Task]:
        """拓扑排序"""
        # 简化实现
        sorted_tasks = []
        visited = set()
        temp_mark = set()

        def visit(task):
            if task.task_id in temp_mark:
                raise ValueError("循环依赖")
            if task.task_id in visited:
                return

            temp_mark.add(task.task_id)

            for dep_id in dependencies.get(task.task_id, []):
                dep_task = next((t for t in tasks if t.task_id == dep_id), None)
                if dep_task:
                    visit(dep_task)

            temp_mark.remove(task.task_id)
            visited.add(task.task_id)
            sorted_tasks.append(task)

        for task in tasks:
            if task.task_id not in visited:
                visit(task)

        return sorted_tasks

    def has_resource_conflict(self, task: Task, group: List[Task]) -> bool:
        """检查资源冲突"""
        task_files = set(task.files)
        for other_task in group:
            if set(other_task.files) & task_files:
                return True
        return False

    def estimate_start_time(self, task: Task, group_idx: int) -> datetime:
        """估算开始时间"""
        # 简化实现
        delay = group_idx * 10  # 每组延迟10秒
        return datetime.now() + timedelta(seconds=delay)

    def can_preempt(self, lock: Lock) -> bool:
        """检查是否可以抢占"""
        # 简化实现：不允许抢占
        return False

    def preempt_lock(self, lock: Lock) -> None:
        """抢占锁"""
        # 实现抢占逻辑
        pass

    def estimate_wait_time(self, locks: List[Lock]) -> int:
        """估算等待时间"""
        # 简化实现
        return len(locks) * 10  # 每个锁预计10秒

    def estimate_conflict_resolution_time(self, conflict: Conflict) -> int:
        """估算冲突解决时间"""
        return 30  # 默认30秒

    def create_merge_plan(self, conflict: Conflict) -> Dict[str, Any]:
        """创建合并计划"""
        return {
            "strategy": "three-way-merge",
            "base": conflict.resource_id,
            "theirs": conflict.agent1_id,
            "ours": conflict.agent2_id
        }

    def negotiate_with_agent(
        self,
        agent1_id: str,
        agent2_id: str,
        conflict: Conflict
    ) -> Dict[str, Any]:
        """与代理协商"""
        return {
            "agreed": True,
            "resolution": "agent1_proceeds",
            "compensation": "agent2_waits"
        }

    def acquire_locks_for_changes(
        self,
        agent_id: str,
        changes: Dict[str, Any]
    ) -> List[Lock]:
        """为更改获取锁"""
        locks = []
        for file in changes.get("files", []):
            lock = self.request_lock(
                agent_id=agent_id,
                lock_type=LockType.FILE,
                resource_id=file,
                resource_path=file,
                intent=changes.get("description", "")
            )
            if lock:
                locks.append(lock)
        return locks

    def analyze_semantic_impact(self, changes: Dict[str, Any]) -> Dict[str, Any]:
        """分析语义影响"""
        return {
            "affected_functions": changes.get("functions", []),
            "affected_classes": changes.get("classes", []),
            "impact_level": "medium"
        }

    def get_task_semantics(self, task_id: str) -> Dict[str, Any]:
        """获取任务语义"""
        task = next((t for t in self.task_queue if t.task_id == task_id), None)
        if task:
            return {
                "description": task.description,
                "files": task.files,
                "type": task.task_type
            }
        return {}

    def calculate_semantic_similarity(
        self,
        semantics1: Dict[str, Any],
        semantics2: Dict[str, Any]
    ) -> float:
        """计算语义相似度"""
        # 简化实现
        if semantics1.get("files") == semantics2.get("files"):
            return 0.9
        return 0.1

    def modifications_conflict(self, mod1: Dict, mod2: Dict) -> bool:
        """检查修改是否冲突"""
        # 简化实现
        return mod1.get("file") == mod2.get("file") and mod1.get("line") == mod2.get("line")

    def smart_merge_modifications(self, mod1: Dict, mod2: Dict) -> Optional[Dict]:
        """智能合并修改"""
        # 简化实现
        return None

    def get_task_progress(self, task: Task) -> float:
        """获取任务进度"""
        if task.status == TaskStatus.COMPLETED:
            return 1.0
        elif task.status == TaskStatus.IN_PROGRESS:
            return 0.5
        elif task.status == TaskStatus.ASSIGNED:
            return 0.1
        return 0.0

    def optimize_task_distribution(self, agents: List[AIAgent]) -> Dict[str, List[str]]:
        """优化任务分配"""
        distribution = {}
        for agent in agents:
            distribution[agent.agent_id] = []
            # 简化实现：平均分配
            for i, task in enumerate(self.task_queue):
                if i % len(agents) == agents.index(agent):
                    distribution[agent.agent_id].append(task.task_id)
        return distribution

    def allocate_resources(self, agents: List[AIAgent]) -> Dict[str, Dict]:
        """分配资源"""
        allocation = {}
        for agent in agents:
            allocation[agent.agent_id] = {
                "cpu": 2,
                "memory": "4GB",
                "priority": 1
            }
        return allocation

    def create_timeline(
        self,
        agents: List[AIAgent],
        task_distribution: Dict[str, List[str]]
    ) -> List[Dict]:
        """创建时间线"""
        timeline = []
        current_time = datetime.now()

        for agent in agents:
            for task_id in task_distribution.get(agent.agent_id, []):
                task = next((t for t in self.task_queue if t.task_id == task_id), None)
                if task:
                    timeline.append({
                        "agent": agent.agent_id,
                        "task": task_id,
                        "start": current_time.isoformat(),
                        "end": (current_time + timedelta(seconds=task.estimated_time)).isoformat()
                    })
                    current_time += timedelta(seconds=task.estimated_time)

        return timeline


# ============================================
# 单例模式
# ============================================

_collaboration_controller_instance: Optional[MultiAICollaborationController] = None

def get_collaboration_controller() -> MultiAICollaborationController:
    """获取协同控制器单例"""
    global _collaboration_controller_instance
    if _collaboration_controller_instance is None:
        _collaboration_controller_instance = MultiAICollaborationController()
    return _collaboration_controller_instance
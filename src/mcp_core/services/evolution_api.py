"""
智能进化系统API路由
提供学习系统、图谱生成、协同控制的HTTP接口
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio

from ..services.learning_system import get_learning_system, CodingSession
from ..services.graph_generator import get_graph_generator
from ..services.collaboration_controller import (
    get_collaboration_controller,
    AIAgent,
    Task,
    TaskStatus,
    LockType,
    LockLevel
)
from ..common.logger import get_logger

logger = get_logger(__name__)

# 创建路由器
router = APIRouter(prefix="/api/evolution", tags=["evolution"])

# ============================================
# 请求/响应模型
# ============================================

class LearnFromSessionRequest(BaseModel):
    """学习请求"""
    session_id: str
    project_id: str
    context_type: str = Field(..., description="bug_fix, feature, refactor, optimization")
    problem_description: str
    solution_description: str
    code_before: str
    code_after: str
    files_modified: List[str]
    time_spent: int = Field(0, description="花费时间(秒)")
    lines_changed: int = 0
    bugs_fixed: int = 0
    bugs_introduced: int = 0
    test_coverage_change: float = 0.0
    performance_metrics: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

class GetSuggestionsRequest(BaseModel):
    """获取建议请求"""
    context_type: str
    problem: str
    files: List[str] = []
    current_code: Optional[str] = None
    top_k: int = 5

class GenerateGraphRequest(BaseModel):
    """生成图谱请求"""
    project_path: str
    project_id: Optional[str] = None
    max_depth: int = 10
    min_importance: float = 0.1

class AssignTaskRequest(BaseModel):
    """分配任务请求"""
    task_id: str
    task_type: str
    description: str
    files: List[str]
    priority: int = 0
    estimated_time: int = 0
    agent_ids: List[str]

class AcquireLockRequest(BaseModel):
    """获取锁请求"""
    agent_id: str
    resource_id: str
    resource_path: str
    lock_type: str = "file"
    lock_level: str = "write"
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    intent: str = ""
    priority: int = 0

class CheckConflictsRequest(BaseModel):
    """检查冲突请求"""
    agent_id: str
    files: List[str]
    modifications: List[Dict[str, Any]] = []
    description: str = ""

# ============================================
# 学习系统API
# ============================================

@router.post("/learn")
async def learn_from_session(request: LearnFromSessionRequest):
    """从编码会话中学习"""
    try:
        learning_system = get_learning_system()

        # 创建会话对象
        session = CodingSession(
            session_id=request.session_id,
            project_id=request.project_id,
            context_type=request.context_type,
            problem_description=request.problem_description,
            solution_description=request.solution_description,
            code_before=request.code_before,
            code_after=request.code_after,
            files_modified=request.files_modified,
            time_spent=request.time_spent,
            lines_changed=request.lines_changed,
            bugs_fixed=request.bugs_fixed,
            bugs_introduced=request.bugs_introduced,
            test_coverage_change=request.test_coverage_change,
            performance_metrics=request.performance_metrics,
            metadata=request.metadata
        )

        # 执行学习
        result = learning_system.learn_from_session(session)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "result": result,
                "message": "学习完成"
            }
        )

    except Exception as e:
        logger.error(f"学习失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/suggestions")
async def get_coding_suggestions(request: GetSuggestionsRequest):
    """获取智能编码建议"""
    try:
        learning_system = get_learning_system()

        # 构建上下文
        context = {
            "type": request.context_type,
            "problem": request.problem,
            "files": request.files,
            "current_code": request.current_code
        }

        # 获取建议
        suggestions = learning_system.suggest_solution(context, request.top_k)

        # 转换为JSON可序列化格式
        suggestions_data = []
        for suggestion in suggestions:
            suggestions_data.append({
                "solution": suggestion.solution,
                "confidence": suggestion.confidence,
                "past_success_rate": suggestion.past_success_rate,
                "estimated_time": suggestion.estimated_time,
                "similar_cases": suggestion.similar_cases,
                "reasoning": suggestion.reasoning
            })

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "suggestions": suggestions_data,
                "count": len(suggestions_data)
            }
        )

    except Exception as e:
        logger.error(f"获取建议失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/experiences/{project_id}")
async def get_project_experiences(project_id: str, limit: int = 100):
    """获取项目学习经验"""
    try:
        learning_system = get_learning_system()

        with learning_system.SessionLocal() as session:
            result = session.execute(
                """
                SELECT
                    experience_id,
                    context_type,
                    problem_description,
                    solution_description,
                    reusability_score,
                    success_rate,
                    time_spent,
                    created_at
                FROM coding_experiences
                WHERE project_id = :project_id
                ORDER BY reusability_score DESC, created_at DESC
                LIMIT :limit
                """,
                {"project_id": project_id, "limit": limit}
            )

            experiences = []
            for row in result:
                experiences.append({
                    "id": row.experience_id,
                    "type": row.context_type,
                    "problem": row.problem_description,
                    "solution": row.solution_description,
                    "reusability": row.reusability_score,
                    "success_rate": row.success_rate,
                    "time_spent": row.time_spent,
                    "created_at": row.created_at.isoformat() if row.created_at else None
                })

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "project_id": project_id,
                "experiences": experiences,
                "count": len(experiences)
            }
        )

    except Exception as e:
        logger.error(f"获取经验失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# ============================================
# 图谱生成API
# ============================================

@router.post("/graph/generate")
async def generate_project_graph(
    request: GenerateGraphRequest,
    background_tasks: BackgroundTasks
):
    """生成项目知识图谱"""
    try:
        graph_generator = get_graph_generator()

        # 配置生成器
        graph_generator.max_depth = request.max_depth
        graph_generator.min_importance = request.min_importance

        # 在后台生成图谱(可能耗时)
        def generate_graph_task():
            try:
                graph, visualization = graph_generator.generate_graph(
                    request.project_path,
                    request.project_id
                )
                # 存储结果到Redis
                import json
                graph_generator.redis_client.set(
                    f"graph:{graph.project_id}",
                    json.dumps(visualization),
                    ex=86400  # 缓存24小时
                )
                logger.info(f"图谱生成完成: {graph.project_id}")
            except Exception as e:
                logger.error(f"图谱生成失败: {e}")

        background_tasks.add_task(generate_graph_task)

        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "success": True,
                "message": "图谱生成任务已启动",
                "project_id": request.project_id or "auto_generated"
            }
        )

    except Exception as e:
        logger.error(f"启动图谱生成失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/graph/{project_id}")
async def get_project_graph(project_id: str):
    """获取项目图谱"""
    try:
        graph_generator = get_graph_generator()

        # 先从缓存获取
        import json
        cached = graph_generator.redis_client.get(f"graph:{project_id}")
        if cached:
            visualization = json.loads(cached)
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "success": True,
                    "project_id": project_id,
                    "graph": visualization
                }
            )

        # 从数据库获取
        with graph_generator.SessionLocal() as session:
            # 获取节点
            nodes_result = session.execute(
                """
                SELECT * FROM graph_nodes
                WHERE project_id = :project_id
                """,
                {"project_id": project_id}
            )

            nodes = []
            for row in nodes_result:
                nodes.append({
                    "id": row.node_id,
                    "type": row.node_type,
                    "name": row.node_name,
                    "path": row.node_path,
                    "complexity": row.complexity_score,
                    "importance": row.importance_score,
                    "x": row.layout_x,
                    "y": row.layout_y,
                    "cluster": row.cluster_id
                })

            # 获取边
            edges_result = session.execute(
                """
                SELECT * FROM graph_edges
                WHERE project_id = :project_id
                """,
                {"project_id": project_id}
            )

            edges = []
            for row in edges_result:
                edges.append({
                    "id": row.edge_id,
                    "source": row.source_node_id,
                    "target": row.target_node_id,
                    "type": row.edge_type,
                    "weight": row.weight
                })

        if not nodes:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"图谱不存在: {project_id}"
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "project_id": project_id,
                "graph": {
                    "nodes": nodes,
                    "edges": edges
                }
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取图谱失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/graph/{project_id}/statistics")
async def get_graph_statistics(project_id: str):
    """获取图谱统计信息"""
    try:
        graph_generator = get_graph_generator()

        with graph_generator.SessionLocal() as session:
            result = session.execute(
                """
                SELECT
                    COUNT(DISTINCT node_id) as total_nodes,
                    COUNT(DISTINCT CASE WHEN node_type = 'class' THEN node_id END) as class_count,
                    COUNT(DISTINCT CASE WHEN node_type = 'function' THEN node_id END) as function_count,
                    AVG(complexity_score) as avg_complexity,
                    MAX(importance_score) as max_importance
                FROM graph_nodes
                WHERE project_id = :project_id
                """,
                {"project_id": project_id}
            ).first()

            if not result or not result.total_nodes:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"图谱不存在: {project_id}"
                )

            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "success": True,
                    "project_id": project_id,
                    "statistics": {
                        "total_nodes": result.total_nodes,
                        "class_count": result.class_count,
                        "function_count": result.function_count,
                        "avg_complexity": float(result.avg_complexity) if result.avg_complexity else 0,
                        "max_importance": float(result.max_importance) if result.max_importance else 0
                    }
                }
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取统计失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# ============================================
# 协同控制API
# ============================================

@router.post("/collaborate/task/assign")
async def assign_collaborative_task(request: AssignTaskRequest):
    """分配协作任务"""
    try:
        controller = get_collaboration_controller()

        # 创建任务
        task = Task(
            task_id=request.task_id,
            task_type=request.task_type,
            description=request.description,
            files=request.files,
            priority=request.priority,
            estimated_time=request.estimated_time
        )

        # 创建代理
        agents = []
        for agent_id in request.agent_ids:
            agent = AIAgent(
                agent_id=agent_id,
                name=f"Agent_{agent_id}",
                capabilities=[request.task_type]
            )
            agents.append(agent)
            controller.agents[agent_id] = agent

        # 分配任务
        result = controller.assign_task(task, agents)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": result["success"],
                "assignments": [
                    {
                        "agent_id": agent_id,
                        "task_id": assignment["task"].task_id,
                        "locks": [lock.lock_id for lock in assignment["locks"]],
                        "dependencies": assignment["dependencies"]
                    }
                    for agent_id, assignment in result.get("assignments", {}).items()
                ],
                "parallel_groups": result.get("parallel_groups", 0),
                "total_subtasks": result.get("total_subtasks", 0)
            }
        )

    except Exception as e:
        logger.error(f"任务分配失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/collaborate/lock/acquire")
async def acquire_lock(request: AcquireLockRequest):
    """获取协作锁"""
    try:
        controller = get_collaboration_controller()

        # 转换锁类型和级别
        lock_type = LockType(request.lock_type)
        lock_level = LockLevel(request.lock_level)

        # 请求锁
        lock = controller.request_lock(
            agent_id=request.agent_id,
            lock_type=lock_type,
            resource_id=request.resource_id,
            resource_path=request.resource_path,
            lock_level=lock_level,
            start_line=request.start_line,
            end_line=request.end_line,
            intent=request.intent,
            priority=request.priority
        )

        if lock:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "success": True,
                    "lock_id": lock.lock_id,
                    "status": lock.status.value,
                    "acquired_at": lock.acquired_at.isoformat() if lock.acquired_at else None,
                    "expires_at": lock.expires_at.isoformat() if lock.expires_at else None
                }
            )
        else:
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={
                    "success": False,
                    "message": "无法获取锁"
                }
            )

    except Exception as e:
        logger.error(f"获取锁失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.delete("/collaborate/lock/{lock_id}")
async def release_lock(lock_id: str):
    """释放锁"""
    try:
        controller = get_collaboration_controller()

        success = controller.release_lock(lock_id)

        if success:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "success": True,
                    "message": "锁已释放"
                }
            )
        else:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "success": False,
                    "message": "锁不存在"
                }
            )

    except Exception as e:
        logger.error(f"释放锁失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/collaborate/conflicts/check")
async def check_conflicts(request: CheckConflictsRequest):
    """检查冲突"""
    try:
        controller = get_collaboration_controller()

        # 构建更改信息
        intended_changes = {
            "agent_id": request.agent_id,
            "files": request.files,
            "modifications": request.modifications,
            "description": request.description
        }

        # 检查冲突
        result = controller.prevent_conflicts(request.agent_id, intended_changes)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "status": result["status"],
                "conflicts": [
                    {
                        "id": c.conflict_id,
                        "type": c.conflict_type,
                        "description": c.description,
                        "resolution": c.suggested_resolution
                    }
                    for c in result.get("conflicts", [])
                ],
                "locks": [
                    lock.lock_id
                    for lock in result.get("locks", [])
                ]
            }
        )

    except Exception as e:
        logger.error(f"冲突检查失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/collaborate/progress")
async def get_collaboration_progress():
    """获取协作进度"""
    try:
        controller = get_collaboration_controller()

        # 同步获取进度
        progress = await controller.synchronize_progress()

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "progress": progress
            }
        )

    except Exception as e:
        logger.error(f"获取进度失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/collaborate/locks")
async def get_active_locks():
    """获取活跃锁列表"""
    try:
        controller = get_collaboration_controller()

        locks = []
        for lock_id, lock in controller.locks.items():
            locks.append({
                "lock_id": lock.lock_id,
                "agent_id": lock.agent_id,
                "resource_id": lock.resource_id,
                "lock_type": lock.lock_type.value,
                "status": lock.status.value,
                "intent": lock.intent,
                "acquired_at": lock.acquired_at.isoformat() if lock.acquired_at else None,
                "expires_at": lock.expires_at.isoformat() if lock.expires_at else None
            })

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "locks": locks,
                "count": len(locks)
            }
        )

    except Exception as e:
        logger.error(f"获取锁列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# ============================================
# 健康检查
# ============================================

@router.get("/health")
async def health_check():
    """健康检查"""
    try:
        # 检查各个服务
        learning_system = get_learning_system()
        graph_generator = get_graph_generator()
        controller = get_collaboration_controller()

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "healthy",
                "services": {
                    "learning_system": "ok",
                    "graph_generator": "ok",
                    "collaboration_controller": "ok"
                },
                "timestamp": datetime.now().isoformat()
            }
        )

    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )
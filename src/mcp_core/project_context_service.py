#!/usr/bin/env python3
"""
项目上下文管理服务

持久化开发会话、设计决策、项目笔记，支持AI辅助的项目恢复
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, JSON, DateTime, ForeignKey, Index, func, Boolean
from sqlalchemy.orm import Session
# from sqlalchemy.ext.declarative import declarative_base  # ❌ 已废弃
from mcp_core.models.base import Base

# Base = declarative_base()  # ❌ 已废弃: 使用统一的Base


# ==================== 数据模型 ====================

class ProjectSession(Base):
    """开发会话"""
    __tablename__ = "project_sessions"
    __table_args__ = (
        Index('idx_project_time', 'project_id', 'start_time'),
        {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"}
    )

    session_id = Column(String(64), primary_key=True)
    project_id = Column(String(64), ForeignKey('code_projects.project_id', ondelete='CASCADE'), nullable=False)

    # 会话时间
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    duration_minutes = Column(Integer)  # 持续时间（分钟）

    # 会话目标和成果
    goals = Column(Text)  # 本次目标
    achievements = Column(Text)  # 完成内容
    next_steps = Column(Text)  # 下次继续点
    context_summary = Column(Text)  # AI生成的摘要

    # 工作状态
    files_modified = Column(JSON, default=list)  # 修改的文件列表
    files_created = Column(JSON, default=list)  # 新建的文件列表
    issues_encountered = Column(JSON, default=list)  # 遇到的问题
    todos_completed = Column(JSON, default=list)  # 完成的TODO

    # 元数据
    meta_data = Column(JSON, default=dict)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class DesignDecision(Base):
    """设计决策记录"""
    __tablename__ = "design_decisions"
    __table_args__ = (
        Index('idx_project_category', 'project_id', 'category'),
        {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"}
    )

    decision_id = Column(String(64), primary_key=True)
    project_id = Column(String(64), ForeignKey('code_projects.project_id', ondelete='CASCADE'), nullable=False)
    session_id = Column(String(64), ForeignKey('project_sessions.session_id', ondelete='SET NULL'))

    # 决策信息
    category = Column(String(64))  # architecture, technology, pattern, optimization
    title = Column(String(255), nullable=False)
    description = Column(Text)  # 决策内容
    reasoning = Column(Text, nullable=False)  # 为什么这样做

    # 方案对比
    alternatives = Column(JSON, default=list)  # 考虑过的其他方案
    trade_offs = Column(JSON, default=dict)  # 权衡（优点、缺点）

    # 影响分析
    impact_scope = Column(Text)  # 影响范围
    related_entities = Column(JSON, default=list)  # 相关代码实体ID
    related_files = Column(JSON, default=list)  # 相关文件

    # 决策状态
    status = Column(String(32), default="active")  # active, superseded, deprecated
    superseded_by = Column(String(64))  # 被哪个决策替代

    # 元数据
    meta_data = Column(JSON, default=dict)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class ProjectNote(Base):
    """项目笔记"""
    __tablename__ = "project_notes"
    __table_args__ = (
        Index('idx_project_category', 'project_id', 'category'),
        Index('idx_importance', 'importance'),
        {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"}
    )

    note_id = Column(String(64), primary_key=True)
    project_id = Column(String(64), ForeignKey('code_projects.project_id', ondelete='CASCADE'), nullable=False)
    session_id = Column(String(64), ForeignKey('project_sessions.session_id', ondelete='SET NULL'))

    # 笔记类型
    category = Column(String(64), nullable=False)  # pitfall, tip, optimization, issue, reminder
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)

    # 重要性
    importance = Column(Integer, default=3)  # 1-5，5最重要

    # 关联信息
    related_code = Column(Text)  # 相关代码片段
    related_entities = Column(JSON, default=list)  # 相关实体ID
    related_files = Column(JSON, default=list)  # 相关文件

    # 标签
    tags = Column(JSON, default=list)

    # 状态
    is_resolved = Column(Boolean, default=False)  # 问题是否已解决
    resolved_at = Column(DateTime)
    resolved_note = Column(Text)

    # 元数据
    meta_data = Column(JSON, default=dict)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class DevelopmentTodo(Base):
    """开发TODO"""
    __tablename__ = "development_todos"
    __table_args__ = (
        Index('idx_project_status', 'project_id', 'status'),
        Index('idx_priority', 'priority'),
        {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"}
    )

    todo_id = Column(String(64), primary_key=True)
    project_id = Column(String(64), ForeignKey('code_projects.project_id', ondelete='CASCADE'), nullable=False)
    session_id = Column(String(64), ForeignKey('project_sessions.session_id', ondelete='SET NULL'))

    # TODO信息
    title = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(64))  # feature, bugfix, refactor, test, documentation

    # 优先级和难度
    priority = Column(Integer, default=3)  # 1-5，5最高优先级
    estimated_difficulty = Column(Integer, default=3)  # 1-5，5最难
    estimated_hours = Column(Integer)  # 预估工时

    # 状态
    status = Column(String(32), default="pending")  # pending, in_progress, completed, blocked, cancelled
    progress = Column(Integer, default=0)  # 0-100

    # 依赖关系
    depends_on = Column(JSON, default=list)  # 依赖的其他TODO ID
    blocks = Column(JSON, default=list)  # 阻塞的其他TODO ID

    # 关联信息
    related_entities = Column(JSON, default=list)
    related_files = Column(JSON, default=list)

    # 完成信息
    completed_at = Column(DateTime)
    completion_note = Column(Text)

    # 元数据
    meta_data = Column(JSON, default=dict)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


# ==================== 项目上下文管理服务 ====================

class ProjectContextManager:
    """项目上下文管理器"""

    def __init__(self, db: Session):
        self.db = db
        self.current_session_id: Optional[str] = None

    # ==================== 会话管理 ====================

    def start_session(self, project_id: str, goals: str, session_id: Optional[str] = None) -> ProjectSession:
        """开始新的开发会话"""
        import uuid

        if not session_id:
            session_id = f"session_{uuid.uuid4().hex[:16]}"

        session = ProjectSession(
            session_id=session_id,
            project_id=project_id,
            start_time=datetime.now(),
            goals=goals
        )

        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)

        self.current_session_id = session_id
        print(f"✅ 开发会话开始: {session_id}")
        print(f"   目标: {goals}")

        return session

    def end_session(self,
                   session_id: str,
                   achievements: str,
                   next_steps: Optional[str] = None,
                   files_modified: Optional[List[str]] = None,
                   issues_encountered: Optional[List[Dict]] = None) -> ProjectSession:
        """结束开发会话"""
        session = self.db.query(ProjectSession).filter_by(session_id=session_id).first()
        if not session:
            raise ValueError(f"会话不存在: {session_id}")

        session.end_time = datetime.now()
        session.achievements = achievements
        session.next_steps = next_steps

        # 计算持续时间
        if session.start_time:
            duration = session.end_time - session.start_time
            session.duration_minutes = int(duration.total_seconds() / 60)

        # 记录工作状态
        if files_modified:
            session.files_modified = files_modified
        if issues_encountered:
            session.issues_encountered = issues_encountered

        self.db.commit()
        self.db.refresh(session)

        print(f"✅ 开发会话结束: {session_id}")
        print(f"   持续时间: {session.duration_minutes}分钟")
        print(f"   完成内容: {achievements}")

        if self.current_session_id == session_id:
            self.current_session_id = None

        return session

    def get_last_session(self, project_id: str) -> Optional[ProjectSession]:
        """获取最近的会话"""
        return self.db.query(ProjectSession).filter_by(
            project_id=project_id
        ).order_by(ProjectSession.start_time.desc()).first()

    def get_session_history(self, project_id: str, limit: int = 10) -> List[ProjectSession]:
        """获取会话历史"""
        return self.db.query(ProjectSession).filter_by(
            project_id=project_id
        ).order_by(ProjectSession.start_time.desc()).limit(limit).all()

    def update_session_summary(self, session_id: str, context_summary: str) -> None:
        """更新会话摘要（AI生成）"""
        session = self.db.query(ProjectSession).filter_by(session_id=session_id).first()
        if session:
            session.context_summary = context_summary
            self.db.commit()

    # ==================== 设计决策管理 ====================

    def record_decision(self,
                       project_id: str,
                       title: str,
                       reasoning: str,
                       category: str = "architecture",
                       description: Optional[str] = None,
                       alternatives: Optional[List[Dict]] = None,
                       trade_offs: Optional[Dict] = None,
                       impact_scope: Optional[str] = None,
                       decision_id: Optional[str] = None) -> DesignDecision:
        """记录设计决策"""
        import uuid

        if not decision_id:
            decision_id = f"decision_{uuid.uuid4().hex[:16]}"

        decision = DesignDecision(
            decision_id=decision_id,
            project_id=project_id,
            session_id=self.current_session_id,
            category=category,
            title=title,
            description=description,
            reasoning=reasoning,
            alternatives=alternatives or [],
            trade_offs=trade_offs or {},
            impact_scope=impact_scope
        )

        self.db.add(decision)
        self.db.commit()
        self.db.refresh(decision)

        print(f"✅ 设计决策已记录: {title}")
        return decision

    def get_decisions(self,
                     project_id: str,
                     category: Optional[str] = None,
                     status: str = "active") -> List[DesignDecision]:
        """获取设计决策"""
        query = self.db.query(DesignDecision).filter_by(
            project_id=project_id,
            status=status
        )

        if category:
            query = query.filter_by(category=category)

        return query.order_by(DesignDecision.created_at.desc()).all()

    def supersede_decision(self, old_decision_id: str, new_decision_id: str) -> None:
        """替代旧决策"""
        old_decision = self.db.query(DesignDecision).filter_by(decision_id=old_decision_id).first()
        if old_decision:
            old_decision.status = "superseded"
            old_decision.superseded_by = new_decision_id
            self.db.commit()

    # ==================== 项目笔记管理 ====================

    def add_note(self,
                project_id: str,
                category: str,
                title: str,
                content: str,
                importance: int = 3,
                related_code: Optional[str] = None,
                tags: Optional[List[str]] = None,
                note_id: Optional[str] = None) -> ProjectNote:
        """添加项目笔记"""
        import uuid

        if not note_id:
            note_id = f"note_{uuid.uuid4().hex[:16]}"

        note = ProjectNote(
            note_id=note_id,
            project_id=project_id,
            session_id=self.current_session_id,
            category=category,
            title=title,
            content=content,
            importance=importance,
            related_code=related_code,
            tags=tags or []
        )

        self.db.add(note)
        self.db.commit()
        self.db.refresh(note)

        print(f"✅ 笔记已添加: {title} ({category})")
        return note

    def get_notes(self,
                 project_id: str,
                 category: Optional[str] = None,
                 min_importance: int = 1,
                 unresolved_only: bool = False) -> List[ProjectNote]:
        """获取项目笔记"""
        query = self.db.query(ProjectNote).filter_by(project_id=project_id)

        if category:
            query = query.filter_by(category=category)

        if min_importance > 1:
            query = query.filter(ProjectNote.importance >= min_importance)

        if unresolved_only:
            query = query.filter_by(is_resolved=False)

        return query.order_by(ProjectNote.importance.desc(), ProjectNote.created_at.desc()).all()

    def resolve_note(self, note_id: str, resolved_note: Optional[str] = None) -> None:
        """标记笔记已解决"""
        note = self.db.query(ProjectNote).filter_by(note_id=note_id).first()
        if note:
            note.is_resolved = True
            note.resolved_at = datetime.now()
            note.resolved_note = resolved_note
            self.db.commit()

    # ==================== TODO管理 ====================

    def create_todo(self,
                   project_id: str,
                   title: str,
                   description: Optional[str] = None,
                   category: str = "feature",
                   priority: int = 3,
                   estimated_difficulty: int = 3,
                   estimated_hours: Optional[int] = None,
                   depends_on: Optional[List[str]] = None,
                   todo_id: Optional[str] = None) -> DevelopmentTodo:
        """创建TODO"""
        import uuid

        if not todo_id:
            todo_id = f"todo_{uuid.uuid4().hex[:16]}"

        todo = DevelopmentTodo(
            todo_id=todo_id,
            project_id=project_id,
            session_id=self.current_session_id,
            title=title,
            description=description,
            category=category,
            priority=priority,
            estimated_difficulty=estimated_difficulty,
            estimated_hours=estimated_hours,
            depends_on=depends_on or []
        )

        self.db.add(todo)
        self.db.commit()
        self.db.refresh(todo)

        print(f"✅ TODO已创建: {title} (优先级: {priority})")
        return todo

    def update_todo_status(self,
                          todo_id: str,
                          status: str,
                          progress: Optional[int] = None,
                          completion_note: Optional[str] = None) -> DevelopmentTodo:
        """更新TODO状态"""
        todo = self.db.query(DevelopmentTodo).filter_by(todo_id=todo_id).first()
        if not todo:
            raise ValueError(f"TODO不存在: {todo_id}")

        todo.status = status
        if progress is not None:
            todo.progress = progress

        if status == "completed":
            todo.completed_at = datetime.now()
            todo.progress = 100
            if completion_note:
                todo.completion_note = completion_note

        self.db.commit()
        self.db.refresh(todo)

        print(f"✅ TODO状态已更新: {todo.title} → {status}")
        return todo

    def get_todos(self,
                 project_id: str,
                 status: Optional[str] = None,
                 category: Optional[str] = None,
                 min_priority: int = 1) -> List[DevelopmentTodo]:
        """获取TODO列表"""
        query = self.db.query(DevelopmentTodo).filter_by(project_id=project_id)

        if status:
            query = query.filter_by(status=status)

        if category:
            query = query.filter_by(category=category)

        if min_priority > 1:
            query = query.filter(DevelopmentTodo.priority >= min_priority)

        return query.order_by(DevelopmentTodo.priority.desc(), DevelopmentTodo.created_at.desc()).all()

    def get_next_todo(self, project_id: str) -> Optional[DevelopmentTodo]:
        """获取建议的下一个TODO（考虑依赖关系）"""
        # 获取所有pending的TODO
        pending_todos = self.get_todos(project_id, status="pending")

        if not pending_todos:
            return None

        # 过滤掉有未完成依赖的TODO
        available_todos = []
        for todo in pending_todos:
            if not todo.depends_on:
                available_todos.append(todo)
            else:
                # 检查依赖是否都完成了
                all_deps_completed = True
                for dep_id in todo.depends_on:
                    dep_todo = self.db.query(DevelopmentTodo).filter_by(todo_id=dep_id).first()
                    if not dep_todo or dep_todo.status != "completed":
                        all_deps_completed = False
                        break
                if all_deps_completed:
                    available_todos.append(todo)

        if not available_todos:
            return None

        # 按优先级排序，返回最高优先级的
        available_todos.sort(key=lambda x: (-x.priority, x.created_at))
        return available_todos[0]

    # ==================== 上下文恢复 ====================

    def generate_resume_context(self, project_id: str) -> Dict[str, Any]:
        """生成恢复上下文（用于AI生成恢复briefing）"""

        # 获取最近的会话
        last_session = self.get_last_session(project_id)

        # 获取进行中的TODO
        in_progress_todos = self.get_todos(project_id, status="in_progress")

        # 获取pending的TODO
        pending_todos = self.get_todos(project_id, status="pending", min_priority=3)

        # 获取最近的设计决策
        recent_decisions = self.get_decisions(project_id)[:5]

        # 获取未解决的问题笔记
        issues = self.get_notes(project_id, category="issue", unresolved_only=True)

        # 获取重要提示
        important_notes = self.get_notes(project_id, min_importance=4)

        # 构建上下文
        context = {
            "last_session": {
                "session_id": last_session.session_id if last_session else None,
                "start_time": last_session.start_time.isoformat() if last_session else None,
                "end_time": last_session.end_time.isoformat() if last_session and last_session.end_time else None,
                "goals": last_session.goals if last_session else None,
                "achievements": last_session.achievements if last_session else None,
                "next_steps": last_session.next_steps if last_session else None,
                "context_summary": last_session.context_summary if last_session else None,
                "files_modified": last_session.files_modified if last_session else [],
                "issues_encountered": last_session.issues_encountered if last_session else []
            } if last_session else None,

            "in_progress": [
                {
                    "todo_id": todo.todo_id,
                    "title": todo.title,
                    "description": todo.description,
                    "progress": todo.progress,
                    "category": todo.category
                }
                for todo in in_progress_todos
            ],

            "pending_todos": [
                {
                    "todo_id": todo.todo_id,
                    "title": todo.title,
                    "priority": todo.priority,
                    "category": todo.category,
                    "estimated_hours": todo.estimated_hours
                }
                for todo in pending_todos[:10]  # 只返回前10个
            ],

            "recent_decisions": [
                {
                    "decision_id": decision.decision_id,
                    "title": decision.title,
                    "category": decision.category,
                    "reasoning": decision.reasoning[:200] + "..." if len(decision.reasoning) > 200 else decision.reasoning
                }
                for decision in recent_decisions
            ],

            "unresolved_issues": [
                {
                    "note_id": note.note_id,
                    "title": note.title,
                    "content": note.content[:200] + "..." if len(note.content) > 200 else note.content,
                    "importance": note.importance
                }
                for note in issues
            ],

            "important_notes": [
                {
                    "note_id": note.note_id,
                    "title": note.title,
                    "category": note.category,
                    "content": note.content[:200] + "..." if len(note.content) > 200 else note.content
                }
                for note in important_notes[:5]  # 只返回前5个
            ]
        }

        return context

    # ==================== 统计信息 ====================

    def get_project_statistics(self, project_id: str) -> Dict[str, Any]:
        """获取项目统计信息"""

        total_sessions = self.db.query(ProjectSession).filter_by(project_id=project_id).count()
        total_time = self.db.query(func.sum(ProjectSession.duration_minutes)).filter_by(project_id=project_id).scalar() or 0

        todos_by_status = {}
        for status in ["pending", "in_progress", "completed", "blocked", "cancelled"]:
            count = self.db.query(DevelopmentTodo).filter_by(project_id=project_id, status=status).count()
            todos_by_status[status] = count

        total_todos = sum(todos_by_status.values())
        completion_rate = (todos_by_status.get("completed", 0) / total_todos * 100) if total_todos > 0 else 0

        decisions_count = self.db.query(DesignDecision).filter_by(project_id=project_id, status="active").count()
        notes_count = self.db.query(ProjectNote).filter_by(project_id=project_id).count()
        unresolved_issues = self.db.query(ProjectNote).filter_by(project_id=project_id, category="issue", is_resolved=False).count()

        return {
            "total_sessions": total_sessions,
            "total_development_hours": round(total_time / 60, 1),
            "todos": {
                "total": total_todos,
                "by_status": todos_by_status,
                "completion_rate": round(completion_rate, 1)
            },
            "decisions_count": decisions_count,
            "notes_count": notes_count,
            "unresolved_issues": unresolved_issues
        }


# ==================== 测试代码 ====================

def test_context_manager():
    """测试上下文管理器"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    # 创建数据库连接
    engine = create_engine("mysql+pymysql://root:Wxwy.2025%40%23@localhost:3306/mcp_db?charset=utf8mb4")
    Base.metadata.create_all(engine)

    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    # 创建管理器
    manager = ProjectContextManager(db)

    print("=" * 60)
    print("项目上下文管理测试")
    print("=" * 60)

    # 测试开始会话
    session = manager.start_session(
        project_id="test_project_001",
        goals="实现用户认证模块"
    )

    # 测试记录决策
    decision = manager.record_decision(
        project_id="test_project_001",
        title="使用JWT进行身份认证",
        reasoning="JWT无状态，易于扩展，适合微服务架构",
        category="technology",
        alternatives=[
            {"name": "Session", "pros": "简单", "cons": "有状态，难以扩展"},
            {"name": "OAuth2", "pros": "标准协议", "cons": "过于复杂"}
        ],
        trade_offs={"pros": ["无状态", "可扩展"], "cons": ["无法即时撤销"]}
    )

    # 测试添加笔记
    note = manager.add_note(
        project_id="test_project_001",
        category="pitfall",
        title="JWT Secret必须足够长",
        content="Secret少于32字节会导致安全问题，建议使用64字节",
        importance=5,
        tags=["security", "jwt"]
    )

    # 测试创建TODO
    todo1 = manager.create_todo(
        project_id="test_project_001",
        title="实现JWT生成和验证",
        description="创建token生成和验证函数",
        category="feature",
        priority=5,
        estimated_hours=2
    )

    todo2 = manager.create_todo(
        project_id="test_project_001",
        title="添加认证中间件",
        description="在FastAPI中集成JWT认证",
        category="feature",
        priority=4,
        estimated_hours=3,
        depends_on=[todo1.todo_id]
    )

    # 测试结束会话
    manager.end_session(
        session_id=session.session_id,
        achievements="完成JWT基础实现和单元测试",
        next_steps="继续实现认证中间件",
        files_modified=["auth/jwt.py", "tests/test_jwt.py"]
    )

    # 测试获取恢复上下文
    print("\n" + "=" * 60)
    print("生成恢复上下文")
    print("=" * 60)
    context = manager.generate_resume_context("test_project_001")
    print(f"\n上次会话: {context['last_session']['goals']}")
    print(f"完成内容: {context['last_session']['achievements']}")
    print(f"下一步: {context['last_session']['next_steps']}")
    print(f"\nPending TODOs: {len(context['pending_todos'])}")
    print(f"设计决策: {len(context['recent_decisions'])}")

    # 测试统计信息
    print("\n" + "=" * 60)
    print("项目统计")
    print("=" * 60)
    stats = manager.get_project_statistics("test_project_001")
    print(f"\n总会话数: {stats['total_sessions']}")
    print(f"总开发时间: {stats['total_development_hours']}小时")
    print(f"TODO完成率: {stats['todos']['completion_rate']}%")

    db.close()


if __name__ == "__main__":
    test_context_manager()

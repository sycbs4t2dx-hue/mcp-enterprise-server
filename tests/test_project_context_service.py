"""
Project Context Service Unit Tests
测试项目上下文服务的所有功能
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch

from src.mcp_core.project_context_service import (
    ProjectContextManager,
    ProjectSession,
    DesignDecision,
    ProjectNote,
    DevelopmentTodo
)


class TestSessionManagement:
    """会话管理测试"""

    @pytest.fixture
    def mock_db(self):
        """Mock数据库会话"""
        return MagicMock()

    @pytest.fixture
    def context_manager(self, mock_db):
        """创建上下文管理器实例"""
        return ProjectContextManager(db=mock_db)

    @pytest.mark.unit
    @pytest.mark.db
    def test_start_session_success(self, context_manager, mock_db):
        """测试:开始会话成功"""
        # Arrange
        project_id = "test-project"
        goals = "实现用户认证功能"
        
        # Act
        session = context_manager.start_session(project_id, goals)
        
        # Assert
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        assert context_manager.current_session_id is not None

    @pytest.mark.unit
    @pytest.mark.db
    def test_start_session_with_custom_id(self, context_manager, mock_db):
        """测试:开始会话 - 自定义ID"""
        # Arrange
        project_id = "test-project"
        goals = "重构数据库层"
        custom_session_id = "custom_session_123"
        
        # Act
        session = context_manager.start_session(project_id, goals, session_id=custom_session_id)
        
        # Assert
        mock_db.add.assert_called_once()
        assert context_manager.current_session_id == custom_session_id

    @pytest.mark.unit
    @pytest.mark.db
    def test_end_session_success(self, context_manager, mock_db):
        """测试:结束会话成功"""
        # Arrange
        session_id = "session_123"
        achievements = "完成用户登录和注册"
        next_steps = "实现权限管理"
        
        # Mock查询返回
        mock_session = MagicMock(spec=ProjectSession)
        mock_session.session_id = session_id
        mock_session.start_time = datetime.now() - timedelta(hours=2)
        
        mock_query = MagicMock()
        mock_query.filter_by.return_value.first.return_value = mock_session
        mock_db.query.return_value = mock_query
        
        context_manager.current_session_id = session_id
        
        # Act
        result = context_manager.end_session(
            session_id, 
            achievements,
            next_steps=next_steps
        )
        
        # Assert
        assert mock_session.achievements == achievements
        assert mock_session.next_steps == next_steps
        assert mock_session.duration_minutes > 0
        mock_db.commit.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.db
    def test_end_session_not_found(self, context_manager, mock_db):
        """测试:结束会话 - 会话不存在"""
        # Arrange
        session_id = "non_existent"
        
        # Mock查询返回None
        mock_query = MagicMock()
        mock_query.filter_by.return_value.first.return_value = None
        mock_db.query.return_value = mock_query
        
        # Act & Assert
        with pytest.raises(ValueError, match="会话不存在"):
            context_manager.end_session(session_id, "完成内容")

    @pytest.mark.unit
    @pytest.mark.db
    def test_end_session_with_files_and_issues(self, context_manager, mock_db):
        """测试:结束会话 - 包含文件和问题"""
        # Arrange
        session_id = "session_123"
        achievements = "完成功能"
        files_modified = ["src/auth.py", "tests/test_auth.py"]
        issues = [{"issue": "数据库连接超时", "solution": "增加重试机制"}]
        
        mock_session = MagicMock(spec=ProjectSession)
        mock_session.session_id = session_id
        mock_session.start_time = datetime.now() - timedelta(minutes=30)
        
        mock_query = MagicMock()
        mock_query.filter_by.return_value.first.return_value = mock_session
        mock_db.query.return_value = mock_query
        
        # Act
        result = context_manager.end_session(
            session_id,
            achievements,
            files_modified=files_modified,
            issues_encountered=issues
        )
        
        # Assert
        assert mock_session.files_modified == files_modified
        assert mock_session.issues_encountered == issues

    @pytest.mark.unit
    @pytest.mark.db
    def test_get_last_session(self, context_manager, mock_db):
        """测试:获取最近会话"""
        # Arrange
        project_id = "test-project"
        
        mock_session = MagicMock(spec=ProjectSession)
        mock_query = MagicMock()
        mock_query.filter_by.return_value.order_by.return_value.first.return_value = mock_session
        mock_db.query.return_value = mock_query
        
        # Act
        session = context_manager.get_last_session(project_id)
        
        # Assert
        assert session == mock_session

    @pytest.mark.unit
    @pytest.mark.db
    def test_get_session_history(self, context_manager, mock_db):
        """测试:获取会话历史"""
        # Arrange
        project_id = "test-project"
        limit = 5
        
        mock_sessions = [MagicMock(spec=ProjectSession) for _ in range(5)]
        mock_query = MagicMock()
        mock_query.filter_by.return_value.order_by.return_value.limit.return_value.all.return_value = mock_sessions
        mock_db.query.return_value = mock_query
        
        # Act
        sessions = context_manager.get_session_history(project_id, limit=limit)
        
        # Assert
        assert len(sessions) == 5

    @pytest.mark.unit
    @pytest.mark.db
    def test_update_session_summary(self, context_manager, mock_db):
        """测试:更新会话摘要"""
        # Arrange
        session_id = "session_123"
        summary = "本次会话实现了用户认证模块,包括登录、注册和权限验证"
        
        mock_session = MagicMock(spec=ProjectSession)
        mock_query = MagicMock()
        mock_query.filter_by.return_value.first.return_value = mock_session
        mock_db.query.return_value = mock_query
        
        # Act
        context_manager.update_session_summary(session_id, summary)
        
        # Assert
        assert mock_session.context_summary == summary
        mock_db.commit.assert_called_once()


class TestDesignDecisionManagement:
    """设计决策管理测试"""

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    @pytest.fixture
    def context_manager(self, mock_db):
        return ProjectContextManager(db=mock_db)

    @pytest.mark.unit
    @pytest.mark.db
    def test_record_decision_success(self, context_manager, mock_db):
        """测试:记录设计决策成功"""
        # Arrange
        project_id = "test-project"
        title = "选择PostgreSQL作为主数据库"
        reasoning = "需要复杂查询和事务支持"
        category = "technology"
        
        # Act
        decision = context_manager.record_decision(
            project_id, 
            title,
            reasoning,
            category=category
        )
        
        # Assert
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.db
    def test_record_decision_with_alternatives(self, context_manager, mock_db):
        """测试:记录设计决策 - 包含备选方案"""
        # Arrange
        project_id = "test-project"
        title = "使用Redis缓存"
        reasoning = "提高读性能"
        alternatives = [
            {"option": "Memcached", "pros": "简单", "cons": "功能少"},
            {"option": "本地缓存", "pros": "零延迟", "cons": "扩展性差"}
        ]
        trade_offs = {
            "pros": ["高性能", "持久化", "丰富数据结构"],
            "cons": ["内存开销", "运维复杂度"]
        }
        
        # Act
        decision = context_manager.record_decision(
            project_id,
            title,
            reasoning,
            alternatives=alternatives,
            trade_offs=trade_offs
        )
        
        # Assert
        mock_db.add.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.db
    def test_get_decisions_all(self, context_manager, mock_db):
        """测试:获取所有设计决策"""
        # Arrange
        project_id = "test-project"
        
        mock_decisions = [MagicMock(spec=DesignDecision) for _ in range(3)]
        mock_query = MagicMock()
        mock_query.filter_by.return_value.order_by.return_value.all.return_value = mock_decisions
        mock_db.query.return_value = mock_query
        
        # Act
        decisions = context_manager.get_decisions(project_id)
        
        # Assert
        assert len(decisions) == 3

    @pytest.mark.unit
    @pytest.mark.db
    def test_get_decisions_by_category(self, context_manager, mock_db):
        """测试:获取决策 - 按类别筛选"""
        # Arrange
        project_id = "test-project"
        category = "architecture"
        
        mock_decisions = [MagicMock(spec=DesignDecision)]
        mock_query = MagicMock()
        mock_query.filter_by.return_value.filter_by.return_value.order_by.return_value.all.return_value = mock_decisions
        mock_db.query.return_value = mock_query
        
        # Act
        decisions = context_manager.get_decisions(project_id, category=category)
        
        # Assert
        assert len(decisions) == 1

    @pytest.mark.unit
    @pytest.mark.db
    def test_supersede_decision(self, context_manager, mock_db):
        """测试:替代旧决策"""
        # Arrange
        old_decision_id = "old_dec_123"
        new_decision_id = "new_dec_456"
        
        mock_decision = MagicMock(spec=DesignDecision)
        mock_query = MagicMock()
        mock_query.filter_by.return_value.first.return_value = mock_decision
        mock_db.query.return_value = mock_query
        
        # Act
        context_manager.supersede_decision(old_decision_id, new_decision_id)
        
        # Assert
        assert mock_decision.status == "superseded"
        assert mock_decision.superseded_by == new_decision_id
        mock_db.commit.assert_called_once()


class TestProjectNoteManagement:
    """项目笔记管理测试"""

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    @pytest.fixture
    def context_manager(self, mock_db):
        return ProjectContextManager(db=mock_db)

    @pytest.mark.unit
    @pytest.mark.db
    def test_add_note_success(self, context_manager, mock_db):
        """测试:添加笔记成功"""
        # Arrange
        project_id = "test-project"
        category = "pitfall"
        title = "避免N+1查询"
        content = "使用join或select_related避免循环查询"
        importance = 4
        
        # Act
        note = context_manager.add_note(
            project_id,
            category,
            title,
            content,
            importance=importance
        )
        
        # Assert
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.db
    def test_add_note_with_code_and_tags(self, context_manager, mock_db):
        """测试:添加笔记 - 包含代码和标签"""
        # Arrange
        project_id = "test-project"
        category = "tip"
        title = "性能优化技巧"
        content = "使用批量插入减少数据库往返"
        related_code = "Model.objects.bulk_create([...])"
        tags = ["performance", "database", "optimization"]
        
        # Act
        note = context_manager.add_note(
            project_id,
            category,
            title,
            content,
            related_code=related_code,
            tags=tags
        )
        
        # Assert
        mock_db.add.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.db
    def test_get_notes_all(self, context_manager, mock_db):
        """测试:获取所有笔记"""
        # Arrange
        project_id = "test-project"
        
        mock_notes = [MagicMock(spec=ProjectNote) for _ in range(5)]
        mock_query = MagicMock()
        mock_query.filter_by.return_value.order_by.return_value.all.return_value = mock_notes
        mock_db.query.return_value = mock_query
        
        # Act
        notes = context_manager.get_notes(project_id)
        
        # Assert
        assert len(notes) == 5

    @pytest.mark.unit
    @pytest.mark.db
    def test_get_notes_by_category(self, context_manager, mock_db):
        """测试:获取笔记 - 按类别"""
        # Arrange
        project_id = "test-project"
        category = "issue"
        
        mock_notes = [MagicMock(spec=ProjectNote)]
        mock_query = MagicMock()
        mock_query.filter_by.return_value.filter_by.return_value.order_by.return_value.all.return_value = mock_notes
        mock_db.query.return_value = mock_query
        
        # Act
        notes = context_manager.get_notes(project_id, category=category)
        
        # Assert
        assert len(notes) == 1

    @pytest.mark.unit
    @pytest.mark.db
    def test_get_notes_by_importance(self, context_manager, mock_db):
        """测试:获取笔记 - 按重要性筛选"""
        # Arrange
        project_id = "test-project"
        min_importance = 4
        
        mock_notes = [MagicMock(spec=ProjectNote) for _ in range(2)]
        mock_query = MagicMock()
        mock_query.filter_by.return_value.filter.return_value.order_by.return_value.all.return_value = mock_notes
        mock_db.query.return_value = mock_query
        
        # Act
        notes = context_manager.get_notes(project_id, min_importance=min_importance)
        
        # Assert
        assert len(notes) == 2

    @pytest.mark.unit
    @pytest.mark.db
    def test_get_notes_unresolved_only(self, context_manager, mock_db):
        """测试:获取笔记 - 只获取未解决"""
        # Arrange
        project_id = "test-project"
        
        mock_notes = [MagicMock(spec=ProjectNote)]
        mock_query = MagicMock()
        mock_query.filter_by.return_value.filter_by.return_value.order_by.return_value.all.return_value = mock_notes
        mock_db.query.return_value = mock_query
        
        # Act
        notes = context_manager.get_notes(project_id, unresolved_only=True)
        
        # Assert
        assert len(notes) == 1

    @pytest.mark.unit
    @pytest.mark.db
    def test_resolve_note(self, context_manager, mock_db):
        """测试:标记笔记已解决"""
        # Arrange
        note_id = "note_123"
        resolved_note = "问题已通过优化索引解决"
        
        mock_note = MagicMock(spec=ProjectNote)
        mock_query = MagicMock()
        mock_query.filter_by.return_value.first.return_value = mock_note
        mock_db.query.return_value = mock_query
        
        # Act
        context_manager.resolve_note(note_id, resolved_note=resolved_note)
        
        # Assert
        assert mock_note.is_resolved is True
        assert mock_note.resolved_note == resolved_note
        assert mock_note.resolved_at is not None
        mock_db.commit.assert_called_once()


class TestDataModels:
    """数据模型测试"""

    @pytest.mark.unit
    def test_project_session_model(self):
        """测试:ProjectSession模型"""
        # Arrange & Act
        session = ProjectSession(
            session_id="session_123",
            project_id="test-project",
            start_time=datetime.now(),
            goals="测试目标"
        )
        
        # Assert
        assert session.session_id == "session_123"
        assert session.project_id == "test-project"
        assert session.goals == "测试目标"

    @pytest.mark.unit
    def test_design_decision_model(self):
        """测试:DesignDecision模型"""
        # Arrange & Act
        decision = DesignDecision(
            decision_id="dec_123",
            project_id="test-project",
            category="architecture",
            title="选择微服务架构",
            reasoning="提高可扩展性"
        )
        
        # Assert
        assert decision.decision_id == "dec_123"
        assert decision.category == "architecture"
        assert decision.status == "active"

    @pytest.mark.unit
    def test_project_note_model(self):
        """测试:ProjectNote模型"""
        # Arrange & Act
        note = ProjectNote(
            note_id="note_123",
            project_id="test-project",
            category="tip",
            title="优化建议",
            content="使用缓存",
            importance=4
        )
        
        # Assert
        assert note.note_id == "note_123"
        assert note.category == "tip"
        assert note.importance == 4
        assert note.is_resolved is False

    @pytest.mark.unit
    def test_development_todo_model(self):
        """测试:DevelopmentTodo模型"""
        # Arrange & Act
        todo = DevelopmentTodo(
            todo_id="todo_123",
            project_id="test-project",
            title="实现用户认证",
            priority=5,
            estimated_difficulty=3
        )
        
        # Assert
        assert todo.todo_id == "todo_123"
        assert todo.priority == 5
        assert todo.status == "pending"
        assert todo.progress == 0

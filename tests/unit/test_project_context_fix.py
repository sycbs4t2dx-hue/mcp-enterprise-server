#!/usr/bin/env python3
"""
测试 project_notes 和 development_todos 表修复
验证所有6个MCP工具是否正常工作
"""
import sys
import os

# 设置正确的Python路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from mcp_core.project_context_service import ProjectContextService

def test_project_context():
    """测试项目上下文服务的所有功能"""
    # 数据库连接
    db_password = os.getenv("DB_PASSWORD", "Wxwy.2025@#")
    encoded_password = db_password.replace("@", "%40").replace("#", "%23")
    db_url = f"mysql+pymysql://root:{encoded_password}@localhost:3306/mcp_db?charset=utf8mb4"

    engine = create_engine(db_url, echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # 初始化服务
        service = ProjectContextService(session)
        project_id = "history-timeline"

        print("=" * 60)
        print("测试 project_context_service 修复")
        print("=" * 60)

        # 测试1: 创建开发会话
        print("\n测试1: 启动开发会话...")
        session_result = service.start_development_session(
            project_id=project_id,
            description="测试Schema修复",
            goals=["验证 project_notes", "验证 development_todos"]
        )

        if not session_result.get("success"):
            print(f"❌ 测试1失败: {session_result.get('error')}")
            return False

        session_id = session_result["session"]["session_id"]
        print(f"✅ 测试1成功: Session ID = {session_id}")

        # 测试2: 添加项目笔记 (add_project_note)
        print("\n测试2: 添加项目笔记...")
        note_result = service.add_project_note(
            project_id=project_id,
            session_id=session_id,
            category="tip",
            title="Schema修复验证",
            content="验证 project_notes 表的 session_id 和其他字段是否正常工作",
            importance=5,
            tags=["database", "schema", "test"]
        )

        if not note_result.get("success"):
            print(f"❌ 测试2失败: {note_result.get('error')}")
            return False

        note_id = note_result["note"]["note_id"]
        print(f"✅ 测试2成功: Note ID = {note_id}")

        # 测试3: 创建TODO (create_todo)
        print("\n测试3: 创建TODO...")
        todo_result = service.create_todo(
            project_id=project_id,
            session_id=session_id,
            title="验证Schema修复",
            description="测试 development_todos 表的所有字段",
            category="test",
            priority=5,
            estimated_difficulty=3,
            estimated_hours=1
        )

        if not todo_result.get("success"):
            print(f"❌ 测试3失败: {todo_result.get('error')}")
            return False

        todo_id = todo_result["todo"]["todo_id"]
        print(f"✅ 测试3成功: TODO ID = {todo_id}")

        # 测试4: 列出项目笔记 (list_project_notes)
        print("\n测试4: 列出项目笔记...")
        notes_result = service.list_project_notes(
            project_id=project_id,
            limit=5
        )

        if not notes_result.get("success"):
            print(f"❌ 测试4失败: {notes_result.get('error')}")
            return False

        note_count = len(notes_result["notes"])
        print(f"✅ 测试4成功: 找到 {note_count} 条笔记")

        # 测试5: 列出TODO (list_todos)
        print("\n测试5: 列出TODO...")
        todos_result = service.list_todos(
            project_id=project_id,
            status="pending"
        )

        if not todos_result.get("success"):
            print(f"❌ 测试5失败: {todos_result.get('error')}")
            return False

        todo_count = len(todos_result["todos"])
        print(f"✅ 测试5成功: 找到 {todo_count} 条TODO")

        # 测试6: 列出设计决策 (list_design_decisions) - 之前受事务回滚影响
        print("\n测试6: 列出设计决策...")
        decisions_result = service.list_design_decisions(
            project_id=project_id,
            limit=5
        )

        if not decisions_result.get("success"):
            print(f"❌ 测试6失败: {decisions_result.get('error')}")
            return False

        decision_count = len(decisions_result["decisions"])
        print(f"✅ 测试6成功: 找到 {decision_count} 条设计决策")

        # 测试7: 获取项目上下文 (get_project_context) - 之前受事务回滚影响
        print("\n测试7: 获取项目上下文...")
        context_result = service.get_project_context(
            project_id=project_id
        )

        if not context_result.get("success"):
            print(f"❌ 测试7失败: {context_result.get('error')}")
            return False

        print(f"✅ 测试7成功: 项目上下文获取成功")
        print(f"   - 设计决策: {len(context_result['context']['design_decisions'])} 条")
        print(f"   - 项目笔记: {len(context_result['context']['notes'])} 条")
        print(f"   - TODO: {len(context_result['context']['todos'])} 条")
        print(f"   - 开发会话: {len(context_result['context']['sessions'])} 个")

        print("\n" + "=" * 60)
        print("🎉 所有测试通过!")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n❌ 测试过程中出现异常: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        session.close()

if __name__ == "__main__":
    success = test_project_context()
    sys.exit(0 if success else 1)

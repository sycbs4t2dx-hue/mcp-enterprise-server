#!/usr/bin/env python3
"""
测试 design_decisions 表修复
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.mcp_core.services.memory_service import MemoryService

def test_design_decision():
    """测试设计决策存储"""
    # 数据库连接
    db_password = os.getenv("DB_PASSWORD", "Wxwy.2025@#")
    encoded_password = db_password.replace("@", "%40").replace("#", "%23")
    db_url = f"mysql+pymysql://root:{encoded_password}@localhost:3306/mcp_db?charset=utf8mb4"

    engine = create_engine(db_url, echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # 初始化记忆服务
        memory_service = MemoryService(session)

        # 测试内容
        test_content = """核心路由架构:
后端路由(server.js):
- /api/events - 事件CRUD和查询
- /api/ai - AI智能助手功能
- /api/verified - 验证相关服务

前端组件架构(App.jsx):
- Timeline - 时间轴主组件
- SearchBar - 搜索栏
- EventDetail - 事件详情弹窗"""

        print("测试记忆存储...")
        result = memory_service.store_memory(
            project_id="history-timeline",
            content=test_content,
            memory_level="long"
        )

        print(f"✅ 存储成功!")
        print(f"   Memory ID: {result.get('memory_id')}")
        print(f"   级别: {result.get('memory_level')}")

        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        session.close()

if __name__ == "__main__":
    success = test_design_decision()
    sys.exit(0 if success else 1)

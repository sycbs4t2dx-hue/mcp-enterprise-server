"""
Pytest Configuration and Fixtures
提供测试所需的fixtures和配置
"""
import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

# 设置测试环境变量
os.environ["TEST_MODE"] = "true"
os.environ["DB_PASSWORD"] = "Wxwy.2025@#"


@pytest.fixture(scope="session")
def db_engine():
    """创建测试数据库引擎 (session级别)"""
    database_url = os.getenv(
        "TEST_DATABASE_URL",
        "mysql+pymysql://root:Wxwy.2025@#@localhost:3306/mcp_test_db"
    )
    
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=False  # 测试时不输出SQL
    )
    
    yield engine
    
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine) -> Generator[Session, None, None]:
    """创建数据库会话 (function级别 - 每个测试独立)"""
    SessionLocal = sessionmaker(bind=db_engine)
    session = SessionLocal()
    
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@pytest.fixture(scope="function")
def redis_client():
    """创建Redis客户端 (function级别)"""
    from src.mcp_core.services.redis_client import RedisClient
    
    client = RedisClient(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        db=1  # 使用db=1用于测试
    )
    
    yield client
    
    # 清理测试数据
    client.redis.flushdb()


@pytest.fixture(scope="function")
def memory_service(db_session):
    """创建记忆服务实例 (function级别)"""
    from src.mcp_core.services.memory_service import MemoryService
    
    service = MemoryService(db=db_session)
    
    yield service


@pytest.fixture(scope="function")
def project_context_service(db_session):
    """创建项目上下文服务实例 (function级别)"""
    from src.mcp_core.services.project_context_service import ProjectContextService
    
    service = ProjectContextService(db=db_session)
    
    yield service


@pytest.fixture
def sample_project_id() -> str:
    """提供测试项目ID"""
    return "test-project-123"


@pytest.fixture
def sample_memory_data() -> dict:
    """提供测试记忆数据"""
    return {
        "project_id": "test-project-123",
        "content": "历史时间轴项目使用React和D3.js开发",
        "memory_level": "long_term",
        "category": "technical",
        "confidence": 0.8
    }


@pytest.fixture
def sample_session_data() -> dict:
    """提供测试会话数据"""
    return {
        "project_id": "test-project-123",
        "session_name": "测试会话",
        "description": "这是一个测试会话"
    }


# Marker helpers
def pytest_configure(config):
    """配置pytest markers"""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "db: Tests requiring database")
    config.addinivalue_line("markers", "redis: Tests requiring Redis")
    config.addinivalue_line("markers", "milvus: Tests requiring Milvus")
    config.addinivalue_line("markers", "ai: Tests requiring AI service")
    config.addinivalue_line("markers", "enterprise: Enterprise feature tests")

"""测试配置和fixtures"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.mcp_core.models.database import Base


@pytest.fixture(scope="session")
def test_db_engine():
    """测试数据库引擎"""
    # 使用内存SQLite数据库
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def db_session(test_db_engine):
    """数据库会话(每个测试函数后回滚)"""
    connection = test_db_engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


# Pytest markers
def pytest_configure(config):
    """注册自定义markers"""
    config.addinivalue_line(
        "markers", "integration: 集成测试(需要真实数据库)"
    )
    config.addinivalue_line(
        "markers", "slow: 慢速测试"
    )
    config.addinivalue_line(
        "markers", "performance: 性能测试"
    )

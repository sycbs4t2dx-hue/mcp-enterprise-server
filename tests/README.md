# MCP Enterprise Server - 测试框架

本目录包含MCP企业级服务器的完整测试套件。

---

## 📁 目录结构

```
tests/
├── README.md                    # 本文档
├── conftest.py                  # Pytest配置和Fixtures
├── test_memory_service.py       # 记忆服务测试
├── test_project_context_service.py  # 项目上下文服务测试 (待添加)
├── test_code_knowledge_service.py   # 代码知识服务测试 (待添加)
├── test_ai_service.py           # AI服务测试 (待添加)
├── test_quality_service.py      # 质量服务测试 (待添加)
└── integration/                 # 集成测试 (待添加)
    ├── test_end_to_end.py
    └── test_mcp_tools.py
```

---

## 🚀 快速开始

### 1. 安装测试依赖

```bash
pip install -r requirements-dev.txt
```

### 2. 运行所有测试

```bash
pytest tests/ -v
```

### 3. 运行特定测试

```bash
# 运行单个测试文件
pytest tests/test_memory_service.py -v

# 运行特定测试类
pytest tests/test_memory_service.py::TestMemoryService -v

# 运行特定测试方法
pytest tests/test_memory_service.py::TestMemoryService::test_extract_keywords_chinese -v
```

---

## 🏷️ 测试标记 (Markers)

使用markers来选择性运行测试:

```bash
# 只运行单元测试
pytest tests/ -m unit

# 只运行集成测试
pytest tests/ -m integration

# 跳过慢速测试
pytest tests/ -m "not slow"

# 只运行数据库相关测试
pytest tests/ -m db

# 只运行Redis相关测试
pytest tests/ -m redis

# 只运行AI服务测试
pytest tests/ -m ai
```

**可用markers**:
- `unit` - 单元测试
- `integration` - 集成测试
- `slow` - 慢速测试 (>1秒)
- `db` - 需要数据库
- `redis` - 需要Redis
- `milvus` - 需要Milvus
- `ai` - 需要AI服务
- `enterprise` - 企业功能测试

---

## 📊 测试覆盖率

### 生成覆盖率报告

```bash
# HTML报告
pytest tests/ --cov=src/mcp_core --cov-report=html
open htmlcov/index.html

# 终端报告
pytest tests/ --cov=src/mcp_core --cov-report=term-missing

# XML报告 (用于CI/CD)
pytest tests/ --cov=src/mcp_core --cov-report=xml
```

### 覆盖率目标

- **总体覆盖率**: >80%
- **核心服务**: >90%
- **工具类**: >70%
- **配置文件**: >60%

---

## 🧪 测试类型

### 1. 单元测试 (Unit Tests)

测试单个函数或方法的行为。

**特点**:
- 快速执行 (<100ms)
- 不依赖外部服务
- 使用Mock/Stub

**示例**:
```python
@pytest.mark.unit
def test_extract_keywords_chinese(self, memory_service):
    """测试中文关键词提取"""
    text = "历史时间轴项目使用React和D3.js开发"
    keywords = memory_service._extract_keywords(text)
    
    assert "历史" in keywords
    assert "时间轴" in keywords
```

### 2. 集成测试 (Integration Tests)

测试多个组件协同工作。

**特点**:
- 较慢执行 (100ms-1s)
- 依赖真实服务 (数据库、Redis、Milvus)
- 测试完整工作流

**示例**:
```python
@pytest.mark.integration
@pytest.mark.db
@pytest.mark.redis
def test_full_memory_workflow(self, memory_service):
    """测试完整的记忆工作流"""
    # 存储 -> 检索 -> 验证
    pass
```

### 3. 端到端测试 (E2E Tests)

测试完整的用户场景。

**特点**:
- 最慢执行 (>1s)
- 依赖所有服务
- 模拟真实用户操作

---

## 🔧 Fixtures说明

### 数据库Fixtures

```python
# session级别 - 整个测试会话共享
db_engine  # 数据库引擎

# function级别 - 每个测试独立
db_session  # 数据库会话
```

### 服务Fixtures

```python
memory_service            # 记忆服务
project_context_service   # 项目上下文服务
redis_client             # Redis客户端
```

### 数据Fixtures

```python
sample_project_id        # 测试项目ID
sample_memory_data       # 测试记忆数据
sample_session_data      # 测试会话数据
```

---

## 📝 编写测试指南

### 测试文件命名

```
test_<模块名>.py
```

### 测试类命名

```python
class Test<功能名>:
    """功能描述"""
```

### 测试方法命名

```python
def test_<功能>_<场景>(self, fixtures):
    """测试描述"""
```

**示例**:
```python
class TestMemoryService:
    """记忆服务测试"""
    
    def test_store_memory_success(self, memory_service):
        """测试存储记忆成功场景"""
        pass
    
    def test_store_memory_invalid_input(self, memory_service):
        """测试存储记忆失败场景 - 无效输入"""
        pass
```

### 测试结构 (AAA模式)

```python
def test_example(self):
    # Arrange - 准备测试数据
    project_id = "test-project"
    content = "测试内容"
    
    # Act - 执行操作
    result = service.do_something(project_id, content)
    
    # Assert - 验证结果
    assert result["success"] is True
    assert result["data"] is not None
```

### 测试边界条件

```python
def test_edge_cases(self):
    # 空值
    with pytest.raises(ValueError):
        service.method("")
    
    # None
    with pytest.raises(ValueError):
        service.method(None)
    
    # 极大值
    result = service.method("x" * 10000)
    assert result is not None
```

---

## 🐛 调试测试

### 在测试中添加断点

```python
def test_debug(self):
    import ipdb; ipdb.set_trace()  # 断点
    result = service.method()
```

### 显示print输出

```bash
pytest tests/ -v -s
```

### 只运行失败的测试

```bash
pytest tests/ --lf  # last failed
pytest tests/ --ff  # failed first
```

### 详细输出

```bash
pytest tests/ -vv  # 更详细
pytest tests/ -vvv  # 最详细
```

---

## 📈 持续集成 (CI)

### GitHub Actions配置

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - run: pip install -r requirements.txt -r requirements-dev.txt
      - run: pytest tests/ --cov=src --cov-report=xml
      - uses: codecov/codecov-action@v3
```

---

## ✅ 测试清单

编写新功能时,确保包含以下测试:

- [ ] **成功场景** - 正常输入,正常输出
- [ ] **失败场景** - 错误输入,异常处理
- [ ] **边界条件** - 空值、None、极值
- [ ] **并发场景** - 多线程/多进程 (如适用)
- [ ] **性能测试** - 响应时间 (如适用)
- [ ] **集成测试** - 与其他服务交互

---

## 📚 参考资源

- [Pytest文档](https://docs.pytest.org/)
- [Pytest-cov文档](https://pytest-cov.readthedocs.io/)
- [Testing Best Practices](https://docs.python-guide.org/writing/tests/)

---

**最后更新**: 2025-11-19
**测试框架版本**: pytest 7.4+
**当前覆盖率**: ~30% (目标: >80%)

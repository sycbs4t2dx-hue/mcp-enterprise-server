# 测试覆盖率提升计划

**日期**: 2025-11-19  
**当前覆盖率**: ~30%  
**目标覆盖率**: >80%  
**状态**: 进行中

---

## 📊 当前状态

### 已有测试

1. **test_memory_retrieval.py** - 记忆检索功能测试 (端到端)
2. **test_end_to_end.py** - 端到端测试
3. **tests/test_memory_service.py** - 记忆服务单元测试 (11个测试)

### 覆盖情况

| 服务模块 | 测试状态 | 优先级 |
|---------|:-------:|:-----:|
| memory_service.py | ✅ 部分 (11个测试) | P1 |
| project_context_service.py | ❌ 无 | P1 |
| code_knowledge_service.py | ❌ 无 | P1 |
| ai_understanding_service.py | ❌ 无 | P2 |
| quality_guardian_service.py | ❌ 无 | P2 |
| redis_client.py | ❌ 无 | P1 |
| vector_db.py | ❌ 无 | P1 |
| embedding_service.py | ❌ 无 | P2 |
| token_service.py | ❌ 无 | P2 |
| config_manager.py | ❌ 无 | P1 |

---

## 🎯 测试计划

### Phase 1: 核心基础服务 (P1 - 本周)

#### 1.1 Redis客户端测试
**文件**: `tests/test_redis_client.py`

**测试用例**:
```python
- test_connection_success
- test_get_set_value
- test_delete_value
- test_exists_key
- test_expire_key
- test_list_operations (lpush, rpush, lpop, rpop)
- test_hash_operations (hset, hget, hdel)
- test_connection_error_handling
```

**覆盖率目标**: >85%

#### 1.2 项目上下文服务测试
**文件**: `tests/test_project_context_service.py`

**测试用例**:
```python
- test_create_session
- test_get_session
- test_update_session
- test_list_sessions
- test_create_todo
- test_update_todo
- test_complete_todo
- test_create_design_decision
- test_create_note
- test_session_lifecycle
```

**覆盖率目标**: >80%

#### 1.3 配置管理器测试
**文件**: `tests/test_config_manager.py`

**测试用例**:
```python
- test_load_config_success
- test_load_config_not_found
- test_env_variable_substitution
- test_validate_config
- test_get_database_url
- test_get_server_config
- test_get_ai_config
```

**覆盖率目标**: >90%

#### 1.4 向量数据库测试
**文件**: `tests/test_vector_db.py`

**测试用例**:
```python
- test_connection_success
- test_create_collection
- test_insert_vectors
- test_search_vectors
- test_delete_vectors
- test_collection_exists
- test_get_collection_stats
```

**覆盖率目标**: >80%

### Phase 2: 业务服务 (P1-P2 - 下周)

#### 2.1 代码知识服务测试
**文件**: `tests/test_code_knowledge_service.py`

**测试用例**:
```python
- test_add_code_entity
- test_query_code_entity
- test_add_relationship
- test_query_relationships
- test_dependency_analysis
- test_impact_analysis
```

**覆盖率目标**: >75%

#### 2.2 AI理解服务测试
**文件**: `tests/test_ai_understanding_service.py`

**测试用例**:
```python
- test_understand_code_snippet
- test_generate_summary
- test_suggest_refactoring
- test_explain_error
- test_ai_not_enabled
- test_api_error_handling
```

**覆盖率目标**: >75%

#### 2.3 质量守护服务测试
**文件**: `tests/test_quality_guardian_service.py`

**测试用例**:
```python
- test_code_smell_detection
- test_security_scan
- test_performance_analysis
- test_tech_debt_assessment
- test_quality_report
```

**覆盖率目标**: >75%

### Phase 3: 辅助服务 (P2 - 后续)

#### 3.1 Token服务测试
#### 3.2 Embedding服务测试
#### 3.3 压缩服务测试

---

## 📝 测试编写规范

### 命名规范

```python
# 测试文件
test_<模块名>.py

# 测试类
class Test<服务名>:
    """服务名测试"""

# 测试方法
def test_<功能>_<场景>(self):
    """测试:<功能> - <场景>"""
```

### AAA模式

```python
def test_example(self):
    # Arrange - 准备数据
    project_id = "test-project"
    
    # Act - 执行操作
    result = service.method(project_id)
    
    # Assert - 验证结果
    assert result is not None
```

### Mock使用

```python
from unittest.mock import Mock, patch

@patch('src.mcp_core.services.redis_client.redis.Redis')
def test_with_mock(self, mock_redis):
    mock_redis.return_value.get.return_value = b"test"
    # 测试逻辑
```

---

## 🔧 执行计划

### Week 1 (当前周)

**Day 1-2**: Phase 1.1-1.2
- ✅ Redis客户端测试
- ✅ 项目上下文服务测试

**Day 3-4**: Phase 1.3-1.4
- ✅ 配置管理器测试
- ✅ 向量数据库测试

**Day 5**: Phase 2.1
- ✅ 代码知识服务测试

### Week 2

**Day 1-2**: Phase 2.2-2.3
- AI理解服务测试
- 质量守护服务测试

**Day 3-5**: Phase 3 + 覆盖率优化
- Token/Embedding/压缩服务测试
- 查漏补缺
- 达成>80%覆盖率目标

---

## 📊 进度跟踪

### Phase 1 进度

| 任务 | 状态 | 测试数 | 覆盖率 |
|-----|:---:|:-----:|:-----:|
| Redis客户端 | 🔄 进行中 | 0/8 | 0% |
| 项目上下文服务 | ⏳ 待开始 | 0/10 | 0% |
| 配置管理器 | ⏳ 待开始 | 0/7 | 0% |
| 向量数据库 | ⏳ 待开始 | 0/7 | 0% |

### 总体进度

- **已完成测试**: 11个
- **计划新增测试**: ~60个
- **预计总测试数**: ~70个
- **当前覆盖率**: ~30%
- **预计覆盖率**: >80%

---

## ✅ 验收标准

### 测试质量

- ✅ 所有测试通过
- ✅ 无测试警告
- ✅ Mock使用合理
- ✅ 测试独立性 (可单独运行)
- ✅ 测试速度 (<5秒/文件)

### 覆盖率

- ✅ 总覆盖率 >80%
- ✅ 核心服务覆盖率 >85%
- ✅ 关键方法100%覆盖

### 文档

- ✅ 每个测试有清晰的Docstring
- ✅ 复杂测试有注释说明
- ✅ README更新测试说明

---

## 🚀 快速命令

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定测试文件
pytest tests/test_redis_client.py -v

# 生成覆盖率报告
pytest tests/ --cov=src/mcp_core --cov-report=html
open htmlcov/index.html

# 只运行单元测试
pytest tests/ -m unit

# 运行失败的测试
pytest tests/ --lf
```

---

**创建时间**: 2025-11-19  
**负责人**: Claude Code AI Assistant  
**预计完成**: 2周内  
**状态**: 🔄 Phase 1.1 进行中

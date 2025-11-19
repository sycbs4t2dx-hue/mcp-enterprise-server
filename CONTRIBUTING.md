# Contributing to MCP Enterprise Server

感谢您对MCP企业级服务器项目的关注!我们欢迎所有形式的贡献。

---

## 🎯 贡献方式

### 1. 报告Bug

如果您发现了Bug,请创建Issue并包含以下信息:

- **问题描述**: 清晰描述遇到的问题
- **复现步骤**: 详细的复现步骤
- **期望行为**: 您期望发生什么
- **实际行为**: 实际发生了什么
- **环境信息**:
  - Python版本 (`python3 --version`)
  - 操作系统 (macOS/Linux/Windows)
  - MCP服务器版本
  - 相关日志 (`tail -50 enterprise_server.log`)

**示例**:
```markdown
**环境**: Python 3.9.18, macOS 14.0, MCP v2.0.0
**问题**: 中文记忆检索返回空结果
**复现**:
1. 存储中文记忆: `store_memory("历史时间轴项目")`
2. 检索记忆: `retrieve_memory("历史")`
3. 返回: count=0, memories=[]

**期望**: 应该返回匹配的记忆
**日志**: [附上相关日志]
```

### 2. 提出新功能

如果您有功能建议,请创建Issue并包含:

- **功能描述**: 您希望添加什么功能
- **使用场景**: 这个功能解决什么问题
- **实现思路**: (可选) 您认为如何实现
- **优先级**: 低/中/高

### 3. 提交代码

我们欢迎Pull Request! 请遵循以下流程:

#### 3.1 开发设置

```bash
# 1. Fork项目到您的GitHub账户

# 2. 克隆您的Fork
git clone https://github.com/YOUR_USERNAME/mcp-enterprise-server.git
cd mcp-enterprise-server

# 3. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 4. 安装依赖
pip install -r requirements.txt
pip install -r requirements-dev.txt  # 开发依赖

# 5. 启动Docker服务
./start_services.sh

# 6. 运行测试
pytest tests/ -v
```

#### 3.2 创建分支

```bash
# 从main分支创建功能分支
git checkout -b feature/your-feature-name

# 或者修复分支
git checkout -b fix/bug-description
```

**分支命名规范**:
- `feature/描述` - 新功能
- `fix/描述` - Bug修复
- `docs/描述` - 文档更新
- `refactor/描述` - 代码重构
- `test/描述` - 测试相关

#### 3.3 代码规范

##### Python代码规范

遵循 **PEP 8** 规范:

```python
# ✅ 好的示例
def retrieve_memory(
    project_id: str,
    query: str,
    top_k: int = 5
) -> Dict[str, Any]:
    """检索项目记忆

    Args:
        project_id: 项目ID
        query: 查询字符串
        top_k: 返回结果数量

    Returns:
        包含记忆列表的字典

    Raises:
        ValueError: 如果project_id为空
    """
    if not project_id:
        raise ValueError("project_id不能为空")

    # 实现逻辑...
    return {"memories": [], "count": 0}


# ❌ 避免的写法
def retrieve_memory(project_id,query,top_k=5):  # 缺少类型提示
    if not project_id:
        return None  # 应该抛出异常
    return {"memories":[],"count":0}  # 格式不规范
```

**关键要求**:
- ✅ 使用类型提示 (Type Hints)
- ✅ 编写Docstring (Google风格)
- ✅ 每行不超过100字符
- ✅ 使用4空格缩进 (不使用Tab)
- ✅ 导入顺序: 标准库 → 第三方库 → 本地模块
- ✅ 函数/方法名使用`snake_case`
- ✅ 类名使用`PascalCase`
- ✅ 常量使用`UPPER_CASE`

##### 代码检查

在提交前运行:

```bash
# 格式检查
black src/ tests/ --check --line-length 100

# 自动格式化
black src/ tests/ --line-length 100

# Lint检查
flake8 src/ tests/ --max-line-length 100

# 类型检查
mypy src/ --strict
```

#### 3.4 提交规范

遵循 **Conventional Commits** 规范:

**格式**:
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Type类型**:
- `feat` - 新功能
- `fix` - Bug修复
- `docs` - 文档更新
- `style` - 代码格式 (不影响功能)
- `refactor` - 重构
- `test` - 测试相关
- `chore` - 构建/工具/依赖更新
- `perf` - 性能优化

**示例**:

```bash
# 新功能
git commit -m "feat(memory): 添加中文分词支持

- 集成jieba分词库
- 改进_extract_keywords函数
- 支持中英文混合查询

Closes #123"

# Bug修复
git commit -m "fix(server): 修复retrieve_memory返回值类型错误

- 处理Dict返回值
- 添加向后兼容逻辑
- 更新测试用例

Fixes #456"

# 文档更新
git commit -m "docs: 更新README快速开始指南"

# 重构
git commit -m "refactor(database): 统一Base元数据架构

- 创建src/mcp_core/models/base.py
- 重构3个服务文件
- 解决跨服务外键问题"
```

#### 3.5 编写测试

**所有新功能必须包含测试!**

```python
# tests/test_memory_service.py
import pytest
from src.mcp_core.services.memory_service import MemoryService


class TestMemoryService:
    """记忆服务测试"""

    @pytest.fixture
    def memory_service(self, db_session):
        """创建记忆服务实例"""
        return MemoryService(db=db_session)

    def test_extract_keywords_chinese(self, memory_service):
        """测试中文关键词提取"""
        text = "历史时间轴项目使用React和D3.js开发"
        keywords = memory_service._extract_keywords(text)

        assert "历史" in keywords
        assert "时间轴" in keywords
        assert "项目" in keywords
        assert "react" in keywords
        assert "d3" in keywords

    def test_retrieve_memory_success(self, memory_service):
        """测试记忆检索成功场景"""
        # 先存储记忆
        memory_service.store_memory(
            project_id="test-project",
            content="历史时间轴项目",
            memory_level="long_term"
        )

        # 检索记忆
        result = memory_service.retrieve_memory(
            project_id="test-project",
            query="历史",
            top_k=5
        )

        assert result["count"] > 0
        assert len(result["memories"]) > 0
        assert result["memories"][0]["content"] == "历史时间轴项目"

    def test_retrieve_memory_empty_query(self, memory_service):
        """测试空查询"""
        with pytest.raises(ValueError, match="query不能为空"):
            memory_service.retrieve_memory(
                project_id="test-project",
                query="",
                top_k=5
            )
```

**测试要求**:
- ✅ 单元测试覆盖率 >80%
- ✅ 测试成功场景和失败场景
- ✅ 测试边界条件
- ✅ 使用有意义的测试名称
- ✅ 使用fixtures管理测试数据

**运行测试**:
```bash
# 运行所有测试
pytest tests/ -v

# 运行特定文件
pytest tests/test_memory_service.py -v

# 生成覆盖率报告
pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html
```

#### 3.6 提交Pull Request

```bash
# 1. 推送分支到您的Fork
git push origin feature/your-feature-name

# 2. 在GitHub上创建Pull Request

# 3. 填写PR描述模板
```

**PR描述模板**:

```markdown
## 摘要
简要描述此PR做了什么 (1-2句话)

## 修改内容
- [ ] 添加了XXX功能
- [ ] 修复了XXX问题
- [ ] 更新了XXX文档

## 测试
- [ ] 单元测试通过
- [ ] 集成测试通过
- [ ] 手动测试通过

## 测试用例
描述如何测试此PR:
1. 启动服务器
2. 执行XXX操作
3. 验证XXX结果

## 相关Issue
Closes #123
Fixes #456

## 截图/日志
(如果适用,添加截图或日志)

## Checklist
- [ ] 代码遵循项目规范
- [ ] 已添加测试
- [ ] 测试全部通过
- [ ] 已更新文档
- [ ] Commit遵循规范
- [ ] 无冲突需要解决
```

---

## 🔧 开发工具

### 推荐IDE配置

**VSCode** (`.vscode/settings.json`):
```json
{
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.linting.mypyEnabled": true,
  "python.formatting.provider": "black",
  "python.formatting.blackArgs": ["--line-length", "100"],
  "editor.formatOnSave": true,
  "editor.rulers": [100]
}
```

**PyCharm**:
- 启用PEP 8检查
- 配置Black格式化
- 启用Type Checker

### 有用的命令

```bash
# 查看服务器状态
ps aux | grep mcp_server_enterprise

# 查看日志
tail -f enterprise_server.log

# 重启服务器
./restart_server_complete.sh

# 检查数据库Schema
docker exec mcp-mysql mysql -uroot -p'Wxwy.2025@#' mcp_db -e "DESCRIBE project_sessions;"

# 修复数据库Schema
docker exec -i mcp-mysql mysql -uroot -p'Wxwy.2025@#' < scripts/fix_all_schemas.sql
```

---

## 🏗️ 架构指南

### 添加新的MCP工具

**1. 定义工具** (`mcp_server_unified.py`):

```python
def get_all_tools(self) -> List[Dict[str, Any]]:
    tools = [
        # ... 现有工具
        {
            "name": "your_new_tool",
            "description": "工具描述 (简洁明了)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "param1": {
                        "type": "string",
                        "description": "参数1描述"
                    },
                    "param2": {
                        "type": "integer",
                        "description": "参数2描述",
                        "default": 10
                    }
                },
                "required": ["param1"]
            }
        }
    ]
    return tools
```

**2. 实现工具** (`mcp_server_unified.py`):

```python
def _handle_tools_call(self, method: str, params: Dict) -> Dict:
    tool_name = params.get("name")
    args = params.get("arguments", {})

    # ... 现有工具处理

    elif tool_name == "your_new_tool":
        # 参数验证
        param1 = args.get("param1")
        if not param1:
            raise ValueError("param1不能为空")

        # 调用服务
        result = self.your_service.your_method(
            param1=param1,
            param2=args.get("param2", 10)
        )

        return {
            "success": True,
            "data": result
        }
```

**3. 添加测试** (`tests/test_tools.py`):

```python
def test_your_new_tool(mcp_client):
    """测试your_new_tool工具"""
    response = mcp_client.call_tool(
        "your_new_tool",
        {"param1": "test_value", "param2": 20}
    )

    assert response["success"] is True
    assert "data" in response
```

**4. 更新文档** (`README.md` + `docs/`):

添加工具说明到README.md的工具列表中。

### 添加新的服务

**1. 创建服务文件** (`src/mcp_core/services/your_service.py`):

```python
from typing import Dict, Any
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)


class YourService:
    """您的服务描述"""

    def __init__(self, db: Session):
        """初始化服务

        Args:
            db: 数据库会话
        """
        self.db = db
        logger.info("YourService初始化完成")

    def your_method(self, param1: str, param2: int = 10) -> Dict[str, Any]:
        """方法描述

        Args:
            param1: 参数1描述
            param2: 参数2描述

        Returns:
            结果字典

        Raises:
            ValueError: 参数验证失败
        """
        try:
            # 实现逻辑
            result = {"status": "success", "param1": param1, "param2": param2}

            logger.info("操作成功", extra={"param1": param1})
            return result

        except Exception as e:
            logger.error(f"操作失败: {e}", exc_info=True)
            raise
```

**2. 注册服务** (`mcp_server_unified.py`):

```python
from src.mcp_core.services.your_service import YourService

class MCPServer:
    def _init_services(self):
        # ... 现有服务初始化

        # 初始化您的服务
        self.your_service = YourService(db=self.db)
```

---

## 📝 文档规范

### Docstring格式

使用 **Google风格**:

```python
def function_name(param1: str, param2: int = 10) -> Dict[str, Any]:
    """简短描述 (一句话)

    详细描述 (可选):
    这里可以写更详细的说明,包括:
    - 功能细节
    - 使用场景
    - 注意事项

    Args:
        param1: 参数1的描述
        param2: 参数2的描述. 默认为10.

    Returns:
        返回值的描述. 例如:
        {
            "status": "success",
            "data": {...}
        }

    Raises:
        ValueError: 如果param1为空
        RuntimeError: 如果操作失败

    Example:
        >>> result = function_name("test", 20)
        >>> print(result["status"])
        success
    """
```

### README更新

如果您的PR影响用户使用方式,请更新README.md:

- 新功能: 添加到"核心功能"章节
- 配置变更: 更新"配置"章节
- 新命令: 添加到"常用命令"章节
- Bug修复: 如果重要,添加到"最近更新"章节

---

## 🤝 代码审查

### 我们关注的点

1. **功能正确性**
   - 代码是否实现了预期功能
   - 是否处理了边界条件
   - 是否有潜在的Bug

2. **代码质量**
   - 是否遵循代码规范
   - 是否有足够的注释
   - 是否易于理解和维护

3. **测试覆盖**
   - 是否有测试
   - 测试是否充分
   - 测试是否有意义

4. **性能影响**
   - 是否有性能问题
   - 是否需要优化
   - 是否影响现有功能

5. **安全性**
   - 是否有安全漏洞
   - 是否处理了敏感数据
   - 是否验证了输入

### 响应审查意见

- ✅ 积极回应审查意见
- ✅ 如有不同意见,礼貌讨论
- ✅ 及时更新代码
- ✅ 解决所有评论后请求再次审查

---

## 🎓 学习资源

### 项目相关

- [MCP协议规范](https://spec.modelcontextprotocol.io/) - Model Context Protocol官方文档
- [SQLAlchemy文档](https://docs.sqlalchemy.org/) - ORM使用指南
- [aiohttp文档](https://docs.aiohttp.org/) - 异步HTTP框架

### Python最佳实践

- [PEP 8](https://pep8.org/) - Python代码风格指南
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [Effective Python](https://effectivepython.com/) - Python最佳实践

### 开发工具

- [pytest文档](https://docs.pytest.org/) - 测试框架
- [Black文档](https://black.readthedocs.io/) - 代码格式化
- [mypy文档](https://mypy.readthedocs.io/) - 类型检查

---

## 🙏 行为准则

### 我们的承诺

为了营造开放和友好的环境,我们承诺:

- ✅ 尊重所有贡献者
- ✅ 接受建设性批评
- ✅ 关注对社区最有利的事情
- ✅ 对其他社区成员表现出同理心

### 不可接受的行为

- ❌ 使用性别化语言或意象
- ❌ 人身攻击或侮辱性评论
- ❌ 公开或私下骚扰
- ❌ 未经许可发布他人私人信息
- ❌ 其他不道德或不专业的行为

---

## 📞 获得帮助

如果您需要帮助:

1. **查看文档**: [docs/INDEX.md](docs/INDEX.md)
2. **搜索Issue**: 看看是否有类似问题
3. **创建Issue**: 详细描述您的问题
4. **讨论功能**: 在Issue中讨论新功能想法

---

## ✅ 贡献清单

提交PR前,请确认:

- [ ] 代码遵循PEP 8规范
- [ ] 已添加类型提示
- [ ] 已编写Docstring
- [ ] 已添加单元测试
- [ ] 测试覆盖率 >80%
- [ ] 所有测试通过
- [ ] Commit遵循Conventional Commits
- [ ] 已更新相关文档
- [ ] 已运行black格式化
- [ ] 已运行flake8检查
- [ ] PR描述清晰完整

---

感谢您的贡献! 🎉

**维护团队**: Claude Code AI Assistant
**最后更新**: 2025-11-19
**项目版本**: v2.0.0

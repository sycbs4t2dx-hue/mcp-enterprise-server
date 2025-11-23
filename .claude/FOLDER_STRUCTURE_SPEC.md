# MCP项目文件夹结构规范

**版本**: 1.0
**生效日期**: 2025-11-20
**目标**: 标准化项目结构，提高代码可维护性

---

## 📁 核心目录结构

```
/MCP项目根目录
├── src/                      # 源代码目录
│   └── mcp_core/            # MCP核心模块
│       ├── models/          # 数据模型定义
│       │   ├── base.py     # 统一Base定义 (必须)
│       │   └── tables.py   # 数据表模型
│       ├── services/        # 业务服务层
│       ├── analyzers/       # 代码分析器
│       └── utils/           # 工具函数
│
├── mcp-admin-ui/            # 前端管理界面
│   ├── src/                # 前端源码
│   │   ├── components/     # React组件
│   │   ├── pages/         # 页面组件
│   │   ├── services/      # API服务
│   │   └── utils/         # 工具函数
│   └── dist/              # 构建产物
│
├── scripts/                 # 运维脚本
│   ├── download_*.py       # 下载脚本
│   ├── fix_*.sql          # 数据库修复
│   └── sync_*.sql         # 数据同步
│
├── config/                  # 配置文件
│   ├── config.yaml        # 主配置
│   └── *.yaml             # 其他配置
│
├── models/                  # AI模型文件
│   ├── codebert-base/     # CodeBERT模型
│   └── embeddings/        # 嵌入模型
│
├── docs/                    # 核心文档 (精简!)
│   ├── API.md            # API文档
│   ├── ARCHITECTURE.md   # 架构设计
│   └── DEPLOYMENT.md     # 部署指南
│
├── .claude/                 # Claude专用目录
│   ├── DOC_GENERATION_RULES.md    # 文档规范
│   ├── FOLDER_STRUCTURE_SPEC.md   # 本文档
│   └── templates/         # 模板文件
│
├── .archived/              # 归档目录
│   ├── docs/             # 旧文档
│   ├── scripts/          # 废弃脚本
│   └── servers/          # 旧服务器
│
├── tests/                  # 测试文件
│   ├── unit/            # 单元测试
│   ├── integration/     # 集成测试
│   ├── e2e/            # 端到端测试
│   └── conftest.py     # pytest配置
│
├── logs/                   # 日志文件 (gitignore)
├── temp/                   # 临时文件 (gitignore)
└── cache/                  # 缓存文件 (gitignore)
```

---

## 🚫 禁止创建的目录

### 1. 日期相关目录
```
❌ 不要: /2025-11-20/
❌ 不要: /fixes/2025-11-20/
❌ 不要: /backup/20251120/

✅ 改为: 使用版本控制(Git)管理历史
```

### 2. 版本迭代目录
```
❌ 不要: /v1/, /v2/, /v3/
❌ 不要: /old/, /new/, /latest/

✅ 改为: 使用Git标签和分支
```

### 3. 个人目录
```
❌ 不要: /claude/, /user/, /admin/
❌ 不要: /tmp/, /temp_fix/

✅ 改为: 使用标准化目录
```

---

## ✅ 文件放置规则

### 1. Python模块
```python
# 核心业务逻辑
src/mcp_core/*.py

# 数据模型
src/mcp_core/models/*.py

# 服务层
src/mcp_core/services/*.py

# 分析器
src/mcp_core/analyzers/*.py
```

### 2. 配置文件
```yaml
# 主配置
config/config.yaml

# 环境配置
config/env.*.yaml

# 不要散落在根目录
❌ /config.yaml
✅ /config/config.yaml
```

### 3. 脚本文件
```bash
# 运维脚本
scripts/fix_*.sql      # 修复脚本
scripts/sync_*.sql     # 同步脚本
scripts/download_*.py  # 下载脚本

# 启动脚本保留在根目录
/start_*.sh           # 便于快速启动
/restart_*.sh         # 重启脚本
```

### 4. 测试文件
```python
# 单元测试 - 测试单个函数/类
tests/unit/test_*.py

# 集成测试 - 测试模块间交互
tests/integration/test_*.py

# 端到端测试 - 测试完整流程
tests/e2e/test_*.py

# 性能测试
tests/performance/test_*.py

# 不要在源码目录创建测试
❌ src/mcp_core/test_*.py
✅ tests/unit/test_*.py

# 不要在根目录创建测试
❌ /test_*.py
✅ /tests/*/test_*.py
```

### 5. 测试文件分类规则
```
单元测试 (tests/unit/):
- 测试单个函数或类
- 无外部依赖
- 快速执行
- 示例: test_memory_retrieval.py

集成测试 (tests/integration/):
- 测试模块间交互
- 可能需要数据库/网络
- 中等执行时间
- 示例: test_mcp_server.py

端到端测试 (tests/e2e/):
- 测试完整用户场景
- 需要完整环境
- 较长执行时间
- 示例: test_end_to_end.py
```

---

## 📝 命名规范

### 1. 目录命名
- 使用小写字母
- 使用下划线分隔: `mcp_core`
- 避免使用连字符: ~~`mcp-core`~~ (除了前端项目)
- 简洁明确: `models`, `services`, `utils`

### 2. Python文件命名
```python
# 模块文件
code_analyzer.py      # 下划线分隔
java_analyzer.py      # 具体功能
base.py              # 基础模块

# 不要使用
❌ CodeAnalyzer.py   # 大写开头
❌ code-analyzer.py  # 连字符
❌ codeAnalyzer.py   # 驼峰命名
```

### 3. 配置文件命名
```yaml
config.yaml          # 主配置
env.prod.yaml       # 环境配置
database.yaml       # 特定配置
```

### 4. 脚本命名
```bash
# 动作_目标_日期(可选).扩展名
fix_schema.sql
sync_database.sql
download_models.py

# 避免
❌ fix.sql          # 太模糊
❌ FIXBUG.sql       # 全大写
❌ fix-bug.sql      # 连字符
```

---

## 🔄 文件迁移规则

### 何时迁移文件

1. **临时修复脚本** → 执行后移到 `.archived/`
2. **过时文档** → 移到 `.archived/docs/`
3. **废弃代码** → 删除或移到 `.archived/`
4. **测试脚本** → 移到 `tests/`

### 迁移示例
```bash
# 临时修复完成后
mv scripts/fix_specific_bug_2025.sql .archived/scripts/

# 文档过时后
mv docs/OLD_API.md .archived/docs/

# 保留30天后可删除
find .archived -mtime +30 -type f -delete
```

---

## 🎯 服务器文件规范

### 活跃服务器 (根目录)
```python
mcp_server_unified.py      # 统一服务器
mcp_server_enterprise.py   # 企业级服务器
```

### 废弃服务器 (归档)
```bash
.archived/servers/
├── mcp_server.py         # 基础版本
├── mcp_server_claude.py  # Claude版本
├── mcp_server_http.py    # HTTP版本
└── ...
```

---

## 🗂️ 特殊目录说明

### `.claude/` 目录
- **用途**: Claude AI专用配置和规范
- **内容**: 生成规则、模板、指令
- **权限**: 只有Claude相关文件

### `.archived/` 目录
- **用途**: 存放所有归档内容
- **策略**: 只进不出，定期清理
- **结构**: 镜像原始目录结构

### `models/` 目录
- **用途**: AI模型文件存储
- **注意**: 大文件，应在.gitignore中
- **结构**: 按模型名称组织

---

## 📊 当前问题和建议

### 问题诊断
```bash
# 检查冗余文件
find . -name "*.md" | wc -l  # 845个文档
find . -name "*_fix_*.sql" | wc -l  # 过多修复脚本
find . -name "test_*.py" | grep -v "^./tests/" | wc -l  # 散落的测试
```

### 立即行动
1. **归档过时文档**: `mv docs/*_2025*.md .archived/docs/`
2. **整理修复脚本**: `mv scripts/*_fix_*_2025*.sql .archived/scripts/`
3. **统一测试位置**: 将所有测试移到 `tests/` 目录
4. **删除临时文件**: `rm -rf temp/ tmp/ cache/`

---

## 💡 黄金法则

1. **扁平优于嵌套**: 不要创建超过3层的目录结构
2. **明确优于灵活**: 每个文件都有明确的位置
3. **版本控制优于备份目录**: 使用Git而非目录管理版本
4. **归档优于删除**: 不确定的文件先归档
5. **标准化优于个性化**: 遵循Python/JavaScript社区规范
6. **测试分离原则**: 测试文件必须在tests/目录，永不在根目录或源码目录
7. **清晰分类**: 根据测试类型(unit/integration/e2e)正确分类

---

## 🚀 执行检查清单

创建新文件前，检查:

- [ ] 是否有标准目录可以放置？
- [ ] 命名是否符合规范？
- [ ] 是否会创建新的顶级目录？
- [ ] 是否属于临时文件？
- [ ] 30天后这个文件还有用吗？

如果有任何疑问，参考本规范或询问。

---

**强制执行**: 此规范立即生效，新创建的文件必须遵循
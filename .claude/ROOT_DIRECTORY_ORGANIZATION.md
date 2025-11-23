# 根目录文件组织规范

**版本**: 1.0
**生效日期**: 2025-11-22
**目标**: 保持根目录简洁专业，提高项目可读性

---

## 🎯 核心原则

### 根目录极简原则
根目录应该只包含**必要的入口文件**，其他文件应该组织到相应的子目录中。

**理想状态**: 根目录文件数量 < 20个

---

## ✅ 应该保留在根目录的文件

### 1. 项目元信息（必须）
```
README.md           # 项目说明（必须）
LICENSE             # 许可证（必须）
CHANGELOG.md        # 版本历史（推荐）
CONTRIBUTING.md     # 贡献指南（推荐）
ROADMAP.md         # 路线图（可选）
```

### 2. Python包配置（必须）
```
setup.py            # Python包安装配置
pyproject.toml      # 现代Python项目配置
requirements.txt    # 依赖列表
requirements-dev.txt # 开发依赖
```

### 3. 容器化配置（如需要）
```
Dockerfile          # Docker镜像定义
docker-compose.yml  # Docker服务编排
```

### 4. 主服务器文件（2-3个）
```
mcp_server_unified.py     # 统一服务器
mcp_server_enterprise.py  # 企业版服务器
# 注：其他服务器应移到src/servers/
```

### 5. 快速启动脚本（3-5个）
```
start_services.sh   # 启动所有服务
restart_server.sh   # 重启服务器
deploy.sh          # 部署脚本
```

### 6. Git配置
```
.gitignore         # Git忽略规则
.gitattributes     # Git属性配置
```

---

## ❌ 不应该在根目录的文件

### 1. 工具脚本
```
❌ comprehensive_fix.py
❌ fix_dependencies.py
❌ generate_graph.py
✅ 移到: scripts/
```

### 2. 配置文件
```
❌ config.yaml
❌ config_unified.yaml
❌ claude_desktop_config.json
✅ 移到: config/
```

### 3. 测试文件
```
❌ test_*.py
✅ 移到: tests/
```

### 4. 临时文件
```
❌ *.log
❌ *.tmp
❌ test_graph.json
✅ 移到: .archived/temp/ 或删除
```

### 5. 文档
```
❌ IMPLEMENTATION_*.md
❌ FIX_*.md
❌ TODO_*.md
✅ 移到: docs/ 或 .archived/docs/
```

### 6. 客户端/可视化服务器
```
❌ mcp_client_*.py
❌ visualization_server.py
✅ 移到: src/clients/ 或 src/servers/
```

---

## 📊 根目录文件数量标准

| 文件类型 | 推荐数量 | 当前状态 |
|---------|---------|---------|
| Markdown文档 | 3-5个 | 4个 ✅ |
| Python文件 | 2-4个 | 6个 ⚠️ |
| Shell脚本 | 3-5个 | 7个 ⚠️ |
| 配置文件 | 3-5个 | 6个 ⚠️ |
| **总计** | **< 20个** | **23个** ⚠️ |

---

## 🔄 整理建议

### 立即行动
1. 移动 `config_manager.py` → `src/mcp_core/`
2. 移动 `mcp_client_http.py` → `src/clients/`
3. 移动 `visualization_server.py` → `src/servers/`
4. 合并重复的shell脚本

### 目录结构优化
```
/项目根目录
├── src/              # 源代码
│   ├── mcp_core/    # 核心模块
│   ├── servers/     # 服务器集合
│   └── clients/     # 客户端集合
├── config/          # 配置文件
├── scripts/         # 工具脚本
├── tests/           # 测试文件
├── docs/            # 文档
└── .archived/       # 归档文件
```

---

## 🚫 严格禁止

1. **禁止在根目录创建临时文件**
   - 使用 `/tmp` 或 `.cache/` 目录

2. **禁止在根目录创建测试文件**
   - 所有测试必须在 `tests/` 目录

3. **禁止在根目录创建日期文件**
   - 如 `fix_2025-11-22.py`

4. **禁止在根目录堆积配置文件**
   - 统一放在 `config/` 目录

---

## ✨ 根目录整洁守则

### 每次提交前检查
```bash
# 检查根目录文件数量
ls -1 *.* | wc -l  # 应该 < 20

# 查找可疑文件
ls -1 test_* fix_* temp_* *.log *.tmp 2>/dev/null

# 如果发现，立即整理
```

### 新文件放置决策树
```
是配置文件？ → config/
是测试文件？ → tests/
是工具脚本？ → scripts/
是服务器？  → src/servers/
是客户端？  → src/clients/
是文档？    → docs/
是临时文件？ → 不要创建！
其他？      → 考虑是否真的需要在根目录
```

---

## 📈 预期效果

整理完成后：
- 根目录文件 < 20个
- 一眼看清项目结构
- 专业的第一印象
- 便于新成员理解

---

**黄金法则**: 如果不确定文件是否应该在根目录，那它就不应该在根目录。

**立即生效**: 此规范立即生效，所有新文件必须遵循。
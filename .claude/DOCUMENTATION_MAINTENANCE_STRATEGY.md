# MCP项目文档维护策略

**版本**: 1.0
**生效日期**: 2025-11-20
**目标**: 建立可持续的文档管理机制，避免文档爆炸式增长

---

## 🎯 核心策略

### 1. 文档生命周期管理

```mermaid
文档创建 → 活跃期(7天) → 评估期 → [归档/更新/删除]
```

| 阶段 | 时长 | 操作 |
|------|------|------|
| 活跃期 | 0-7天 | 正常使用 |
| 评估期 | 7-30天 | 评估价值 |
| 归档决策 | 30天 | 归档或删除 |

### 2. 文档分类管理

#### 永久文档 (保留在 /docs)
- `README.md` - 项目主文档
- `API.md` - API接口文档
- `ARCHITECTURE.md` - 系统架构
- `DEPLOYMENT.md` - 部署指南
- `CHANGELOG.md` - 版本历史

#### 临时文档 (30天后归档)
- Bug修复记录 → 代码注释
- 进度报告 → Git日志
- 会议纪要 → Issue评论
- 测试报告 → CI/CD日志

#### 禁止创建
- 每日总结文档
- 个人笔记文档
- 重复内容文档
- 版本迭代文档

---

## 📝 文档更新策略

### 增量更新原则

**不要创建新版本文档**：
```
❌ API_v1.md, API_v2.md, API_v3.md
✅ API.md (使用Git追踪历史)
```

**不要创建日期文档**：
```
❌ FIXES_2025-11-20.md
✅ 在CHANGELOG.md中添加条目
```

### 更新示例

#### 场景1: API变更
```markdown
# 不要创建 API_NEW.md
# 而是更新 docs/API.md:

## Endpoints

### /api/v2/users (Updated: 2025-11-20)
- Added pagination support
- Breaking change: removed deprecated fields
```

#### 场景2: Bug修复
```python
# 不要创建 BUG_FIX.md
# 而是在代码中注释:

def process_data(self, data):
    """处理数据

    Bug Fix 2025-11-20:
    - 修复了Position对象访问错误
    - 原因: javalang使用namedtuple而非dict
    - 影响: 解决88个Java文件分析失败
    """
    pass
```

---

## 🗄️ 归档执行流程

### 自动归档脚本

创建 `scripts/archive_docs.py`:

```python
#!/usr/bin/env python3
"""
文档自动归档工具
每周执行一次，清理过期文档
"""

import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path

def archive_old_docs():
    """归档30天前的文档"""

    archive_dir = Path(".archived/docs")
    archive_dir.mkdir(parents=True, exist_ok=True)

    # 需要检查的目录
    check_dirs = ["docs", ".", "scripts"]

    # 永久保留的文件
    keep_files = {
        "README.md", "API.md", "ARCHITECTURE.md",
        "DEPLOYMENT.md", "CHANGELOG.md", "LICENSE"
    }

    archived_count = 0
    cutoff_date = datetime.now() - timedelta(days=30)

    for dir_path in check_dirs:
        for file in Path(dir_path).glob("*.md"):
            # 跳过永久文件
            if file.name in keep_files:
                continue

            # 检查修改时间
            mtime = datetime.fromtimestamp(file.stat().st_mtime)
            if mtime < cutoff_date:
                # 归档
                archive_path = archive_dir / file.name
                shutil.move(str(file), str(archive_path))
                print(f"归档: {file} → {archive_path}")
                archived_count += 1

    print(f"✅ 归档完成: {archived_count}个文件")
    return archived_count

if __name__ == "__main__":
    archive_old_docs()
```

### 手动归档命令

```bash
# 归档所有修复文档
find docs -name "*FIX*.md" -mtime +7 -exec mv {} .archived/docs/ \;

# 归档所有日期文档
find . -name "*2025-*.md" -mtime +7 -exec mv {} .archived/docs/ \;

# 清理归档目录(90天以上)
find .archived -mtime +90 -type f -delete
```

---

## 📊 文档质量指标

### 健康指标

| 指标 | 目标值 | 当前值 | 状态 |
|------|--------|--------|------|
| 总文档数 | < 20 | 845 | ❌ 严重超标 |
| docs/目录 | < 10 | 143 | ❌ 需要清理 |
| 平均文档年龄 | < 30天 | > 60天 | ⚠️ 过时 |
| 重复率 | < 5% | > 40% | ❌ 大量重复 |

### 监控脚本

```bash
#!/bin/bash
# doc_health_check.sh

echo "=== 文档健康检查 ==="
echo ""

# 统计文档数量
total_docs=$(find . -name "*.md" -type f | wc -l)
docs_in_docs=$(find docs -name "*.md" -type f 2>/dev/null | wc -l)
archived_docs=$(find .archived -name "*.md" -type f 2>/dev/null | wc -l)

echo "📊 文档统计:"
echo "  总文档数: $total_docs"
echo "  docs/目录: $docs_in_docs"
echo "  已归档: $archived_docs"
echo ""

# 检查过期文档
old_docs=$(find docs -name "*.md" -mtime +30 -type f 2>/dev/null | wc -l)
echo "⏰ 过期文档(30天+): $old_docs"

# 健康评分
if [ $docs_in_docs -lt 10 ]; then
    echo "✅ 文档数量: 健康"
elif [ $docs_in_docs -lt 20 ]; then
    echo "⚠️  文档数量: 警告"
else
    echo "❌ 文档数量: 需要清理"
fi
```

---

## 🔄 定期维护任务

### 每日任务
- [ ] 检查新创建的文档是否符合规范
- [ ] 将修复记录转为代码注释

### 每周任务
- [ ] 运行文档健康检查
- [ ] 归档过期文档
- [ ] 更新CHANGELOG.md

### 每月任务
- [ ] 清理.archived目录(90天以上)
- [ ] 审查并更新核心文档
- [ ] 生成文档统计报告

---

## 💻 Git Hooks集成

### pre-commit hook
```bash
#!/bin/bash
# .git/hooks/pre-commit

# 检查是否创建了禁止的文档类型
forbidden_patterns=(
    "*FIX_*.md"
    "*_2025-*.md"
    "*TODO*.md"
    "*TEMP*.md"
)

for pattern in "${forbidden_patterns[@]}"; do
    if git diff --cached --name-only | grep -q "$pattern"; then
        echo "❌ 错误: 检测到禁止的文档类型: $pattern"
        echo "请将内容添加到现有文档或代码注释中"
        exit 1
    fi
done

# 检查文档数量
doc_count=$(find docs -name "*.md" | wc -l)
if [ $doc_count -gt 20 ]; then
    echo "⚠️  警告: docs/目录文档过多 ($doc_count个)"
    echo "请考虑归档或合并文档"
fi

exit 0
```

---

## 📋 维护检查清单

### 创建文档前
- [ ] 是否可以更新现有文档？
- [ ] 是否可以写在代码注释？
- [ ] 是否可以写在commit message？
- [ ] 30天后还需要这个文档吗？

### 每次提交前
- [ ] 是否创建了临时文档？
- [ ] 是否有重复内容？
- [ ] 文档位置是否正确？
- [ ] 是否需要归档旧文档？

### 项目review时
- [ ] docs/目录是否超过10个文件？
- [ ] 是否有30天未更新的文档？
- [ ] .archived是否需要清理？
- [ ] 文档是否都有实际价值？

---

## 🚨 立即执行计划

### Phase 1: 大扫除 (立即)
```bash
# 1. 创建归档目录
mkdir -p .archived/{docs,scripts,servers}

# 2. 归档过时文档
find docs -name "*2025*.md" -exec mv {} .archived/docs/ \;
find . -maxdepth 1 -name "*FIX*.md" -exec mv {} .archived/docs/ \;

# 3. 归档废弃脚本
mv scripts/*_fix_*_2025*.sql .archived/scripts/

# 4. 归档旧服务器
mv mcp_server_*.py .archived/servers/ 2>/dev/null
mv mcp_server_unified.py . # 保留活跃的
mv mcp_server_enterprise.py . # 保留活跃的
```

### Phase 2: 建立规范 (今天)
- ✅ 创建文档生成规范
- ✅ 创建文件夹结构规范
- ✅ 创建维护策略

### Phase 3: 自动化 (本周)
- [ ] 部署自动归档脚本
- [ ] 设置Git hooks
- [ ] 创建CI/CD检查

### Phase 4: 持续改进
- [ ] 每周执行健康检查
- [ ] 每月清理归档
- [ ] 季度文档审查

---

## 📈 预期效果

| 指标 | 现状 | 1周后 | 1月后 |
|------|------|-------|-------|
| 文档总数 | 845 | < 100 | < 50 |
| docs/目录 | 143 | < 20 | < 10 |
| 新建文档/天 | 37 | < 5 | < 1 |
| 代码可读性 | 低 | 中 | 高 |

---

## 🏆 成功标准

1. **文档精简**: docs/目录保持10个以内核心文档
2. **零临时文档**: 所有临时内容在代码注释中
3. **自动化维护**: 脚本自动归档和清理
4. **团队遵守**: 所有提交符合规范

---

**执行承诺**: 从现在开始，严格执行文档维护策略，拒绝文档泛滥！
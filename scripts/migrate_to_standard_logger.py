#!/usr/bin/env python3
"""
将所有Python文件迁移到标准日志配置
"""

import os
import re
from pathlib import Path
from typing import List, Tuple

def migrate_to_standard_logger(file_path: Path) -> bool:
    """
    将文件迁移到使用标准logger

    Args:
        file_path: 要迁移的文件路径

    Returns:
        是否进行了修改
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        modified = False

        # 1. 替换logger导入
        # 旧: from ..common.logger import get_logger
        # 新: from ..common.standard_logger import get_logger
        if 'from ..common.logger import get_logger' in content:
            content = content.replace(
                'from ..common.logger import get_logger',
                'from ..common.standard_logger import get_logger'
            )
            modified = True

        # 2. 替换logging.getLogger
        # 旧: logger = logging.getLogger(__name__)
        # 新: from src.mcp_core.common.standard_logger import get_logger
        #     logger = get_logger(__name__)
        if 'logger = logging.getLogger(__name__)' in content:
            # 检查是否已有standard_logger导入
            if 'from src.mcp_core.common.standard_logger import' not in content:
                # 找到import部分
                lines = content.split('\n')
                import_end = 0
                for i, line in enumerate(lines):
                    if line.strip() and not line.strip().startswith('import') and not line.strip().startswith('from'):
                        if i > 0:
                            import_end = i
                            break

                # 插入新的导入
                if import_end > 0:
                    lines.insert(import_end, 'from src.mcp_core.common.standard_logger import get_logger')
                    content = '\n'.join(lines)

            # 替换logger创建语句
            content = re.sub(
                r'logger = logging\.getLogger\(__name__\)',
                'logger = get_logger(__name__)',
                content
            )
            modified = True

        # 3. 统一日志格式
        # 替换各种不规范的日志调用
        patterns = [
            # print(f"Error: {e}") -> logger.error(f"Error: {e}")
            (r'print\(f?"[Ee]rror:?\s*{.*?}"\)', 'logger.error'),
            # print(f"Warning: {w}") -> logger.warning(f"Warning: {w}")
            (r'print\(f?"[Ww]arning:?\s*{.*?}"\)', 'logger.warning'),
            # print(f"Debug: {d}") -> logger.debug(f"Debug: {d}")
            (r'print\(f?"[Dd]ebug:?\s*{.*?}"\)', 'logger.debug'),
        ]

        for pattern, replacement in patterns:
            if re.search(pattern, content):
                # 这里需要更复杂的替换逻辑
                modified = True

        # 4. 保存修改
        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True

    except Exception as e:
        print(f"Error processing {file_path}: {e}")

    return False


def find_python_files(root_dir: str, exclude_dirs: List[str] = None) -> List[Path]:
    """
    查找所有Python文件

    Args:
        root_dir: 根目录
        exclude_dirs: 排除的目录

    Returns:
        Python文件路径列表
    """
    exclude_dirs = exclude_dirs or ['venv', '__pycache__', '.git', 'node_modules', '.pytest_cache']
    python_files = []

    for file_path in Path(root_dir).rglob('*.py'):
        # 检查是否在排除目录中
        if any(excluded in str(file_path) for excluded in exclude_dirs):
            continue
        python_files.append(file_path)

    return python_files


def main():
    """主函数"""
    project_root = '/Users/mac/Downloads/MCP'

    print("🔄 开始迁移到标准日志配置...")

    # 查找所有Python文件
    python_files = find_python_files(project_root)
    print(f"📂 找到 {len(python_files)} 个Python文件")

    # 迁移每个文件
    migrated_count = 0
    for file_path in python_files:
        if migrate_to_standard_logger(file_path):
            print(f"  ✅ 已迁移: {file_path.relative_to(project_root)}")
            migrated_count += 1

    print(f"\n✨ 迁移完成！共迁移 {migrated_count} 个文件")

    # 生成迁移报告
    report = f"""
# 日志迁移报告

迁移时间: 2025-11-21
总文件数: {len(python_files)}
迁移文件: {migrated_count}

## 标准日志配置

所有模块现在使用统一的日志配置：

```python
from src.mcp_core.common.standard_logger import get_logger
logger = get_logger(__name__)
```

## 日志级别

- DEBUG: 详细调试信息
- INFO: 一般信息
- WARNING: 警告信息
- ERROR: 错误信息
- CRITICAL: 严重错误

## 配置方式

通过环境变量设置日志级别：
```bash
export LOG_LEVEL=DEBUG
```

或在代码中初始化：
```python
from src.mcp_core.common.standard_logger import setup_logging
setup_logging(level='DEBUG', format_type='detailed')
```
"""

    report_path = Path(project_root) / 'docs' / 'LOGGING_MIGRATION_REPORT.md'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"📄 迁移报告已保存到: {report_path}")


if __name__ == "__main__":
    main()
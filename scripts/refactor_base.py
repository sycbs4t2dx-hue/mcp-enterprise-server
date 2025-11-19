#!/usr/bin/env python3
"""
MCP v2.0.0 - 自动重构Base导入

自动将所有服务文件中的独立Base替换为统一Base

执行: python3 scripts/refactor_base.py
"""

import re
import os
from pathlib import Path

# 需要重构的文件列表
FILES_TO_REFACTOR = [
    "src/mcp_core/code_knowledge_service.py",
    "src/mcp_core/project_context_service.py",
    "src/mcp_core/quality_guardian_service.py",
]

# Base定义的模式
OLD_BASE_PATTERN = r'^Base\s*=\s*declarative_base\(\)'

# 新的import语句
NEW_IMPORT = "from mcp_core.models.base import Base"


def refactor_file(file_path: str) -> bool:
    """
    重构单个文件

    Args:
        file_path: 文件路径

    Returns:
        是否修改成功
    """
    if not os.path.exists(file_path):
        print(f"❌ 文件不存在: {file_path}")
        return False

    print(f"\n📝 处理: {file_path}")

    # 读取文件
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.splitlines()

    # 备份
    backup_path = file_path + ".before_refactor"
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"   ✅ 备份到: {backup_path}")

    # 标记需要修改
    modified = False
    new_lines = []
    found_old_base = False
    has_new_import = False

    for i, line in enumerate(lines):
        # 检查是否有旧的Base定义
        if re.match(OLD_BASE_PATTERN, line.strip()):
            print(f"   🔍 找到旧Base (行{i+1}): {line.strip()}")
            # 注释掉旧的Base定义
            new_lines.append(f"# {line}  # ❌ 已废弃: 使用统一的Base")
            found_old_base = True
            modified = True
            continue

        # 检查是否已有新import
        if NEW_IMPORT in line:
            has_new_import = True

        # 检查declarative_base导入
        if 'from sqlalchemy.ext.declarative import declarative_base' in line:
            if not has_new_import:
                # 替换为新import
                new_lines.append(f"# {line}  # ❌ 已废弃")
                new_lines.append(NEW_IMPORT)
                has_new_import = True
                modified = True
                print(f"   ✅ 添加统一Base导入 (行{i+1})")
                continue

        new_lines.append(line)

    # 如果找到了旧Base但没有新import,在文件开头添加
    if found_old_base and not has_new_import:
        # 找到第一个import语句后插入
        for i, line in enumerate(new_lines):
            if line.startswith('from') or line.startswith('import'):
                new_lines.insert(i + 1, NEW_IMPORT)
                modified = True
                print(f"   ✅ 在import区域添加统一Base导入")
                break

    if not modified:
        print("   ℹ️  无需修改")
        os.remove(backup_path)
        return False

    # 写回文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(new_lines) + '\n')

    print(f"   ✅ 修改完成")
    return True


def main():
    """主函数"""
    print("=" * 60)
    print("  MCP Base重构工具")
    print("=" * 60)

    total = len(FILES_TO_REFACTOR)
    modified = 0

    for file_path in FILES_TO_REFACTOR:
        if refactor_file(file_path):
            modified += 1

    print("\n" + "=" * 60)
    print(f"  完成! 修改了 {modified}/{total} 个文件")
    print("=" * 60)

    print("\n📋 下一步:")
    print("  1. 检查修改: git diff")
    print("  2. 运行测试: python3 -m pytest")
    print("  3. 重启服务器: ./restart_server.sh")
    print("  4. 如有问题,可从.before_refactor备份恢复")


if __name__ == "__main__":
    main()

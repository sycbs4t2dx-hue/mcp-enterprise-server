#!/usr/bin/env python3
"""
技术债务清理脚本
自动化清理MCP项目中的技术债务
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple, Dict

class TechnicalDebtCleaner:
    """技术债务清理器"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.issues_found = []
        self.fixes_applied = []

    def scan_and_fix_bare_excepts(self, file_path: Path) -> int:
        """修复bare except语句"""
        fixes = 0
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 查找bare except
            bare_except_pattern = r'(\s+)except\s*:\s*$'

            # 替换为except Exception
            new_content = re.sub(
                bare_except_pattern,
                r'\1except Exception:',
                content,
                flags=re.MULTILINE
            )

            if new_content != content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                fixes = content.count('except:') - new_content.count('except:')
                self.fixes_applied.append(f"Fixed {fixes} bare except(s) in {file_path}")

        except Exception as e:
            print(f"Error processing {file_path}: {e}")

        return fixes

    def replace_print_with_logger(self, file_path: Path) -> int:
        """将print语句替换为logger调用"""
        fixes = 0
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            modified = False
            has_logger = False

            # 检查是否已有logger
            for line in lines:
                if 'logger = get_logger' in line or 'logger = logging.getLogger' in line:
                    has_logger = True
                    break

            # 如果没有logger，需要添加
            if not has_logger:
                # 查找import语句的位置
                import_index = 0
                for i, line in enumerate(lines):
                    if line.strip().startswith('import ') or line.strip().startswith('from '):
                        import_index = i + 1

                # 添加logger导入
                lines.insert(import_index, 'import logging\n')
                lines.insert(import_index + 1, '\n')
                lines.insert(import_index + 2, 'logger = logging.getLogger(__name__)\n')
                lines.insert(import_index + 3, '\n')
                modified = True

            # 替换print语句
            for i, line in enumerate(lines):
                if 'print(' in line and not line.strip().startswith('#'):
                    # 提取print内容
                    match = re.search(r'print\((.*)\)', line)
                    if match:
                        content = match.group(1)
                        indent = len(line) - len(line.lstrip())

                        # 判断日志级别
                        if 'error' in content.lower() or 'exception' in content.lower():
                            new_line = ' ' * indent + f'logger.error({content})\n'
                        elif 'warn' in content.lower():
                            new_line = ' ' * indent + f'logger.warning({content})\n'
                        elif 'debug' in content.lower():
                            new_line = ' ' * indent + f'logger.debug({content})\n'
                        else:
                            new_line = ' ' * indent + f'logger.info({content})\n'

                        lines[i] = new_line
                        modified = True
                        fixes += 1

            if modified:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                self.fixes_applied.append(f"Replaced {fixes} print statement(s) in {file_path}")

        except Exception as e:
            print(f"Error processing {file_path}: {e}")

        return fixes

    def remove_unused_imports(self, file_path: Path) -> int:
        """移除未使用的导入"""
        fixes = 0
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 特定的未使用导入（基于扫描结果）
            unused_imports = {
                'mcp_server_enterprise.py': ['hashlib'],
            }

            file_name = file_path.name
            if file_name in unused_imports:
                for unused in unused_imports[file_name]:
                    # 移除导入行
                    pattern = f'^import {unused}$|^from .* import .*{unused}.*$'
                    new_content = re.sub(
                        pattern,
                        '',
                        content,
                        flags=re.MULTILINE
                    )

                    if new_content != content:
                        # 清理多余的空行
                        new_content = re.sub(r'\n\n\n+', '\n\n', new_content)

                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        fixes += 1
                        self.fixes_applied.append(f"Removed unused import '{unused}' from {file_path}")
                        content = new_content

        except Exception as e:
            print(f"Error processing {file_path}: {e}")

        return fixes

    def standardize_logging_format(self, file_path: Path) -> int:
        """标准化日志格式"""
        fixes = 0
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 标准化日志格式
            patterns = [
                # logger.info("message") -> logger.info("message")
                (r'logger\.(info|debug|warning|error)\("([^"]+)"\s*%\s*([^)]+)\)',
                 r'logger.\1(f"\2{\3}")'),
                # logger.info("message %s" % var) -> logger.info(f"message {var}")
                (r'logger\.(info|debug|warning|error)\("([^"]+)%s([^"]*)"[,\s]*%\s*([^)]+)\)',
                 r'logger.\1(f"\2{\4}\3")'),
            ]

            for pattern, replacement in patterns:
                new_content = re.sub(pattern, replacement, content)
                if new_content != content:
                    fixes += 1
                    content = new_content

            if fixes > 0:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.fixes_applied.append(f"Standardized {fixes} log format(s) in {file_path}")

        except Exception as e:
            print(f"Error processing {file_path}: {e}")

        return fixes

    def clean_commented_code(self, file_path: Path) -> int:
        """清理注释掉的代码（保留文档注释）"""
        fixes = 0
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            modified = False
            new_lines = []

            for i, line in enumerate(lines):
                # 跳过文档字符串和有用的注释
                if line.strip().startswith('#') and not any(
                    keyword in line.lower() for keyword in ['todo', 'fixme', 'note', 'warning', 'deprecated', '❌']
                ):
                    # 检查是否是注释掉的代码
                    commented_code_patterns = [
                        r'^\s*#\s*(import|from|def|class|if|for|while|try|except|return)\s',
                        r'^\s*#\s*[a-zA-Z_][a-zA-Z0-9_]*\s*=',  # 变量赋值
                        r'^\s*#\s*[a-zA-Z_][a-zA-Z0-9_]*\(',     # 函数调用
                    ]

                    is_code = any(re.match(pattern, line) for pattern in commented_code_patterns)

                    if is_code:
                        modified = True
                        fixes += 1
                        continue  # 跳过这一行

                new_lines.append(line)

            if modified:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(new_lines)
                self.fixes_applied.append(f"Removed {fixes} commented code line(s) from {file_path}")

        except Exception as e:
            print(f"Error processing {file_path}: {e}")

        return fixes

    def process_file(self, file_path: Path) -> Dict[str, int]:
        """处理单个文件的所有技术债务"""
        results = {
            'bare_excepts': 0,
            'print_statements': 0,
            'unused_imports': 0,
            'log_formats': 0,
            'commented_code': 0
        }

        if file_path.suffix == '.py':
            print(f"Processing {file_path}...")

            results['bare_excepts'] = self.scan_and_fix_bare_excepts(file_path)
            results['print_statements'] = self.replace_print_with_logger(file_path)
            results['unused_imports'] = self.remove_unused_imports(file_path)
            results['log_formats'] = self.standardize_logging_format(file_path)
            results['commented_code'] = self.clean_commented_code(file_path)

        return results

    def run(self, target_files: List[str] = None):
        """运行技术债务清理"""
        total_results = {
            'bare_excepts': 0,
            'print_statements': 0,
            'unused_imports': 0,
            'log_formats': 0,
            'commented_code': 0
        }

        if target_files:
            # 处理指定文件
            for file_path in target_files:
                path = Path(file_path)
                if path.exists():
                    results = self.process_file(path)
                    for key in total_results:
                        total_results[key] += results[key]
        else:
            # 处理所有Python文件
            for file_path in self.project_root.rglob('*.py'):
                # 跳过虚拟环境和测试文件
                if 'venv' in str(file_path) or '__pycache__' in str(file_path):
                    continue

                results = self.process_file(file_path)
                for key in total_results:
                    total_results[key] += results[key]

        # 生成报告
        self.generate_report(total_results)

    def generate_report(self, results: Dict[str, int]):
        """生成清理报告"""
        print("\n" + "=" * 60)
        print("技术债务清理报告")
        print("=" * 60)

        print("\n📊 清理统计:")
        print(f"  • Bare except语句修复: {results['bare_excepts']}")
        print(f"  • Print语句替换为logger: {results['print_statements']}")
        print(f"  • 未使用导入移除: {results['unused_imports']}")
        print(f"  • 日志格式标准化: {results['log_formats']}")
        print(f"  • 注释代码清理: {results['commented_code']}")

        total_fixes = sum(results.values())
        print(f"\n✅ 总计修复: {total_fixes} 个问题")

        if self.fixes_applied:
            print("\n📝 详细修复列表:")
            for fix in self.fixes_applied:
                print(f"  • {fix}")

        print("\n" + "=" * 60)


def main():
    """主函数"""
    # 高优先级清理文件
    priority_files = [
        '/Users/mac/Downloads/MCP/mcp_server_enterprise.py',
        '/Users/mac/Downloads/MCP/src/mcp_core/code_analyzer.py',
        '/Users/mac/Downloads/MCP/src/mcp_core/multi_lang_analyzer.py',
        '/Users/mac/Downloads/MCP/src/mcp_core/services/error_firewall.py',
        '/Users/mac/Downloads/MCP/src/mcp_core/services/experience_manager.py',
        '/Users/mac/Downloads/MCP/src/mcp_core/swift_analyzer.py',
        '/Users/mac/Downloads/MCP/src/mcp_core/quality_guardian_service.py',
    ]

    cleaner = TechnicalDebtCleaner('/Users/mac/Downloads/MCP')

    print("🧹 开始技术债务清理...")
    print(f"目标文件: {len(priority_files)} 个高优先级文件")

    # 运行清理
    cleaner.run(priority_files)

    print("\n✨ 技术债务清理完成!")


if __name__ == "__main__":
    main()
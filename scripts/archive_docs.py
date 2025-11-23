#!/usr/bin/env python3
"""
文档自动归档工具
每周执行一次，清理过期文档

Usage:
    python3 scripts/archive_docs.py [--dry-run] [--days N]
"""

import os
import sys
import shutil
import argparse
from datetime import datetime, timedelta
from pathlib import Path


class DocumentArchiver:
    """文档归档管理器"""

    def __init__(self, days=30, dry_run=False):
        self.days = days
        self.dry_run = dry_run
        self.archive_dir = Path(".archived/docs")
        self.cutoff_date = datetime.now() - timedelta(days=days)

        # 永久保留的文件
        self.keep_files = {
            "README.md", "API.md", "ARCHITECTURE.md",
            "DEPLOYMENT.md", "CHANGELOG.md", "LICENSE",
            "INDEX.md", "QUICKSTART.md"
        }

        # 需要归档的文档模式
        self.archive_patterns = [
            "*2025*.md", "*2024*.md", "*2023*.md",
            "*FIX*.md", "*FIXED*.md",
            "*COMPLETE*.md", "*COMPLETED*.md",
            "*SUMMARY*.md", "*REPORT*.md",
            "*IMPLEMENTATION*.md", "*PHASE*.md",
            "*TODO*.md", "*TEMP*.md", "*TEST*.md"
        ]

    def setup_archive_dir(self):
        """创建归档目录"""
        if not self.dry_run:
            self.archive_dir.mkdir(parents=True, exist_ok=True)
        print(f"✅ 归档目录: {self.archive_dir}")

    def should_archive(self, file_path: Path) -> bool:
        """判断文件是否需要归档"""
        # 永久保留文件
        if file_path.name in self.keep_files:
            return False

        # 检查文件名模式
        for pattern in self.archive_patterns:
            if file_path.match(pattern):
                return True

        # 检查修改时间
        mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
        if mtime < self.cutoff_date:
            return True

        return False

    def archive_file(self, file_path: Path) -> bool:
        """归档单个文件"""
        try:
            archive_path = self.archive_dir / file_path.name

            if self.dry_run:
                print(f"  [模拟] {file_path} → {archive_path}")
            else:
                # 如果目标文件已存在，添加时间戳
                if archive_path.exists():
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    stem = archive_path.stem
                    suffix = archive_path.suffix
                    archive_path = self.archive_dir / f"{stem}_{timestamp}{suffix}"

                shutil.move(str(file_path), str(archive_path))
                print(f"  归档: {file_path} → {archive_path}")

            return True
        except Exception as e:
            print(f"  ❌ 归档失败 {file_path}: {e}")
            return False

    def archive_docs_directory(self, docs_dir="docs") -> int:
        """归档docs目录"""
        docs_path = Path(docs_dir)
        if not docs_path.exists():
            print(f"⚠️  目录不存在: {docs_dir}")
            return 0

        archived_count = 0

        print(f"\n📂 扫描目录: {docs_dir}")
        for file_path in docs_path.glob("*.md"):
            if self.should_archive(file_path):
                if self.archive_file(file_path):
                    archived_count += 1

        # 递归处理子目录
        for subdir in docs_path.iterdir():
            if subdir.is_dir() and subdir.name not in ["archive", ".archived"]:
                count = self.archive_subdirectory(subdir)
                archived_count += count

        return archived_count

    def archive_subdirectory(self, subdir: Path) -> int:
        """归档子目录中的文档"""
        archived_count = 0

        print(f"\n📂 扫描子目录: {subdir}")
        for file_path in subdir.glob("*.md"):
            if self.should_archive(file_path):
                # 保持子目录结构
                relative_path = file_path.relative_to(subdir.parent)
                archive_path = self.archive_dir / relative_path.parent

                if not self.dry_run:
                    archive_path.mkdir(parents=True, exist_ok=True)

                if self.archive_file(file_path):
                    archived_count += 1

        return archived_count

    def archive_root_docs(self) -> int:
        """归档根目录的文档"""
        archived_count = 0

        print(f"\n📂 扫描根目录")
        for file_path in Path(".").glob("*.md"):
            if self.should_archive(file_path):
                if self.archive_file(file_path):
                    archived_count += 1

        return archived_count

    def clean_old_archives(self, days=90):
        """清理超期的归档文件"""
        if not self.archive_dir.exists():
            return 0

        cleanup_date = datetime.now() - timedelta(days=days)
        cleaned_count = 0

        print(f"\n🗑️  清理{days}天前的归档文件")
        for file_path in self.archive_dir.rglob("*"):
            if file_path.is_file():
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                if mtime < cleanup_date:
                    if self.dry_run:
                        print(f"  [模拟删除] {file_path}")
                    else:
                        file_path.unlink()
                        print(f"  删除: {file_path}")
                    cleaned_count += 1

        return cleaned_count

    def generate_report(self):
        """生成文档健康报告"""
        print("\n" + "=" * 60)
        print("📊 文档健康报告")
        print("=" * 60)

        # 统计各目录文档数量
        total_docs = len(list(Path(".").rglob("*.md")))
        docs_in_docs = len(list(Path("docs").glob("*.md"))) if Path("docs").exists() else 0
        archived_docs = len(list(self.archive_dir.rglob("*.md"))) if self.archive_dir.exists() else 0

        print(f"总文档数: {total_docs}")
        print(f"docs/目录: {docs_in_docs}")
        print(f"已归档: {archived_docs}")

        # 健康评分
        if docs_in_docs <= 10:
            status = "✅ 健康"
        elif docs_in_docs <= 20:
            status = "⚠️  警告"
        else:
            status = "❌ 需要清理"

        print(f"健康状态: {status}")
        print("=" * 60)

    def run(self):
        """执行归档流程"""
        print(f"🚀 文档自动归档工具")
        print(f"配置: {'模拟模式' if self.dry_run else '执行模式'}, 归档{self.days}天前的文档")

        # 1. 设置归档目录
        self.setup_archive_dir()

        # 2. 归档各目录
        total_archived = 0
        total_archived += self.archive_docs_directory("docs")
        total_archived += self.archive_root_docs()

        # 3. 清理旧归档
        cleaned = self.clean_old_archives(90)

        # 4. 生成报告
        self.generate_report()

        print(f"\n✅ 完成: 归档{total_archived}个文件, 清理{cleaned}个旧文件")

        if self.dry_run:
            print("\n💡 提示: 这是模拟运行，使用不带 --dry-run 参数执行实际归档")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="文档自动归档工具")
    parser.add_argument("--dry-run", action="store_true", help="模拟运行，不实际移动文件")
    parser.add_argument("--days", type=int, default=30, help="归档N天前的文档（默认30天）")

    args = parser.parse_args()

    archiver = DocumentArchiver(days=args.days, dry_run=args.dry_run)
    archiver.run()


if __name__ == "__main__":
    main()
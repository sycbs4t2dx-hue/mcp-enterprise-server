#!/usr/bin/env python3
"""
多语言代码分析器 - 统一入口

自动检测代码语言并调用对应的分析器
"""

import os
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional
from collections import defaultdict

from .code_analyzer import CodeEntity, CodeRelation, ProjectAnalyzer as PythonProjectAnalyzer


class MultiLanguageAnalyzer:
    """多语言项目分析器"""

    # 语言到文件扩展名的映射
    LANGUAGE_EXTENSIONS = {
        "python": [".py"],
        "java": [".java"],
        "vue": [".vue"],
        "javascript": [".js", ".jsx"],
        "typescript": [".ts", ".tsx"],
        "swift": [".swift"],
    }

    # 扩展名到语言的映射（反向）
    EXTENSION_TO_LANGUAGE = {}
    for lang, exts in LANGUAGE_EXTENSIONS.items():
        for ext in exts:
            EXTENSION_TO_LANGUAGE[ext] = lang

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.all_entities: List[CodeEntity] = []
        self.all_relations: List[CodeRelation] = []

        # 统计信息
        self.stats = {
            "total_files": 0,
            "languages": defaultdict(int),
            "entities_by_language": defaultdict(int),
            "relations_by_language": defaultdict(int),
        }

    def analyze_project(self) -> Dict[str, Any]:
        """分析整个多语言项目"""
        print(f"📊 开始分析多语言项目: {self.project_root}")

        # 扫描所有支持的文件
        files_by_language = self._scan_files()

        print(f"\n📂 扫描结果:")
        for lang, files in files_by_language.items():
            print(f"   {lang}: {len(files)}个文件")

        # 逐语言分析
        for language, files in files_by_language.items():
            if files:
                print(f"\n分析{language}代码...")
                self._analyze_language(language, files)

        # 更新统计
        self.stats["total_files"] = sum(len(files) for files in files_by_language.values())

        print("\n" + "=" * 60)
        print("✅ 多语言分析完成！")
        print(f"   总文件数: {self.stats['total_files']}")
        for lang in files_by_language.keys():
            print(f"   {lang}: {self.stats['entities_by_language'][lang]}个实体, "
                  f"{self.stats['relations_by_language'][lang]}个关系")
        print("=" * 60)

        return {
            "entities": [self._entity_to_dict(e) for e in self.all_entities],
            "relations": [self._relation_to_dict(r) for r in self.all_relations],
            "stats": dict(self.stats)
        }

    def _scan_files(self) -> Dict[str, List[Path]]:
        """扫描项目中的所有支持文件"""
        files_by_language = defaultdict(list)

        # 排除目录
        exclude_dirs = {'venv', '__pycache__', '.git', 'node_modules', 'build', 'dist', 'target'}

        for file_path in self.project_root.rglob('*'):
            if not file_path.is_file():
                continue

            # 检查是否在排除目录中
            if any(part in exclude_dirs for part in file_path.parts):
                continue

            # 检查扩展名
            ext = file_path.suffix.lower()
            language = self.EXTENSION_TO_LANGUAGE.get(ext)

            if language:
                files_by_language[language].append(file_path)
                self.stats["languages"][language] += 1

        return files_by_language

    def _analyze_language(self, language: str, files: List[Path]):
        """分析特定语言的文件"""
        if language == "python":
            self._analyze_python_files(files)
        elif language == "java":
            self._analyze_java_files(files)
        elif language == "vue":
            self._analyze_vue_files(files)
        elif language == "swift":
            self._analyze_swift_files(files)
        elif language == "javascript" or language == "typescript":
            # TODO: 实现JS/TS分析
            print(f"   ⚠️  {language}支持开发中...")
        else:
            print(f"   ⚠️  不支持的语言: {language}")

    def _analyze_python_files(self, files: List[Path]):
        """分析Python文件"""
        from .code_analyzer import PythonCodeAnalyzer

        for i, file_path in enumerate(files, 1):
            if i % 10 == 0:
                print(f"   [{i}/{len(files)}] {file_path.name}")

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    source_code = f.read()

                analyzer = PythonCodeAnalyzer(str(file_path), str(self.project_root))
                entities, relations = analyzer.analyze(source_code)

                self.all_entities.extend(entities)
                self.all_relations.extend(relations)

                self.stats["entities_by_language"]["python"] += len(entities)
                self.stats["relations_by_language"]["python"] += len(relations)

            except Exception as e:
                print(f"   ⚠️  分析失败 {file_path}: {e}")

    def _analyze_java_files(self, files: List[Path]):
        """分析Java文件"""
        try:
            from .java_analyzer import JavaCodeAnalyzer
        except ImportError:
            print("   ⚠️  javalang未安装，跳过Java分析")
            print("   安装: pip install javalang")
            return

        for i, file_path in enumerate(files, 1):
            if i % 10 == 0:
                print(f"   [{i}/{len(files)}] {file_path.name}")

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    source_code = f.read()

                analyzer = JavaCodeAnalyzer(str(file_path), str(self.project_root))
                entities, relations = analyzer.analyze(source_code)

                self.all_entities.extend(entities)
                self.all_relations.extend(relations)

                self.stats["entities_by_language"]["java"] += len(entities)
                self.stats["relations_by_language"]["java"] += len(relations)

            except Exception as e:
                print(f"   ⚠️  分析失败 {file_path}: {e}")

    def _analyze_vue_files(self, files: List[Path]):
        """分析Vue文件"""
        from .vue_analyzer import VueCodeAnalyzer

        for i, file_path in enumerate(files, 1):
            if i % 10 == 0:
                print(f"   [{i}/{len(files)}] {file_path.name}")

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    source_code = f.read()

                analyzer = VueCodeAnalyzer(str(file_path), str(self.project_root))
                entities, relations = analyzer.analyze(source_code)

                self.all_entities.extend(entities)
                self.all_relations.extend(relations)

                self.stats["entities_by_language"]["vue"] += len(entities)
                self.stats["relations_by_language"]["vue"] += len(relations)

            except Exception as e:
                print(f"   ⚠️  分析失败 {file_path}: {e}")

    def _analyze_swift_files(self, files: List[Path]):
        """分析Swift文件"""
        from .swift_analyzer import SwiftCodeAnalyzer

        for i, file_path in enumerate(files, 1):
            if i % 10 == 0:
                print(f"   [{i}/{len(files)}] {file_path.name}")

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    source_code = f.read()

                analyzer = SwiftCodeAnalyzer(str(file_path), str(self.project_root))
                entities, relations = analyzer.analyze(source_code)

                self.all_entities.extend(entities)
                self.all_relations.extend(relations)

                self.stats["entities_by_language"]["swift"] += len(entities)
                self.stats["relations_by_language"]["swift"] += len(relations)

            except Exception as e:
                print(f"   ⚠️  分析失败 {file_path}: {e}")

    def _entity_to_dict(self, entity: CodeEntity) -> Dict:
        """实体转为字典"""
        return {
            "id": entity.id,
            "type": entity.type,
            "name": entity.name,
            "qualified_name": entity.qualified_name,
            "file_path": entity.file_path,
            "line_number": entity.line_number,
            "end_line": entity.end_line,
            "docstring": entity.docstring,
            "signature": entity.signature,
            "parent_id": entity.parent_id,
            "metadata": entity.metadata or {}
        }

    def _relation_to_dict(self, relation: CodeRelation) -> Dict:
        """关系转为字典"""
        return {
            "source_id": relation.source_id,
            "target_id": relation.target_id,
            "relation_type": relation.relation_type,
            "metadata": relation.metadata or {}
        }

    def export_json(self, output_path: str):
        """导出为JSON"""
        import json

        data = {
            "entities": [self._entity_to_dict(e) for e in self.all_entities],
            "relations": [self._relation_to_dict(r) for e in self.all_relations],
            "stats": dict(self.stats)
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"💾 导出到: {output_path}")


# ==================== 命令行工具 ====================

def main():
    """命令行入口"""
    import sys

    if len(sys.argv) < 2:
        print("用法: python multi_lang_analyzer.py <project_path>")
        print("示例: python multi_lang_analyzer.py /path/to/project")
        sys.exit(1)

    project_path = sys.argv[1]

    # 创建分析器
    analyzer = MultiLanguageAnalyzer(project_path)

    # 分析项目
    result = analyzer.analyze_project()

    # 导出
    output_path = Path(project_path) / "code_knowledge_graph_multi.json"
    analyzer.export_json(str(output_path))

    # 生成摘要
    print("\n" + "=" * 60)
    print("📈 分析摘要")
    print("=" * 60)
    print(f"项目: {project_path}")
    print(f"总文件: {result['stats']['total_files']}")
    print(f"总实体: {len(result['entities'])}")
    print(f"总关系: {len(result['relations'])}")
    print()
    print("各语言统计:")
    for lang, count in result['stats']['languages'].items():
        entities = result['stats']['entities_by_language'][lang]
        relations = result['stats']['relations_by_language'][lang]
        print(f"  {lang}:")
        print(f"    文件: {count}")
        print(f"    实体: {entities}")
        print(f"    关系: {relations}")


if __name__ == "__main__":
    main()

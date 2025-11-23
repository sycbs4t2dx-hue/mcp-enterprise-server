#!/usr/bin/env python3
"""
代码知识图谱 - 代码分析引擎

深度分析Python项目，提取结构化知识，构建永久记忆
"""

import ast
import os
import json
from pathlib import Path
from typing import Dict, List, Set, Any, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict
import hashlib
import logging

# Configure logger
logger = logging.getLogger(__name__)


@dataclass
class CodeEntity:
    """代码实体"""
    id: str  # 唯一标识
    type: str  # 类型: class, function, variable, module
    name: str  # 名称
    qualified_name: str  # 完全限定名
    file_path: str  # 文件路径
    line_number: int  # 行号
    end_line: int  # 结束行号
    docstring: Optional[str] = None  # 文档字符串
    signature: Optional[str] = None  # 函数签名
    parent_id: Optional[str] = None  # 父实体ID
    metadata: Dict[str, Any] = None  # 额外元数据

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class CodeRelation:
    """代码关系"""
    source_id: str  # 源实体ID
    target_id: str  # 目标实体ID
    relation_type: str  # 关系类型: calls, imports, inherits, uses
    metadata: Dict[str, Any] = None  # 额外元数据

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class PythonCodeAnalyzer(ast.NodeVisitor):
    """Python代码AST分析器"""

    def __init__(self, file_path: str, project_root: str):
        self.file_path = file_path
        self.project_root = project_root
        self.relative_path = os.path.relpath(file_path, project_root)

        # 实体存储
        self.entities: List[CodeEntity] = []
        self.relations: List[CodeRelation] = []

        # 上下文栈
        self.context_stack: List[str] = []  # 当前作用域
        self.current_class: Optional[str] = None

        # 映射表
        self.entity_map: Dict[str, CodeEntity] = {}  # name -> entity

    def analyze(self, source_code: str) -> tuple[List[CodeEntity], List[CodeRelation]]:
        """分析源代码"""
        try:
            tree = ast.parse(source_code, filename=self.file_path)
            self.visit(tree)
            return self.entities, self.relations
        except SyntaxError as e:
            logger.info(f"⚠️  语法错误 {self.file_path}: {e}")
            return [], []

    def _generate_id(self, type: str, name: str, line: int) -> str:
        """生成唯一ID"""
        key = f"{self.relative_path}:{type}:{name}:{line}"
        return hashlib.md5(key.encode()).hexdigest()[:16]

    def _get_qualified_name(self, name: str) -> str:
        """获取完全限定名"""
        if self.context_stack:
            return ".".join(self.context_stack + [name])
        return name

    def _get_docstring(self, node) -> Optional[str]:
        """提取文档字符串"""
        return ast.get_docstring(node)

    # ==================== 访问者模式 ====================

    def visit_ClassDef(self, node: ast.ClassDef):
        """访问类定义"""
        qualified_name = self._get_qualified_name(node.name)
        entity_id = self._generate_id("class", node.name, node.lineno)

        # 创建类实体
        entity = CodeEntity(
            id=entity_id,
            type="class",
            name=node.name,
            qualified_name=qualified_name,
            file_path=self.relative_path,
            line_number=node.lineno,
            end_line=getattr(node, 'end_lineno', node.lineno),
            docstring=self._get_docstring(node),
            metadata={
                "bases": [self._get_name(base) for base in node.bases],
                "decorators": [self._get_name(dec) for dec in node.decorator_list],
                "methods": [],
                "attributes": []
            }
        )

        self.entities.append(entity)
        self.entity_map[qualified_name] = entity

        # 继承关系
        for base in node.bases:
            base_name = self._get_name(base)
            if base_name:
                self.relations.append(CodeRelation(
                    source_id=entity_id,
                    target_id=base_name,  # 先存名字，后续解析
                    relation_type="inherits",
                    metadata={"base_class": base_name}
                ))

        # 进入类作用域
        old_class = self.current_class
        self.current_class = entity_id
        self.context_stack.append(node.name)

        self.generic_visit(node)

        # 退出类作用域
        self.context_stack.pop()
        self.current_class = old_class

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """访问函数/方法定义"""
        qualified_name = self._get_qualified_name(node.name)
        entity_id = self._generate_id("function", node.name, node.lineno)

        # 提取参数
        args = []
        for arg in node.args.args:
            arg_name = arg.arg
            arg_type = None
            if arg.annotation:
                arg_type = ast.unparse(arg.annotation)
            args.append({"name": arg_name, "type": arg_type})

        # 提取返回类型
        return_type = None
        if node.returns:
            return_type = ast.unparse(node.returns)

        # 生成函数签名
        signature = self._generate_signature(node.name, args, return_type)

        # 创建函数实体
        entity = CodeEntity(
            id=entity_id,
            type="function" if not self.current_class else "method",
            name=node.name,
            qualified_name=qualified_name,
            file_path=self.relative_path,
            line_number=node.lineno,
            end_line=getattr(node, 'end_lineno', node.lineno),
            docstring=self._get_docstring(node),
            signature=signature,
            parent_id=self.current_class,
            metadata={
                "arguments": args,
                "return_type": return_type,
                "decorators": [self._get_name(dec) for dec in node.decorator_list],
                "is_async": isinstance(node, ast.AsyncFunctionDef),
                "calls": [],  # 调用的函数
                "uses": []    # 使用的变量/类
            }
        )

        self.entities.append(entity)
        self.entity_map[qualified_name] = entity

        # 如果是类方法，建立父子关系
        if self.current_class:
            self.relations.append(CodeRelation(
                source_id=self.current_class,
                target_id=entity_id,
                relation_type="contains",
                metadata={"type": "method"}
            ))

        # 进入函数作用域
        self.context_stack.append(node.name)

        # 分析函数体
        self._analyze_function_body(node, entity_id)

        # 退出函数作用域
        self.context_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """访问异步函数"""
        self.visit_FunctionDef(node)

    def visit_Import(self, node: ast.Import):
        """访问import语句"""
        for alias in node.names:
            module_name = alias.name
            # 记录导入关系
            # TODO: 创建模块实体和导入关系

    def visit_ImportFrom(self, node: ast.ImportFrom):
        """访问from...import语句"""
        module_name = node.module if node.module else ""
        for alias in node.names:
            name = alias.name
            # 记录导入关系
            # TODO: 创建导入关系

    # ==================== 辅助方法 ====================

    def _analyze_function_body(self, func_node, func_id: str):
        """分析函数体，提取调用关系"""
        for node in ast.walk(func_node):
            # 函数调用
            if isinstance(node, ast.Call):
                func_name = self._get_name(node.func)
                if func_name:
                    self.relations.append(CodeRelation(
                        source_id=func_id,
                        target_id=func_name,  # 先存名字
                        relation_type="calls",
                        metadata={"function": func_name}
                    ))

            # 属性访问 (可能是方法调用)
            elif isinstance(node, ast.Attribute):
                attr_name = node.attr
                # TODO: 分析属性访问

    def _get_name(self, node) -> Optional[str]:
        """从AST节点获取名称"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return ast.unparse(node)
        elif isinstance(node, ast.Call):
            return self._get_name(node.func)
        else:
            try:
                return ast.unparse(node)
            except Exception as e:
                return None

    def _generate_signature(self, name: str, args: List[Dict], return_type: Optional[str]) -> str:
        """生成函数签名"""
        arg_strs = []
        for arg in args:
            if arg.get("type"):
                arg_strs.append(f"{arg['name']}: {arg['type']}")
            else:
                arg_strs.append(arg['name'])

        signature = f"{name}({', '.join(arg_strs)})"
        if return_type:
            signature += f" -> {return_type}"

        return signature


class ProjectAnalyzer:
    """项目级别分析器"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.all_entities: List[CodeEntity] = []
        self.all_relations: List[CodeRelation] = []

        # 统计信息
        self.stats = {
            "total_files": 0,
            "total_lines": 0,
            "total_classes": 0,
            "total_functions": 0,
            "total_imports": 0,
            "total_relations": 0
        }

    def analyze_project(self, extensions: List[str] = [".py"]) -> Dict[str, Any]:
        """分析整个项目"""
        logger.info(f"📊 开始分析项目: {self.project_root}")

        # 扫描所有Python文件
        python_files = []
        for ext in extensions:
            python_files.extend(self.project_root.rglob(f"*{ext}"))

        # 过滤掉虚拟环境和缓存
        python_files = [
            f for f in python_files
            if not any(part in f.parts for part in ['venv', '__pycache__', '.git', 'node_modules'])
        ]

        self.stats["total_files"] = len(python_files)

        logger.info(f"📂 找到 {len(python_files)} 个Python文件")

        # 逐个分析文件
        for i, file_path in enumerate(python_files, 1):
            logger.info(f"[{i}/{len(python_files)}] 分析: {file_path.relative_to(self.project_root)}")
            self._analyze_file(str(file_path))

        # 后处理：解析关系中的名字引用
        self._resolve_references()

        # 更新统计
        self.stats["total_classes"] = sum(1 for e in self.all_entities if e.type == "class")
        self.stats["total_functions"] = sum(1 for e in self.all_entities if e.type in ["function", "method"])
        self.stats["total_relations"] = len(self.all_relations)

        logger.info("\n" + "="*60)
        logger.info("✅ 分析完成！")
        logger.info(f"   文件数: {self.stats['total_files']}")
        logger.info(f"   类数量: {self.stats['total_classes']}")
        logger.info(f"   函数数: {self.stats['total_functions']}")
        logger.info(f"   关系数: {self.stats['total_relations']}")
        logger.info("="*60)

        return {
            "entities": [asdict(e) for e in self.all_entities],
            "relations": [asdict(r) for r in self.all_relations],
            "stats": self.stats
        }

    def _analyze_file(self, file_path: str):
        """分析单个文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
                self.stats["total_lines"] += len(source_code.splitlines())

            analyzer = PythonCodeAnalyzer(file_path, str(self.project_root))
            entities, relations = analyzer.analyze(source_code)

            self.all_entities.extend(entities)
            self.all_relations.extend(relations)

        except Exception as e:
            logger.info(f"  ⚠️  错误: {e}")

    def _resolve_references(self):
        """解析关系中的名字引用为实际ID"""
        # 构建名字->ID映射
        name_to_id = {}
        for entity in self.all_entities:
            name_to_id[entity.qualified_name] = entity.id
            name_to_id[entity.name] = entity.id  # 简短名字也映射

        # 更新关系中的target_id
        for relation in self.all_relations:
            if relation.target_id in name_to_id:
                relation.target_id = name_to_id[relation.target_id]

    def export_json(self, output_path: str):
        """导出为JSON"""
        data = {
            "entities": [asdict(e) for e in self.all_entities],
            "relations": [asdict(r) for r in self.all_relations],
            "stats": self.stats
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"💾 导出到: {output_path}")

    def generate_graph_summary(self) -> str:
        """生成图谱摘要"""
        summary = []
        summary.append("# 代码知识图谱摘要\n")
        summary.append(f"**项目**: {self.project_root.name}\n")
        summary.append(f"**文件数**: {self.stats['total_files']}\n")
        summary.append(f"**代码行**: {self.stats['total_lines']}\n\n")

        summary.append("## 实体统计\n")
        summary.append(f"- 类: {self.stats['total_classes']}\n")
        summary.append(f"- 函数/方法: {self.stats['total_functions']}\n\n")

        summary.append("## 主要模块\n")
        # 按文件路径分组
        files = set(e.file_path for e in self.all_entities)
        for file in sorted(files)[:10]:  # 前10个文件
            entities_in_file = [e for e in self.all_entities if e.file_path == file]
            summary.append(f"- `{file}`: {len(entities_in_file)} 个实体\n")

        return "".join(summary)


# ==================== 测试代码 ====================

def main():
    """测试主函数"""
    import sys

    if len(sys.argv) < 2:
        logger.info("用法: python code_analyzer.py <project_path>")
        logger.info("示例: python code_analyzer.py /Users/mac/Downloads/MCP")
        sys.exit(1)

    project_path = sys.argv[1]

    # 创建分析器
    analyzer = ProjectAnalyzer(project_path)

    # 分析项目
    result = analyzer.analyze_project()

    # 导出JSON
    output_path = Path(project_path) / "code_knowledge_graph.json"
    analyzer.export_json(str(output_path))

    # 生成摘要
    summary = analyzer.generate_graph_summary()
    logger.info("\n" + summary)

    summary_path = Path(project_path) / "code_analysis_summary.md"
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write(summary)
    logger.info(f"📄 摘要保存到: {summary_path}")


if __name__ == "__main__":
    main()

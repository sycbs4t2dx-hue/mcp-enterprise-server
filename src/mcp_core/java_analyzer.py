#!/usr/bin/env python3
"""
Java代码分析器

使用javalang库解析Java代码，提取类、方法、字段等信息
"""

import os
from typing import List, Tuple, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass

try:
    import javalang
except ImportError:
    print("❌ javalang未安装，请运行: pip install javalang")
    raise

from .code_analyzer import CodeEntity, CodeRelation


class JavaCodeAnalyzer:
    """Java代码分析器"""

    def __init__(self, file_path: str, project_root: str):
        self.file_path = file_path
        self.project_root = project_root
        self.relative_path = os.path.relpath(file_path, project_root)

        # 存储
        self.entities: List[CodeEntity] = []
        self.relations: List[CodeRelation] = []

        # 上下文
        self.current_package: Optional[str] = None
        self.current_class: Optional[str] = None
        self.entity_map: Dict[str, CodeEntity] = {}

    def analyze(self, source_code: str) -> Tuple[List[CodeEntity], List[CodeRelation]]:
        """分析Java源代码"""
        try:
            # 解析Java代码
            tree = javalang.parse.parse(source_code)

            # 提取package
            if tree.package:
                self.current_package = tree.package.name

            # 提取imports
            for imp in tree.imports:
                self._process_import(imp)

            # 提取类型定义
            for path, node in tree.filter(javalang.tree.TypeDeclaration):
                self._process_type_declaration(node)

            return self.entities, self.relations

        except javalang.parser.JavaSyntaxError as e:
            print(f"⚠️  Java语法错误 {self.file_path}: {e}")
            return [], []
        except Exception as e:
            print(f"⚠️  分析失败 {self.file_path}: {e}")
            return [], []

    def _generate_id(self, type_str: str, name: str, line: int = 0) -> str:
        """生成唯一ID"""
        import hashlib
        key = f"{self.relative_path}:{type_str}:{name}:{line}"
        return hashlib.md5(key.encode()).hexdigest()[:16]

    def _get_qualified_name(self, name: str) -> str:
        """获取完全限定名"""
        parts = []
        if self.current_package:
            parts.append(self.current_package)
        if self.current_class:
            parts.append(self.current_class)
        parts.append(name)
        return ".".join(parts)

    def _process_import(self, imp):
        """
        处理import语句，建立依赖关系

        Args:
            imp: javalang.tree.Import对象
        """
        import_path = imp.path  # 如 "java.util.List"
        is_static = imp.static  # 是否静态导入
        is_wildcard = imp.wildcard  # 是否通配符导入

        # 1. 确定导入类型
        if is_static:
            import_type = "static_wildcard" if is_wildcard else "static_single"
        else:
            import_type = "wildcard" if is_wildcard else "single"

        # 2. 提取被导入的类/包名
        if is_wildcard:
            # 通配符导入：记录包名
            imported_entity = import_path  # 如 "java.util"
            target_name = f"{import_path}.*"
        else:
            # 单类导入：记录完整类名
            imported_entity = import_path  # 如 "java.util.List"
            # 提取简单类名 (如 "List")
            target_name = import_path.split(".")[-1]

        # 3. 生成import关系ID
        line_num = imp.position.line if hasattr(imp, 'position') and imp.position else 0
        import_id = self._generate_id("import", imported_entity, line_num)

        # 4. 创建CodeEntity记录import
        import_entity = CodeEntity(
            id=import_id,
            type="import",
            name=target_name,
            qualified_name=imported_entity,
            file_path=self.relative_path,
            line_number=line_num,
            end_line=line_num,
            signature=f"import {'static ' if is_static else ''}{import_path}{'.*' if is_wildcard else ''}",
            metadata={
                "import_type": import_type,
                "is_static": is_static,
                "is_wildcard": is_wildcard,
                "package": ".".join(import_path.split(".")[:-1]) if not is_wildcard else import_path,
                "simple_name": target_name
            }
        )

        self.entities.append(import_entity)

        # 5. 建立import关系 (文件级别依赖)
        self.relations.append(CodeRelation(
            source_id=self.file_path,  # 当前文件依赖于imported_entity
            target_id=imported_entity,
            relation_type="imports",
            metadata={
                "import_type": import_type,
                "simple_name": target_name,
                "line": line_num
            }
        ))

        # 6. 存储到import映射表 (用于后续类型解析)
        if not hasattr(self, 'import_map'):
            self.import_map = {}

        self.import_map[target_name] = imported_entity

    def _process_type_declaration(self, node):
        """处理类型声明（类、接口、枚举）"""

        # 确定类型
        if isinstance(node, javalang.tree.ClassDeclaration):
            entity_type = "class"
        elif isinstance(node, javalang.tree.InterfaceDeclaration):
            entity_type = "interface"
        elif isinstance(node, javalang.tree.EnumDeclaration):
            entity_type = "enum"
        else:
            entity_type = "class"

        # 创建实体
        qualified_name = self._get_qualified_name(node.name)
        entity_id = self._generate_id(entity_type, node.name)

        # 提取文档注释
        docstring = node.documentation if hasattr(node, 'documentation') else None

        # 提取修饰符
        modifiers = node.modifiers if hasattr(node, 'modifiers') else []

        # 元数据
        metadata = {
            "modifiers": modifiers,
            "annotations": [],
            "type_parameters": []
        }

        # 处理注解
        if hasattr(node, 'annotations') and node.annotations:
            for anno in node.annotations:
                metadata["annotations"].append(anno.name)

        # 处理泛型
        if hasattr(node, 'type_parameters') and node.type_parameters:
            for tp in node.type_parameters:
                metadata["type_parameters"].append(tp.name)

        # 处理继承
        if hasattr(node, 'extends') and node.extends:
            metadata["extends"] = node.extends.name if hasattr(node.extends, 'name') else str(node.extends)

        # 处理实现
        if hasattr(node, 'implements') and node.implements:
            metadata["implements"] = [impl.name if hasattr(impl, 'name') else str(impl) for impl in node.implements]

        # 创建实体
        entity = CodeEntity(
            id=entity_id,
            type=entity_type,
            name=node.name,
            qualified_name=qualified_name,
            file_path=self.relative_path,
            line_number=node.position.line if hasattr(node, 'position') and node.position else 0,
            end_line=0,
            docstring=docstring,
            metadata=metadata
        )

        self.entities.append(entity)
        self.entity_map[qualified_name] = entity

        # 处理继承关系
        if hasattr(node, 'extends') and node.extends:
            extends_name = node.extends.name if hasattr(node.extends, 'name') else str(node.extends)
            self.relations.append(CodeRelation(
                source_id=entity_id,
                target_id=extends_name,  # 稍后解析
                relation_type="extends",
                metadata={"parent_class": extends_name}
            ))

        # 处理实现关系
        if hasattr(node, 'implements') and node.implements:
            for impl in node.implements:
                impl_name = impl.name if hasattr(impl, 'name') else str(impl)
                self.relations.append(CodeRelation(
                    source_id=entity_id,
                    target_id=impl_name,  # 稍后解析
                    relation_type="implements",
                    metadata={"interface": impl_name}
                ))

        # 保存当前类上下文
        old_class = self.current_class
        self.current_class = node.name

        # 处理字段
        if hasattr(node, 'fields'):
            for field in node.fields:
                self._process_field(field, entity_id)

        # 处理方法
        if hasattr(node, 'methods'):
            for method in node.methods:
                self._process_method(method, entity_id)

        # 恢复上下文
        self.current_class = old_class

    def _process_field(self, field, parent_id: str):
        """处理字段/属性"""
        for declarator in field.declarators:
            field_name = declarator.name
            qualified_name = self._get_qualified_name(field_name)
            entity_id = self._generate_id("field", field_name)

            # 类型信息
            field_type = str(field.type.name) if hasattr(field.type, 'name') else str(field.type)

            # 修饰符
            modifiers = field.modifiers if hasattr(field, 'modifiers') else []

            entity = CodeEntity(
                id=entity_id,
                type="variable",
                name=field_name,
                qualified_name=qualified_name,
                file_path=self.relative_path,
                line_number=field.position.line if hasattr(field, 'position') and field.position else 0,
                end_line=0,
                signature=f"{field_type} {field_name}",
                parent_id=parent_id,
                metadata={
                    "field_type": field_type,
                    "modifiers": modifiers,
                    "annotations": [anno.name for anno in field.annotations] if hasattr(field, 'annotations') and field.annotations else []
                }
            )

            self.entities.append(entity)

            # 建立包含关系
            self.relations.append(CodeRelation(
                source_id=parent_id,
                target_id=entity_id,
                relation_type="contains",
                metadata={"type": "field"}
            ))

    def _process_method(self, method, parent_id: str):
        """处理方法"""
        method_name = method.name
        qualified_name = self._get_qualified_name(method_name)
        entity_id = self._generate_id("method", method_name)

        # 返回类型
        return_type = str(method.return_type.name) if method.return_type and hasattr(method.return_type, 'name') else "void"

        # 参数
        params = []
        if method.parameters:
            for param in method.parameters:
                param_type = str(param.type.name) if hasattr(param.type, 'name') else str(param.type)
                params.append({
                    "name": param.name,
                    "type": param_type
                })

        # 生成签名
        param_str = ", ".join([f"{p['type']} {p['name']}" for p in params])
        signature = f"{return_type} {method_name}({param_str})"

        # 修饰符
        modifiers = method.modifiers if hasattr(method, 'modifiers') else []

        # 注解
        annotations = []
        if hasattr(method, 'annotations') and method.annotations:
            for anno in method.annotations:
                annotations.append(anno.name)

        # 文档
        docstring = method.documentation if hasattr(method, 'documentation') else None

        entity = CodeEntity(
            id=entity_id,
            type="method",
            name=method_name,
            qualified_name=qualified_name,
            file_path=self.relative_path,
            line_number=method.position.line if hasattr(method, 'position') and method.position else 0,
            end_line=0,
            signature=signature,
            parent_id=parent_id,
            docstring=docstring,
            metadata={
                "return_type": return_type,
                "parameters": params,
                "modifiers": modifiers,
                "annotations": annotations,
                "throws": [str(t) for t in method.throws] if hasattr(method, 'throws') and method.throws else []
            }
        )

        self.entities.append(entity)

        # 建立包含关系
        self.relations.append(CodeRelation(
            source_id=parent_id,
            target_id=entity_id,
            relation_type="contains",
            metadata={"type": "method"}
        ))

        # 分析方法体中的调用关系
        if method.body:
            self._analyze_method_body(method.body, entity_id)

    def _analyze_method_body(self, statements, method_id: str):
        """分析方法体，提取方法调用"""
        if not statements:
            return

        # 遍历所有语句，查找方法调用
        for path, node in statements.filter(javalang.tree.MethodInvocation):
            if isinstance(node, javalang.tree.MethodInvocation):
                called_method = node.member
                # 创建调用关系
                self.relations.append(CodeRelation(
                    source_id=method_id,
                    target_id=called_method,  # 稍后解析为实际ID
                    relation_type="calls",
                    metadata={"method": called_method}
                ))

    def build_dependency_graph(self) -> Dict[str, List[str]]:
        """
        构建类依赖关系图

        Returns:
            {
                "com.example.UserService": [
                    "com.example.UserRepository",
                    "com.example.User",
                    "java.util.List"
                ],
                ...
            }
        """
        dependency_graph = {}

        # 获取当前文件定义的所有类
        defined_classes = [
            entity.qualified_name
            for entity in self.entities
            if entity.type in ["class", "interface", "enum"]
        ]

        # 对每个类，收集其依赖
        for class_name in defined_classes:
            dependencies = set()

            # 1. 从import关系提取
            for relation in self.relations:
                if relation.relation_type == "imports":
                    imported_class = relation.target_id
                    dependencies.add(imported_class)

            # 2. 从继承/实现关系提取
            for relation in self.relations:
                if relation.relation_type in ["extends", "implements"]:
                    parent_class = relation.target_id
                    # 解析为完全限定名 (通过import_map)
                    if hasattr(self, 'import_map') and parent_class in self.import_map:
                        full_name = self.import_map[parent_class]
                        dependencies.add(full_name)
                    else:
                        dependencies.add(parent_class)

            # 3. 从字段类型提取
            for entity in self.entities:
                if entity.type == "variable" and entity.metadata.get("field_type"):
                    field_type = entity.metadata["field_type"]
                    simple_type = field_type.split("<")[0].split("[")[0]
                    if hasattr(self, 'import_map') and simple_type in self.import_map:
                        dependencies.add(self.import_map[simple_type])

            dependency_graph[class_name] = list(dependencies)

        return dependency_graph

    @staticmethod
    def detect_circular_dependencies(dependency_graph: Dict[str, List[str]]) -> List[List[str]]:
        """
        检测循环依赖

        Args:
            dependency_graph: 依赖关系图

        Returns:
            循环依赖链列表，如: [
                ["A", "B", "C", "A"],  # A→B→C→A 形成循环
                ...
            ]
        """
        cycles = []

        def dfs(node, path, visited):
            if node in path:
                # 发现循环
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                cycles.append(cycle)
                return

            if node in visited:
                return

            visited.add(node)
            path.append(node)

            for neighbor in dependency_graph.get(node, []):
                dfs(neighbor, path[:], visited)

            path.pop()

        visited = set()
        for node in dependency_graph.keys():
            if node not in visited:
                dfs(node, [], visited)

        return cycles

    @staticmethod
    def analyze_impact(class_name: str, dependency_graph: Dict[str, List[str]]) -> Dict[str, Any]:
        """
        分析某个类修改的影响范围

        Args:
            class_name: 被修改的类名
            dependency_graph: 依赖关系图

        Returns:
            {
                "direct_impact": ["直接依赖此类的类"],
                "indirect_impact": ["间接依赖此类的类"],
                "impact_level": 3,  # 影响层级深度
                "total_affected": 10  # 总受影响类数
            }
        """
        # 构建反向依赖图 (谁依赖我)
        reverse_graph = {}
        for source, targets in dependency_graph.items():
            for target in targets:
                if target not in reverse_graph:
                    reverse_graph[target] = []
                reverse_graph[target].append(source)

        # BFS查找所有受影响的类
        direct_impact = reverse_graph.get(class_name, [])

        all_impact = set(direct_impact)
        queue = list(direct_impact)
        level = 1
        max_level = 1

        while queue:
            next_level = []
            for node in queue:
                for dependent in reverse_graph.get(node, []):
                    if dependent not in all_impact:
                        all_impact.add(dependent)
                        next_level.append(dependent)

            if next_level:
                level += 1
                max_level = level
                queue = next_level
            else:
                break

        indirect_impact = list(all_impact - set(direct_impact))

        return {
            "direct_impact": direct_impact,
            "indirect_impact": indirect_impact,
            "impact_level": max_level,
            "total_affected": len(all_impact)
        }


# ==================== 测试代码 ====================

def test_java_analyzer():
    """测试Java分析器"""

    # 测试代码
    java_code = """
package com.example.service;

import java.util.List;
import com.example.model.User;

/**
 * 用户服务类
 */
public class UserService {

    private UserRepository repository;

    /**
     * 获取用户
     */
    public User getUser(String userId) {
        return repository.findById(userId);
    }

    /**
     * 创建用户
     */
    public User createUser(String username, String email) {
        User user = new User(username, email);
        return repository.save(user);
    }
}
"""

    analyzer = JavaCodeAnalyzer("test/UserService.java", "test")
    entities, relations = analyzer.analyze(java_code)

    print("=" * 60)
    print("Java代码分析测试")
    print("=" * 60)

    print(f"\n提取实体: {len(entities)}个")
    for entity in entities:
        print(f"  - {entity.type}: {entity.name}")
        if entity.signature:
            print(f"    签名: {entity.signature}")

    print(f"\n提取关系: {len(relations)}个")
    for relation in relations:
        print(f"  - {relation.relation_type}: {relation.source_id} → {relation.target_id}")


if __name__ == "__main__":
    test_java_analyzer()

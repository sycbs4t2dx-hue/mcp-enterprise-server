#!/usr/bin/env python3
"""
Swift/iOS代码分析器

使用正则表达式解析Swift代码，提取类、结构体、协议、方法等信息
"""

import os
import re
from typing import List, Tuple, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass

from .code_analyzer import CodeEntity, CodeRelation


class SwiftCodeAnalyzer:
    """Swift代码分析器"""

    def __init__(self, file_path: str, project_root: str):
        self.file_path = file_path
        self.project_root = project_root
        self.relative_path = os.path.relpath(file_path, project_root)

        # 存储
        self.entities: List[CodeEntity] = []
        self.relations: List[CodeRelation] = []

        # 上下文
        self.current_namespace: Optional[str] = None
        self.current_class: Optional[str] = None

    def analyze(self, source_code: str) -> Tuple[List[CodeEntity], List[CodeRelation]]:
        """分析Swift源代码"""
        try:
            lines = source_code.split('\n')

            # 提取import语句
            self._extract_imports(lines)

            # 提取类、结构体、协议
            self._extract_types(source_code, lines)

            # 提取顶层函数
            self._extract_top_level_functions(source_code, lines)

            # 提取扩展
            self._extract_extensions(source_code, lines)

            return self.entities, self.relations

        except Exception as e:
            logger.info(f"⚠️  Swift分析失败 {self.file_path}: {e}")
            return [], []

    def _generate_id(self, type_str: str, name: str, line: int = 0) -> str:
        """生成唯一ID"""
        import hashlib
        key = f"{self.relative_path}:{type_str}:{name}:{line}"
        return hashlib.md5(key.encode()).hexdigest()[:16]

    def _get_qualified_name(self, name: str) -> str:
        """获取完全限定名"""
        parts = []
        if self.current_namespace:
            parts.append(self.current_namespace)
        if self.current_class:
            parts.append(self.current_class)
        parts.append(name)
        return ".".join(parts)

    def _extract_imports(self, lines: List[str]):
        """提取import语句"""
        for i, line in enumerate(lines, 1):
            match = re.match(r'^\s*import\s+(\w+)', line.strip())
            if match:
                module_name = match.group(1)
                entity_id = self._generate_id("import", module_name, i)

                entity = CodeEntity(
                    id=entity_id,
                    type="import",
                    name=module_name,
                    qualified_name=module_name,
                    file_path=self.relative_path,
                    line_number=i,
                    end_line=i,
                    metadata={"import_type": "module"}
                )
                self.entities.append(entity)

    def _extract_types(self, source_code: str, lines: List[str]):
        """提取类、结构体、协议、枚举"""

        # 匹配类定义: class ClassName: SuperClass, Protocol { }
        # 匹配结构体: struct StructName: Protocol { }
        # 匹配协议: protocol ProtocolName: SuperProtocol { }
        # 匹配枚举: enum EnumName: RawType { }

        patterns = [
            (r'(class|struct|protocol|enum)\s+(\w+)(?:\s*:\s*([^{]+))?\s*\{', None),
        ]

        for pattern, _ in patterns:
            for match in re.finditer(pattern, source_code, re.MULTILINE):
                type_keyword = match.group(1)  # class, struct, protocol, enum
                type_name = match.group(2)
                inheritance = match.group(3).strip() if match.group(3) else None

                # 计算行号
                line_number = source_code[:match.start()].count('\n') + 1

                # 映射类型
                entity_type_map = {
                    "class": "class",
                    "struct": "struct",
                    "protocol": "interface",
                    "enum": "enum"
                }
                entity_type = entity_type_map.get(type_keyword, "class")

                qualified_name = self._get_qualified_name(type_name)
                entity_id = self._generate_id(entity_type, type_name, line_number)

                # 解析继承和协议
                supers = []
                protocols = []
                if inheritance:
                    parts = [p.strip() for p in inheritance.split(',')]
                    supers = parts

                # 提取文档注释
                docstring = self._extract_docstring(lines, line_number - 1)

                # 元数据
                metadata = {
                    "swift_type": type_keyword,
                    "modifiers": self._extract_modifiers(lines[line_number - 1] if line_number <= len(lines) else ""),
                    "inheritance": supers,
                    "is_final": "final" in lines[line_number - 1] if line_number <= len(lines) else False
                }

                entity = CodeEntity(
                    id=entity_id,
                    type=entity_type,
                    name=type_name,
                    qualified_name=qualified_name,
                    file_path=self.relative_path,
                    line_number=line_number,
                    end_line=0,
                    docstring=docstring,
                    metadata=metadata
                )

                self.entities.append(entity)

                # 建立继承关系
                for super_type in supers:
                    self.relations.append(CodeRelation(
                        source_id=entity_id,
                        target_id=super_type.strip(),
                        relation_type="inherits",
                        metadata={"super_type": super_type.strip()}
                    ))

                # 提取类型体内的方法和属性
                old_class = self.current_class
                self.current_class = type_name

                # 查找类型体的结束位置
                body_start = match.end()
                body_end = self._find_matching_brace(source_code, body_start)

                if body_end != -1:
                    body = source_code[body_start:body_end]
                    self._extract_properties(body, lines, line_number)
                    self._extract_methods(body, lines, line_number, entity_id)

                self.current_class = old_class

    def _extract_properties(self, body: str, lines: List[str], start_line: int):
        """提取属性"""
        # var name: Type
        # let constant: Type
        pattern = r'(var|let)\s+(\w+)\s*:\s*([^\n=]+)'

        for match in re.finditer(pattern, body):
            prop_type = match.group(1)  # var or let
            prop_name = match.group(2)
            prop_type_annotation = match.group(3).strip()

            line_offset = body[:match.start()].count('\n')
            line_number = start_line + line_offset

            qualified_name = self._get_qualified_name(prop_name)
            entity_id = self._generate_id("property", prop_name, line_number)

            entity = CodeEntity(
                id=entity_id,
                type="variable",
                name=prop_name,
                qualified_name=qualified_name,
                file_path=self.relative_path,
                line_number=line_number,
                end_line=line_number,
                signature=f"{prop_type} {prop_name}: {prop_type_annotation}",
                parent_id=self._generate_id("class", self.current_class) if self.current_class else None,
                metadata={
                    "property_type": prop_type,
                    "type_annotation": prop_type_annotation,
                    "is_mutable": prop_type == "var"
                }
            )

            self.entities.append(entity)

    def _extract_methods(self, body: str, lines: List[str], start_line: int, parent_id: str):
        """提取方法"""
        # func methodName(param: Type) -> ReturnType { }
        # deinit { }

        patterns = [
            r'func\s+(\w+)\s*\(([^)]*)\)(?:\s*->\s*([^\{]+))?\s*\{',
            r'(init|deinit)\s*\(([^)]*)\)\s*\{',
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, body):
                if 'func' in pattern:
                    method_name = match.group(1)
                    parameters = match.group(2)
                    return_type = match.group(3).strip() if match.group(3) else "Void"
                else:
                    method_name = match.group(1)  # init or deinit
                    parameters = match.group(2)
                    return_type = "" if method_name == "deinit" else "Self"

                line_offset = body[:match.start()].count('\n')
                line_number = start_line + line_offset

                qualified_name = self._get_qualified_name(method_name)
                entity_id = self._generate_id("method", method_name, line_number)

                # 解析参数
                params = self._parse_parameters(parameters)

                # 生成签名
                param_str = ", ".join([f"{p['label']}: {p['type']}" for p in params])
                if return_type and return_type != "Void":
                    signature = f"func {method_name}({param_str}) -> {return_type}"
                else:
                    signature = f"func {method_name}({param_str})"

                # 提取修饰符
                modifiers = self._extract_modifiers(lines[line_number - 1] if line_number <= len(lines) else "")

                entity = CodeEntity(
                    id=entity_id,
                    type="method",
                    name=method_name,
                    qualified_name=qualified_name,
                    file_path=self.relative_path,
                    line_number=line_number,
                    end_line=0,
                    signature=signature,
                    parent_id=parent_id,
                    metadata={
                        "parameters": params,
                        "return_type": return_type,
                        "modifiers": modifiers,
                        "is_init": method_name == "init",
                        "is_deinit": method_name == "deinit"
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

    def _extract_top_level_functions(self, source_code: str, lines: List[str]):
        """提取顶层函数"""
        # 这里简化处理，只提取不在类型内部的函数
        pass

    def _extract_extensions(self, source_code: str, lines: List[str]):
        """提取扩展"""
        # extension TypeName: Protocol { }
        pattern = r'extension\s+(\w+)(?:\s*:\s*([^{]+))?\s*\{'

        for match in re.finditer(pattern, source_code):
            type_name = match.group(1)
            protocols = match.group(2).strip() if match.group(2) else None

            line_number = source_code[:match.start()].count('\n') + 1

            entity_id = self._generate_id("extension", type_name, line_number)

            entity = CodeEntity(
                id=entity_id,
                type="extension",
                name=f"{type_name}Extension",
                qualified_name=f"{type_name}.Extension",
                file_path=self.relative_path,
                line_number=line_number,
                end_line=0,
                metadata={
                    "extended_type": type_name,
                    "protocols": [p.strip() for p in protocols.split(',')] if protocols else []
                }
            )

            self.entities.append(entity)

            # 建立扩展关系
            self.relations.append(CodeRelation(
                source_id=entity_id,
                target_id=type_name,
                relation_type="extends",
                metadata={"type": "extension"}
            ))

    def _parse_parameters(self, params_str: str) -> List[Dict[str, str]]:
        """解析参数列表"""
        if not params_str.strip():
            return []

        params = []
        # Swift参数: label name: Type, _ name: Type, name: Type
        for param in params_str.split(','):
            param = param.strip()
            if not param:
                continue

            # 简化解析
            parts = param.split(':')
            if len(parts) == 2:
                name_part = parts[0].strip()
                type_part = parts[1].strip()

                # 处理标签
                name_parts = name_part.split()
                if len(name_parts) == 2:
                    label = name_parts[0]
                    name = name_parts[1]
                else:
                    label = name_parts[0]
                    name = name_parts[0]

                params.append({
                    "label": label,
                    "name": name,
                    "type": type_part
                })

        return params

    def _extract_modifiers(self, line: str) -> List[str]:
        """提取修饰符"""
        modifiers = []
        keywords = ['public', 'private', 'internal', 'fileprivate', 'open',
                   'final', 'static', 'class', 'override', 'mutating', 'weak', 'unowned']

        for keyword in keywords:
            if re.search(rf'\b{keyword}\b', line):
                modifiers.append(keyword)

        return modifiers

    def _extract_docstring(self, lines: List[str], line_index: int) -> Optional[str]:
        """提取文档注释"""
        if line_index < 0:
            return None

        # Swift文档注释: /// 或 /** */
        docstring_lines = []

        # 向上查找 ///
        i = line_index - 1
        while i >= 0:
            line = lines[i].strip()
            if line.startswith('///'):
                docstring_lines.insert(0, line[3:].strip())
                i -= 1
            else:
                break

        if docstring_lines:
            return '\n'.join(docstring_lines)

        # 查找 /** */
        i = line_index - 1
        if i >= 0 and '/**' in lines[i]:
            # 简化处理
            return lines[i].strip()

        return None

    def _find_matching_brace(self, source: str, start: int) -> int:
        """查找匹配的大括号"""
        count = 1
        i = start

        while i < len(source) and count > 0:
            if source[i] == '{':
                count += 1
            elif source[i] == '}':
                count -= 1
            i += 1

        return i if count == 0 else -1


# ==================== 测试代码 ====================

def test_swift_analyzer():
    """测试Swift分析器"""

    swift_code = '''
import Foundation
import UIKit
import logging

logger = logging.getLogger(__name__)


/// 用户模型
public class User: Codable {
    var id: String
    var name: String
    var age: Int
    private var email: String?

    /// 初始化用户
    init(id: String, name: String, age: Int) {
        self.id = id
        self.name = name
        self.age = age
    }

    /// 获取用户显示名称
    public func getDisplayName() -> String {
        return name
    }

    /// 更新邮箱
    mutating func updateEmail(_ email: String) {
        self.email = email
    }
}

/// 用户服务协议
protocol UserServiceProtocol {
    func fetchUser(id: String) -> User?
    func saveUser(_ user: User)
}

/// 用户服务实现
class UserService: UserServiceProtocol {
    private var users: [String: User] = [:]

    func fetchUser(id: String) -> User? {
        return users[id]
    }

    func saveUser(_ user: User) {
        users[user.id] = user
    }
}

extension User {
    var isAdult: Bool {
        return age >= 18
    }
}
'''

    analyzer = SwiftCodeAnalyzer("Models/User.swift", "src")
    entities, relations = analyzer.analyze(swift_code)

    logger.info("=" * 60)
    logger.info("Swift代码分析测试")
    logger.info("=" * 60)

    logger.info(f"\n提取实体: {len(entities)}个")
    for entity in entities:
        logger.info(f"  - {entity.type}: {entity.name}")
        if entity.signature:
            logger.info(f"    签名: {entity.signature}")
        if entity.metadata:
            logger.info(f"    元数据: {entity.metadata}")

    logger.info(f"\n提取关系: {len(relations)}个")
    for relation in relations:
        logger.info(f"  - {relation.relation_type}: {relation.source_id} → {relation.target_id}")


if __name__ == "__main__":
    test_swift_analyzer()

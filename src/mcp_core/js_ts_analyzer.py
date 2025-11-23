"""
JavaScript/TypeScript代码分析器
支持ES6+, TypeScript, JSX/TSX
"""

import ast
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
import hashlib

from ..models.code_entity import CodeEntity, CodeRelation
from ..common.standard_logger import get_logger

logger = get_logger(__name__)


@dataclass
class JSCodeEntity:
    """JavaScript/TypeScript代码实体"""
    id: str
    type: str  # class, function, interface, type, enum, const, let, var
    name: str
    qualified_name: str
    file_path: str
    line_start: int
    line_end: int
    signature: Optional[str] = None
    docstring: Optional[str] = None
    modifiers: List[str] = field(default_factory=list)  # export, async, static, etc.
    decorators: List[str] = field(default_factory=list)  # TypeScript decorators
    generic_params: List[str] = field(default_factory=list)  # <T, K>
    metadata: Dict[str, Any] = field(default_factory=dict)


class JavaScriptTypeScriptAnalyzer:
    """
    JavaScript/TypeScript代码分析器

    支持特性：
    - ES6+ 语法（类、箭头函数、模块等）
    - TypeScript 类型注解
    - JSX/TSX 组件
    - 装饰器
    - 异步函数
    - 泛型
    """

    # 语言特定的关键字
    JS_KEYWORDS = {
        'class', 'function', 'const', 'let', 'var', 'async', 'await',
        'export', 'import', 'default', 'extends', 'implements',
        'interface', 'type', 'enum', 'namespace', 'module',
        'public', 'private', 'protected', 'static', 'readonly',
        'abstract', 'override', 'decorator'
    }

    # 常见框架模式
    FRAMEWORK_PATTERNS = {
        'react': {
            'component': r'(?:class|function)\s+(\w+)\s*(?:extends\s+(?:React\.)?Component|:\s*(?:React\.)?FC)',
            'hook': r'(?:const|function)\s+use[A-Z]\w*',
            'context': r'(?:const|let)\s+(\w+Context)\s*=\s*(?:React\.)?createContext',
        },
        'vue': {
            'component': r'export\s+default\s+(?:defineComponent|{\s*name:\s*["\'](\w+)["\'])',
            'composable': r'(?:export\s+)?(?:const|function)\s+use[A-Z]\w*',
            'store': r'export\s+const\s+use\w+Store\s*=\s*defineStore',
        },
        'angular': {
            'component': r'@Component\s*\([^)]*\)\s*(?:export\s+)?class\s+(\w+)',
            'service': r'@Injectable\s*\([^)]*\)\s*(?:export\s+)?class\s+(\w+)',
            'directive': r'@Directive\s*\([^)]*\)\s*(?:export\s+)?class\s+(\w+)',
        }
    }

    def __init__(self, file_path: str, project_root: str):
        self.file_path = Path(file_path)
        self.project_root = Path(project_root)
        self.relative_path = self.file_path.relative_to(self.project_root)

        # 判断文件类型
        self.is_typescript = self.file_path.suffix in ['.ts', '.tsx']
        self.is_jsx = self.file_path.suffix in ['.jsx', '.tsx']

        self.entities: List[CodeEntity] = []
        self.relations: List[CodeRelation] = []
        self.imports: Dict[str, str] = {}  # import名称 -> 来源
        self.exports: List[str] = []  # 导出的实体

    def analyze(self, source_code: str) -> Tuple[List[CodeEntity], List[CodeRelation]]:
        """分析JS/TS源代码"""
        try:
            # 清理源代码（移除注释等）
            cleaned_code = self._clean_source_code(source_code)

            # 提取导入
            self._extract_imports(cleaned_code)

            # 提取类
            self._extract_classes(cleaned_code)

            # 提取函数
            self._extract_functions(cleaned_code)

            # 提取接口和类型（TypeScript）
            if self.is_typescript:
                self._extract_interfaces(cleaned_code)
                self._extract_types(cleaned_code)
                self._extract_enums(cleaned_code)

            # 提取React组件（如果是JSX/TSX）
            if self.is_jsx:
                self._extract_react_components(cleaned_code)

            # 提取变量和常量
            self._extract_variables(cleaned_code)

            # 提取导出
            self._extract_exports(cleaned_code)

            # 建立关系
            self._build_relations()

            return self.entities, self.relations

        except Exception as e:
            logger.error(f"分析JS/TS文件失败 {self.file_path}: {e}")
            return [], []

    def _clean_source_code(self, source_code: str) -> str:
        """清理源代码，移除注释但保留JSDoc"""
        # 保留JSDoc注释
        jsdoc_pattern = r'/\*\*[\s\S]*?\*/'
        jsdocs = re.findall(jsdoc_pattern, source_code)

        # 移除单行注释
        source_code = re.sub(r'//.*$', '', source_code, flags=re.MULTILINE)

        # 移除多行注释（但不是JSDoc）
        source_code = re.sub(r'/\*(?!\*)[\s\S]*?\*/', '', source_code)

        return source_code

    def _generate_id(self, type: str, name: str, line: int) -> str:
        """生成唯一ID"""
        key = f"{self.relative_path}:{type}:{name}:{line}"
        return hashlib.md5(key.encode()).hexdigest()[:16]

    def _extract_imports(self, source_code: str):
        """提取导入语句"""
        # ES6 import
        import_patterns = [
            r'import\s+(\w+)\s+from\s+["\']([^"\']+)["\']',  # import X from 'y'
            r'import\s+\*\s+as\s+(\w+)\s+from\s+["\']([^"\']+)["\']',  # import * as X from 'y'
            r'import\s+{([^}]+)}\s+from\s+["\']([^"\']+)["\']',  # import { X } from 'y'
            r'import\s+["\']([^"\']+)["\']',  # import 'y'
        ]

        for pattern in import_patterns:
            for match in re.finditer(pattern, source_code):
                if len(match.groups()) == 2:
                    imported, source = match.groups()
                    self.imports[imported.strip()] = source
                elif len(match.groups()) == 1:
                    # Side effect import
                    source = match.group(1)
                    self.imports[f"_side_effect_{len(self.imports)}"] = source

        # CommonJS require
        require_pattern = r'(?:const|let|var)\s+(\w+)\s*=\s*require\s*\(["\']([^"\']+)["\']\)'
        for match in re.finditer(require_pattern, source_code):
            imported, source = match.groups()
            self.imports[imported] = source

    def _extract_classes(self, source_code: str):
        """提取类定义"""
        # 支持ES6类和TypeScript类
        class_pattern = r'''
            (?:export\s+)?                           # 可选的export
            (?:default\s+)?                          # 可选的default
            (?:abstract\s+)?                         # 可选的abstract（TS）
            class\s+(\w+)                            # 类名
            (?:<([^>]+)>)?                          # 可选的泛型参数（TS）
            (?:\s+extends\s+([^\s{]+))?             # 可选的extends
            (?:\s+implements\s+([^\s{]+))?          # 可选的implements（TS）
            \s*{                                     # 类体开始
        '''

        for match in re.finditer(class_pattern, source_code, re.VERBOSE):
            class_name = match.group(1)
            generic_params = match.group(2)
            extends = match.group(3)
            implements = match.group(4)

            # 获取行号
            line_num = source_code[:match.start()].count('\n') + 1

            # 提取类体
            class_body_start = match.end()
            class_body_end = self._find_matching_brace(source_code, class_body_start - 1)
            class_body = source_code[class_body_start:class_body_end]

            # 创建实体
            entity = CodeEntity(
                id=self._generate_id('class', class_name, line_num),
                type='class',
                name=class_name,
                qualified_name=f"{self.relative_path}:{class_name}",
                file_path=str(self.file_path),
                line_start=line_num,
                line_end=line_num + class_body.count('\n'),
                signature=match.group(0).strip(),
                metadata={
                    'language': 'typescript' if self.is_typescript else 'javascript',
                    'generic_params': generic_params.split(',') if generic_params else [],
                    'extends': extends,
                    'implements': implements.split(',') if implements else []
                }
            )
            self.entities.append(entity)

            # 提取类成员
            self._extract_class_members(class_body, class_name, line_num)

    def _extract_functions(self, source_code: str):
        """提取函数定义"""
        # 支持多种函数定义方式
        function_patterns = [
            # 传统函数
            r'(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*(?:<([^>]+)>)?\s*\(([^)]*)\)(?:\s*:\s*([^\s{]+))?\s*{',
            # 箭头函数
            r'(?:export\s+)?(?:const|let|var)\s+(\w+)\s*(?:<([^>]+)>)?\s*=\s*(?:async\s+)?\(([^)]*)\)(?:\s*:\s*([^\s{]+))?\s*=>\s*[{(]',
            # 对象方法
            r'(\w+)\s*(?:<([^>]+)>)?\s*\(([^)]*)\)(?:\s*:\s*([^\s{]+))?\s*{',
        ]

        for pattern in function_patterns:
            for match in re.finditer(pattern, source_code):
                func_name = match.group(1)
                generic_params = match.group(2)
                params = match.group(3)
                return_type = match.group(4) if len(match.groups()) >= 4 else None

                # 跳过类内部的方法（已在类提取中处理）
                if self._is_inside_class(source_code, match.start()):
                    continue

                line_num = source_code[:match.start()].count('\n') + 1

                # 创建函数签名
                signature = f"{func_name}({params})"
                if return_type:
                    signature += f": {return_type}"

                entity = CodeEntity(
                    id=self._generate_id('function', func_name, line_num),
                    type='function',
                    name=func_name,
                    qualified_name=f"{self.relative_path}:{func_name}",
                    file_path=str(self.file_path),
                    line_start=line_num,
                    line_end=line_num,  # 简化处理
                    signature=signature,
                    metadata={
                        'language': 'typescript' if self.is_typescript else 'javascript',
                        'is_async': 'async' in match.group(0),
                        'is_arrow': '=>' in match.group(0),
                        'generic_params': generic_params.split(',') if generic_params else [],
                        'return_type': return_type
                    }
                )
                self.entities.append(entity)

    def _extract_interfaces(self, source_code: str):
        """提取TypeScript接口"""
        interface_pattern = r'''
            (?:export\s+)?                    # 可选的export
            interface\s+(\w+)                 # 接口名
            (?:<([^>]+)>)?                    # 可选的泛型参数
            (?:\s+extends\s+([^\s{]+))?      # 可选的extends
            \s*{                              # 接口体开始
        '''

        for match in re.finditer(interface_pattern, source_code, re.VERBOSE):
            interface_name = match.group(1)
            generic_params = match.group(2)
            extends = match.group(3)

            line_num = source_code[:match.start()].count('\n') + 1

            entity = CodeEntity(
                id=self._generate_id('interface', interface_name, line_num),
                type='interface',
                name=interface_name,
                qualified_name=f"{self.relative_path}:{interface_name}",
                file_path=str(self.file_path),
                line_start=line_num,
                line_end=line_num,
                signature=match.group(0).strip(),
                metadata={
                    'language': 'typescript',
                    'generic_params': generic_params.split(',') if generic_params else [],
                    'extends': extends.split(',') if extends else []
                }
            )
            self.entities.append(entity)

    def _extract_types(self, source_code: str):
        """提取TypeScript类型别名"""
        type_pattern = r'(?:export\s+)?type\s+(\w+)(?:<([^>]+)>)?\s*=\s*([^;]+);'

        for match in re.finditer(type_pattern, source_code):
            type_name = match.group(1)
            generic_params = match.group(2)
            type_def = match.group(3)

            line_num = source_code[:match.start()].count('\n') + 1

            entity = CodeEntity(
                id=self._generate_id('type', type_name, line_num),
                type='type_alias',
                name=type_name,
                qualified_name=f"{self.relative_path}:{type_name}",
                file_path=str(self.file_path),
                line_start=line_num,
                line_end=line_num,
                signature=f"type {type_name} = {type_def}",
                metadata={
                    'language': 'typescript',
                    'generic_params': generic_params.split(',') if generic_params else [],
                    'definition': type_def
                }
            )
            self.entities.append(entity)

    def _extract_enums(self, source_code: str):
        """提取TypeScript枚举"""
        enum_pattern = r'(?:export\s+)?(?:const\s+)?enum\s+(\w+)\s*{'

        for match in re.finditer(enum_pattern, source_code):
            enum_name = match.group(1)
            line_num = source_code[:match.start()].count('\n') + 1

            # 提取枚举成员
            enum_start = match.end()
            enum_end = self._find_matching_brace(source_code, match.end() - 1)
            enum_body = source_code[enum_start:enum_end]

            # 解析枚举成员
            members = []
            for member_match in re.finditer(r'(\w+)(?:\s*=\s*([^,}]+))?', enum_body):
                member_name = member_match.group(1)
                member_value = member_match.group(2)
                members.append({
                    'name': member_name,
                    'value': member_value.strip() if member_value else None
                })

            entity = CodeEntity(
                id=self._generate_id('enum', enum_name, line_num),
                type='enum',
                name=enum_name,
                qualified_name=f"{self.relative_path}:{enum_name}",
                file_path=str(self.file_path),
                line_start=line_num,
                line_end=line_num + enum_body.count('\n'),
                signature=f"enum {enum_name}",
                metadata={
                    'language': 'typescript',
                    'is_const': 'const' in match.group(0),
                    'members': members
                }
            )
            self.entities.append(entity)

    def _extract_react_components(self, source_code: str):
        """提取React组件"""
        # 函数组件
        func_component_patterns = [
            # 带类型注解的函数组件
            r'(?:export\s+)?(?:const|function)\s+(\w+)\s*:\s*(?:React\.)?F[CR](?:<[^>]+>)?\s*=',
            # 返回JSX的函数
            r'(?:export\s+)?function\s+([A-Z]\w*)\s*\([^)]*\)\s*{[^}]*return\s*(?:<|\()',
            # 箭头函数组件
            r'(?:export\s+)?const\s+([A-Z]\w*)\s*=\s*(?:\([^)]*\)|[^=])\s*=>\s*(?:<|\()',
        ]

        for pattern in func_component_patterns:
            for match in re.finditer(pattern, source_code):
                component_name = match.group(1)
                line_num = source_code[:match.start()].count('\n') + 1

                entity = CodeEntity(
                    id=self._generate_id('component', component_name, line_num),
                    type='react_component',
                    name=component_name,
                    qualified_name=f"{self.relative_path}:{component_name}",
                    file_path=str(self.file_path),
                    line_start=line_num,
                    line_end=line_num,
                    signature=f"React.FC {component_name}",
                    metadata={
                        'language': 'typescript' if self.is_typescript else 'javascript',
                        'component_type': 'functional',
                        'framework': 'react'
                    }
                )
                self.entities.append(entity)

        # React Hooks
        hook_pattern = r'(?:export\s+)?(?:const|function)\s+(use[A-Z]\w*)\s*[=:(]'
        for match in re.finditer(hook_pattern, source_code):
            hook_name = match.group(1)
            line_num = source_code[:match.start()].count('\n') + 1

            entity = CodeEntity(
                id=self._generate_id('hook', hook_name, line_num),
                type='react_hook',
                name=hook_name,
                qualified_name=f"{self.relative_path}:{hook_name}",
                file_path=str(self.file_path),
                line_start=line_num,
                line_end=line_num,
                signature=f"Hook {hook_name}",
                metadata={
                    'language': 'typescript' if self.is_typescript else 'javascript',
                    'framework': 'react'
                }
            )
            self.entities.append(entity)

    def _extract_variables(self, source_code: str):
        """提取重要的变量和常量"""
        # 只提取顶层的导出变量
        var_patterns = [
            r'export\s+(?:const|let|var)\s+([A-Z_][A-Z0-9_]*)\s*(?::\s*([^=]+))?\s*=',  # 常量
            r'export\s+(?:const|let|var)\s+(\w+Schema)\s*=',  # Schema定义
            r'export\s+(?:const|let|var)\s+(\w+Config)\s*=',  # 配置对象
        ]

        for pattern in var_patterns:
            for match in re.finditer(pattern, source_code):
                var_name = match.group(1)
                type_annotation = match.group(2) if len(match.groups()) >= 2 else None

                line_num = source_code[:match.start()].count('\n') + 1

                entity = CodeEntity(
                    id=self._generate_id('variable', var_name, line_num),
                    type='variable',
                    name=var_name,
                    qualified_name=f"{self.relative_path}:{var_name}",
                    file_path=str(self.file_path),
                    line_start=line_num,
                    line_end=line_num,
                    signature=f"{var_name}: {type_annotation}" if type_annotation else var_name,
                    metadata={
                        'language': 'typescript' if self.is_typescript else 'javascript',
                        'is_const': 'const' in match.group(0),
                        'is_exported': True,
                        'type': type_annotation
                    }
                )
                self.entities.append(entity)

    def _extract_exports(self, source_code: str):
        """提取导出"""
        # 默认导出
        default_export = re.search(r'export\s+default\s+(\w+)', source_code)
        if default_export:
            self.exports.append(f"default:{default_export.group(1)}")

        # 命名导出
        named_exports = re.findall(r'export\s+{([^}]+)}', source_code)
        for exports_str in named_exports:
            for export in exports_str.split(','):
                export = export.strip()
                if ' as ' in export:
                    original, alias = export.split(' as ')
                    self.exports.append(f"{alias.strip()}:{original.strip()}")
                else:
                    self.exports.append(export)

        # 直接导出
        direct_exports = re.findall(r'export\s+(?:const|let|var|function|class|interface|type|enum)\s+(\w+)', source_code)
        self.exports.extend(direct_exports)

    def _extract_class_members(self, class_body: str, class_name: str, class_line: int):
        """提取类成员（方法和属性）"""
        # 方法
        method_pattern = r'''
            (?:(?:public|private|protected|static|async|override)\s+)*  # 修饰符
            (?:get\s+|set\s+)?                                          # getter/setter
            (\w+)                                                        # 方法名
            \s*(?:<([^>]+)>)?                                          # 泛型参数
            \s*\(([^)]*)\)                                              # 参数
            (?:\s*:\s*([^\s{]+))?                                      # 返回类型
            \s*{                                                        # 方法体
        '''

        for match in re.finditer(method_pattern, class_body, re.VERBOSE):
            method_name = match.group(1)

            # 跳过constructor等特殊方法的重复
            if method_name in ['constructor', 'super']:
                continue

            generic_params = match.group(2)
            params = match.group(3)
            return_type = match.group(4)

            line_num = class_line + class_body[:match.start()].count('\n')

            entity = CodeEntity(
                id=self._generate_id('method', f"{class_name}.{method_name}", line_num),
                type='method',
                name=method_name,
                qualified_name=f"{self.relative_path}:{class_name}.{method_name}",
                file_path=str(self.file_path),
                line_start=line_num,
                line_end=line_num,
                signature=f"{method_name}({params})",
                metadata={
                    'language': 'typescript' if self.is_typescript else 'javascript',
                    'class': class_name,
                    'generic_params': generic_params.split(',') if generic_params else [],
                    'return_type': return_type
                }
            )
            self.entities.append(entity)

    def _build_relations(self):
        """建立代码关系"""
        # 导入关系
        for entity in self.entities:
            # 继承关系
            if entity.metadata.get('extends'):
                extends = entity.metadata['extends']
                relation = CodeRelation(
                    id=self._generate_id('inherits', f"{entity.name}_{extends}", entity.line_start),
                    source_id=entity.id,
                    target_id=extends,  # 这里是名称，需要后续解析
                    type='inherits',
                    file_path=str(self.file_path),
                    metadata={'resolved': False}
                )
                self.relations.append(relation)

            # 实现关系
            if entity.metadata.get('implements'):
                for impl in entity.metadata['implements']:
                    relation = CodeRelation(
                        id=self._generate_id('implements', f"{entity.name}_{impl}", entity.line_start),
                        source_id=entity.id,
                        target_id=impl.strip(),
                        type='implements',
                        file_path=str(self.file_path),
                        metadata={'resolved': False}
                    )
                    self.relations.append(relation)

            # 类成员关系
            if entity.type == 'method' and entity.metadata.get('class'):
                # 方法属于类
                relation = CodeRelation(
                    id=self._generate_id('contains', f"{entity.metadata['class']}_{entity.name}", entity.line_start),
                    source_id=entity.metadata['class'],  # 类名
                    target_id=entity.id,
                    type='contains',
                    file_path=str(self.file_path),
                    metadata={'member_type': 'method'}
                )
                self.relations.append(relation)

        # 导入关系
        for imported, source in self.imports.items():
            if not imported.startswith('_side_effect_'):
                # 查找是否有对应的实体使用了这个导入
                for entity in self.entities:
                    # 简化：如果实体名称与导入名称匹配，建立使用关系
                    if imported in str(entity.signature) or imported in str(entity.metadata):
                        relation = CodeRelation(
                            id=self._generate_id('imports', f"{entity.name}_{imported}", entity.line_start),
                            source_id=entity.id,
                            target_id=source,
                            type='imports',
                            file_path=str(self.file_path),
                            metadata={'import_name': imported}
                        )
                        self.relations.append(relation)
                        break

    def _find_matching_brace(self, source_code: str, start_pos: int) -> int:
        """找到匹配的大括号位置"""
        count = 1
        i = start_pos + 1
        while i < len(source_code) and count > 0:
            if source_code[i] == '{':
                count += 1
            elif source_code[i] == '}':
                count -= 1
            i += 1
        return i - 1

    def _is_inside_class(self, source_code: str, position: int) -> bool:
        """判断位置是否在类内部"""
        # 简化实现：检查前面最近的class关键字
        before_text = source_code[:position]

        # 查找最后一个class定义
        class_match = None
        for match in re.finditer(r'class\s+\w+[^{]*{', before_text):
            class_match = match

        if not class_match:
            return False

        # 检查class的结束位置
        class_end = self._find_matching_brace(source_code, class_match.end() - 1)
        return position < class_end


def analyze_js_ts_file(file_path: str, project_root: str) -> Tuple[List[CodeEntity], List[CodeRelation]]:
    """
    分析单个JavaScript/TypeScript文件的便捷函数

    Args:
        file_path: 文件路径
        project_root: 项目根目录

    Returns:
        (实体列表, 关系列表)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source_code = f.read()

        analyzer = JavaScriptTypeScriptAnalyzer(file_path, project_root)
        return analyzer.analyze(source_code)

    except Exception as e:
        logger.error(f"分析JS/TS文件失败 {file_path}: {e}")
        return [], []


# 测试代码
if __name__ == "__main__":
    # 测试TypeScript代码
    test_ts_code = '''
import { Component } from '@angular/core';
import * as React from 'react';

export interface User {
    id: number;
    name: string;
    email: string;
}

export type UserRole = 'admin' | 'user' | 'guest';

export enum Status {
    Active = 1,
    Inactive = 0,
    Pending = 2
}

@Component({
    selector: 'app-root'
})
export class AppComponent extends Component implements OnInit {
    private users: User[] = [];

    constructor() {
        super();
    }

    async getUserById(id: number): Promise<User | null> {
        return this.users.find(u => u.id === id) || null;
    }
}

export const UserList: React.FC<{ users: User[] }> = ({ users }) => {
    return (
        <div>
            {users.map(user => (
                <div key={user.id}>{user.name}</div>
            ))}
        </div>
    );
};

export function useUserData() {
    const [users, setUsers] = React.useState<User[]>([]);
    return { users, setUsers };
}

export const API_ENDPOINT = 'https://api.example.com';
    '''

    # 创建临时文件进行测试
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.tsx', delete=False) as f:
        f.write(test_ts_code)
        test_file = f.name

    # 分析文件
    entities, relations = analyze_js_ts_file(test_file, "/tmp")

    print(f"\n发现 {len(entities)} 个实体:")
    for entity in entities:
        print(f"  - {entity.type}: {entity.name} (行 {entity.line_start})")

    print(f"\n发现 {len(relations)} 个关系:")
    for relation in relations:
        print(f"  - {relation.type}: {relation.source_id} -> {relation.target_id}")

    # 清理临时文件
    import os
    os.unlink(test_file)
# 多语言代码分析架构设计

> 支持Python、Java、Swift(iOS)、Vue.js的统一代码分析框架

## 🎯 设计目标

1. **统一接口** - 不同语言使用相同的分析接口
2. **可扩展** - 易于添加新语言支持
3. **高性能** - 利用各语言最佳解析工具
4. **完整性** - 提取相同级别的代码信息

---

## 🏗️ 架构设计

### 统一抽象层

```python
# 基类定义
class BaseCodeAnalyzer:
    """所有语言分析器的基类"""

    def analyze_file(self, file_path: str) -> Tuple[List[Entity], List[Relation]]:
        """分析单个文件"""
        pass

    def get_supported_extensions(self) -> List[str]:
        """返回支持的文件扩展名"""
        pass

    def extract_entities(self, source: str) -> List[Entity]:
        """提取实体"""
        pass

    def extract_relations(self, source: str) -> List[Relation]:
        """提取关系"""
        pass
```

### 语言特定实现

```
BaseCodeAnalyzer (抽象基类)
    │
    ├── PythonAnalyzer    (ast模块)
    ├── JavaAnalyzer      (javalang库)
    ├── SwiftAnalyzer     (tree-sitter)
    └── VueAnalyzer       (vue-parser + babel)
```

---

## 📊 各语言对比

### 语言特性差异

| 特性 | Python | Java | Swift | Vue.js |
|------|--------|------|-------|--------|
| **类型系统** | 动态 | 静态 | 静态 | 动态 |
| **面向对象** | ✅ | ✅ | ✅ | 部分 |
| **函数式** | ✅ | 部分 | ✅ | ✅ |
| **模块系统** | import | package | import | import/require |
| **特殊语法** | 装饰器 | 注解 | 协议 | template |

### 解析工具选择

| 语言 | 工具 | 优势 |
|------|------|------|
| **Python** | ast (标准库) | 官方支持，完整准确 |
| **Java** | javalang | 纯Python实现，易集成 |
| **Swift** | tree-sitter-swift | 快速，增量解析 |
| **Vue** | @vue/compiler-sfc | 官方编译器 |

---

## 🔍 实体映射

### 统一实体类型

```python
class EntityType:
    # 通用类型
    MODULE = "module"          # 模块/包
    CLASS = "class"            # 类
    INTERFACE = "interface"    # 接口（Java）/协议（Swift）
    FUNCTION = "function"      # 函数/方法
    VARIABLE = "variable"      # 变量/属性
    CONSTANT = "constant"      # 常量

    # 语言特定
    ENUM = "enum"              # 枚举
    ANNOTATION = "annotation"  # 注解（Java）
    PROTOCOL = "protocol"      # 协议（Swift）
    COMPONENT = "component"    # 组件（Vue）
    DIRECTIVE = "directive"    # 指令（Vue）
    MIXIN = "mixin"            # 混入（Vue）
```

### 各语言实体映射

#### Python → 统一实体
```
class           → CLASS
def/async def   → FUNCTION
@decorator      → ANNOTATION
import          → MODULE
variable        → VARIABLE
```

#### Java → 统一实体
```
class           → CLASS
interface       → INTERFACE
enum            → ENUM
method          → FUNCTION
@Annotation     → ANNOTATION
field           → VARIABLE
package         → MODULE
```

#### Swift → 统一实体
```
class/struct    → CLASS
protocol        → PROTOCOL
func            → FUNCTION
enum            → ENUM
var/let         → VARIABLE
extension       → INTERFACE
import          → MODULE
```

#### Vue → 统一实体
```
<template>      → COMPONENT (template part)
<script>        → COMPONENT (logic part)
<style>         → COMPONENT (style part)
methods         → FUNCTION
data/computed   → VARIABLE
components      → MODULE
```

---

## 🔗 关系映射

### 统一关系类型

```python
class RelationType:
    # 通用关系
    CALLS = "calls"            # 函数调用
    IMPORTS = "imports"        # 导入/引用
    INHERITS = "inherits"      # 继承
    IMPLEMENTS = "implements"  # 实现接口
    CONTAINS = "contains"      # 包含关系
    USES = "uses"              # 使用
    DEFINES = "defines"        # 定义

    # 语言特定
    EXTENDS = "extends"        # 扩展（Swift）
    INJECTS = "injects"        # 依赖注入（Java）
    EMITS = "emits"            # 事件发送（Vue）
    PROPS = "props"            # 属性传递（Vue）
```

---

## 💻 实现策略

### 阶段1: Java支持

**工具**: javalang

**提取内容**:
- Package声明
- Import语句
- Class/Interface/Enum定义
- Method签名
- Field定义
- Annotation
- 继承和实现关系

**挑战**:
- 泛型处理
- 内部类
- Lambda表达式

### 阶段2: Swift支持

**工具**: tree-sitter-swift

**提取内容**:
- Import声明
- Class/Struct/Protocol定义
- Func定义
- Property定义
- Extension
- Protocol conformance

**挑战**:
- Optional类型
- 闭包
- Property wrapper

### 阶段3: Vue.js支持

**工具**: @vue/compiler-sfc + babel

**提取内容**:
- Component定义
- Props定义
- Data/Computed/Methods
- Template使用的组件
- Event emit
- Composables (Vue 3)

**挑战**:
- Template解析
- 响应式数据追踪
- Composition API

---

## 📦 依赖安装

```bash
# Java解析
pip install javalang

# Swift解析（tree-sitter）
pip install tree-sitter
pip install tree-sitter-swift

# Vue解析（需要Node.js环境）
npm install @vue/compiler-sfc
# 或使用Python调用Node.js
```

---

## 🎯 统一API

```python
from src.mcp_core.multi_lang_analyzer import MultiLanguageAnalyzer

# 创建分析器（自动检测语言）
analyzer = MultiLanguageAnalyzer()

# 分析项目
result = analyzer.analyze_project("/path/to/project")

# 结果格式统一
{
    "language": "java",  # 检测到的主要语言
    "entities": [        # 统一的实体格式
        {
            "type": "class",
            "name": "UserService",
            "qualified_name": "com.example.service.UserService",
            "file_path": "src/main/java/com/example/service/UserService.java",
            "line_number": 15,
            ...
        }
    ],
    "relations": [       # 统一的关系格式
        {
            "source_id": "...",
            "target_id": "...",
            "relation_type": "implements",
            ...
        }
    ]
}
```

---

## 📈 实现优先级

### Phase 1: Java (高优先级)
- ✅ 企业应用最常见
- ✅ 类型信息完整
- ✅ 工具成熟

### Phase 2: Vue.js (高优先级)
- ✅ 前端项目必备
- ✅ 组件化架构
- ✅ 生态系统完善

### Phase 3: Swift (中优先级)
- ✅ iOS开发必备
- ⚠️  工具相对较少
- ⚠️  语法复杂

---

## 🔮 扩展计划

### 短期 (v1.4.0)
- Java完整支持
- Vue.js基础支持
- Swift基础支持

### 中期 (v1.5.0)
- TypeScript支持
- Go支持
- Rust支持

### 长期 (v2.0.0)
- C/C++支持
- Kotlin支持
- 跨语言调用分析

---

**下一步**: 实现Java分析器

---

**设计时间**: 2025-01-19
**版本**: v1.4.0-alpha

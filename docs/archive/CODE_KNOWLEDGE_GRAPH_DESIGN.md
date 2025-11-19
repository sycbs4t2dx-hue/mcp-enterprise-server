# 代码知识图谱系统设计方案

> 针对大型项目（几万行代码）的深度分析与永久记忆存储

## 🎯 核心目标

**问题**:
- 大型项目代码量巨大（几万行）
- 每次都要重新阅读代码理解逻辑
- 模块间关系复杂，难以记忆
- AI无法像人一样"记住"项目全貌

**解决方案**:
构建**代码知识图谱** + **语义记忆系统**，模拟人脑对代码的理解和记忆方式。

---

## 🧠 人类记忆代码的方式

### 层次化记忆

```
人脑记忆代码的层次:

1. 宏观层 - 项目架构
   "这是一个电商系统，分为前端、后端、数据库三层"

2. 中观层 - 模块功能
   "用户模块负责注册登录，订单模块处理购买流程"

3. 微观层 - 具体实现
   "User类有authenticate方法，调用了bcrypt验证密码"

4. 关系层 - 依赖关系
   "订单模块依赖用户模块和支付模块"
```

### 关联记忆

```
当看到 "订单" 时，人脑会联想到:
- 订单状态（待支付、已发货...）
- 相关模块（用户、商品、支付）
- 数据表（orders表）
- API接口（createOrder, getOrderStatus）
- 业务流程（下单 → 支付 → 发货）
```

---

## 🏗️ 系统架构设计

```
┌─────────────────────────────────────────────┐
│         代码知识图谱系统                      │
├─────────────────────────────────────────────┤
│                                             │
│  ┌──────────────┐      ┌─────────────┐    │
│  │ 代码分析引擎  │ ────→│ 知识提取器  │    │
│  └──────────────┘      └─────────────┘    │
│         │                      │           │
│         ↓                      ↓           │
│  ┌──────────────┐      ┌─────────────┐    │
│  │  AST解析     │      │ 关系建模    │    │
│  │  静态分析    │      │ 依赖分析    │    │
│  │  动态追踪    │      │ 语义理解    │    │
│  └──────────────┘      └─────────────┘    │
│         │                      │           │
│         └──────────┬───────────┘           │
│                    ↓                       │
│         ┌─────────────────────┐           │
│         │   知识图谱存储      │           │
│         │  (Neo4j 图数据库)   │           │
│         └─────────────────────┘           │
│                    │                       │
│         ┌──────────┴───────────┐          │
│         ↓                      ↓          │
│  ┌─────────────┐      ┌──────────────┐   │
│  │ 语义检索    │      │  智能推理    │   │
│  │ 向量搜索    │      │  路径查询    │   │
│  └─────────────┘      └──────────────┘   │
│         │                      │          │
│         └──────────┬───────────┘          │
│                    ↓                      │
│         ┌─────────────────────┐          │
│         │   MCP工具接口       │          │
│         │  (供AI调用)         │          │
│         └─────────────────────┘          │
└─────────────────────────────────────────┘
```

---

## 📊 知识图谱结构

### 节点类型（12种）

```python
class NodeType:
    PROJECT = "项目"           # 项目根节点
    MODULE = "模块"            # 模块/包
    FILE = "文件"              # 源文件
    CLASS = "类"               # 类定义
    FUNCTION = "函数"          # 函数/方法
    VARIABLE = "变量"          # 变量/常量
    DATABASE = "数据库"        # 数据库表
    API = "接口"               # API端点
    CONFIG = "配置"            # 配置项
    DEPENDENCY = "依赖"        # 外部依赖
    CONCEPT = "概念"           # 业务概念
    WORKFLOW = "流程"          # 业务流程
```

### 关系类型（15种）

```python
class RelationType:
    CONTAINS = "包含"          # 项目包含模块
    INHERITS = "继承"          # 类继承
    IMPLEMENTS = "实现"        # 接口实现
    CALLS = "调用"             # 函数调用
    USES = "使用"              # 使用变量/类
    DEPENDS_ON = "依赖"        # 依赖关系
    IMPORTS = "导入"           # 模块导入
    DEFINES = "定义"           # 定义关系
    READS = "读取"             # 读取数据
    WRITES = "写入"            # 写入数据
    TRIGGERS = "触发"          # 事件触发
    BELONGS_TO = "属于"        # 归属关系
    RELATED_TO = "关联"        # 业务关联
    PRECEDES = "先于"          # 流程顺序
    SIMILAR_TO = "相似"        # 相似功能
```

### 知识图谱示例

```
项目: MCP Memory Server
  │
  ├─ 包含 ─→ 模块: API Layer
  │           │
  │           ├─ 包含 ─→ 文件: auth.py
  │           │           │
  │           │           ├─ 定义 ─→ 类: AuthService
  │           │           │           │
  │           │           │           ├─ 定义 ─→ 函数: login()
  │           │           │           │           │
  │           │           │           │           ├─ 调用 ─→ verify_password()
  │           │           │           │           └─ 写入 ─→ 数据库: users
  │           │           │           │
  │           │           │           └─ 使用 ─→ 依赖: bcrypt
  │           │           │
  │           │           └─ 导入 ─→ 模块: database
  │           │
  │           └─ 包含 ─→ 文件: memory.py
  │                       │
  │                       └─ 定义 ─→ 类: MemoryService
  │                                   │
  │                                   └─ 调用 ─→ 函数: store_memory()
  │
  ├─ 包含 ─→ 模块: Service Layer
  │           │
  │           └─ 依赖 ─→ 模块: API Layer
  │
  └─ 关联 ─→ 概念: 三级记忆管理
              │
              └─ 关联 ─→ 流程: 记忆存储流程
```

---

## 🔍 代码分析引擎

### 多层次分析

#### 1. 静态分析（AST）

```python
# 分析内容:
- 类、函数、变量定义
- 导入关系
- 继承关系
- 函数调用链
- 参数类型
- 返回值
- 装饰器
- 注释/文档
```

#### 2. 语义分析（NLP）

```python
# 提取内容:
- 函数/类名语义
  "AuthService" → 认证服务
  "store_memory" → 存储记忆

- 注释语义
  "# 验证用户密码" → 功能：密码验证

- 文档字符串
  """用户认证服务""" → 模块功能描述

- 变量命名
  "user_id" → 用户标识符
```

#### 3. 数据流分析

```python
# 追踪:
- 数据来源
  request.json → body → user_id → database

- 数据流向
  database → User对象 → JSON → response

- 状态变化
  order.status: pending → paid → shipped
```

#### 4. 业务逻辑分析

```python
# 识别:
- 业务实体
  User, Order, Product

- 业务流程
  注册 → 登录 → 浏览商品 → 下单 → 支付

- 业务规则
  if user.vip: discount = 0.8
```

---

## 💾 存储策略

### 三层存储架构

#### 1. 图数据库（Neo4j）- 结构化知识

```cypher
// 存储内容:
- 实体节点（类、函数、模块）
- 关系边（调用、依赖、继承）
- 属性（名称、类型、路径、行号）

// 示例查询:
MATCH (f:Function)-[:CALLS*1..3]->(target:Function)
WHERE f.name = 'login'
RETURN target.name
// 查询login函数直接或间接调用的所有函数
```

#### 2. 向量数据库（Milvus）- 语义记忆

```python
# 存储内容:
- 代码片段embedding
- 注释embedding
- 功能描述embedding

# 用途:
- 语义搜索: "找到所有处理支付的代码"
- 相似代码: 找到功能相似的模块
- 概念检索: "数据库操作相关的代码"
```

#### 3. 文档数据库（MySQL）- 元数据

```sql
-- 存储内容:
- 文件元信息（路径、大小、修改时间）
- 分析历史（分析时间、版本）
- 统计数据（代码行数、函数数量）
- 标签系统（人工标注、自动分类）
```

---

## 🛠️ MCP工具接口

### 工具列表（8个新工具）

```python
1. analyze_project
   功能: 深度分析整个项目，构建知识图谱
   参数: project_path, language, depth
   返回: 分析报告（模块数、函数数、关系数）

2. query_architecture
   功能: 查询项目架构
   参数: project_id
   返回: 架构图、模块列表、依赖关系

3. find_module
   功能: 查找特定功能的模块
   参数: project_id, functionality
   返回: 相关模块列表、代码位置

4. trace_function_call
   功能: 追踪函数调用链
   参数: project_id, function_name, depth
   返回: 调用图、调用路径

5. find_dependencies
   功能: 查找模块依赖关系
   参数: project_id, module_name
   返回: 依赖树、被依赖列表

6. search_code_semantic
   功能: 语义搜索代码
   参数: project_id, query, top_k
   返回: 相关代码片段、相似度分数

7. explain_workflow
   功能: 解释业务流程
   参数: project_id, workflow_name
   返回: 流程图、涉及模块、执行顺序

8. diff_versions
   功能: 对比不同版本变化
   参数: project_id, version1, version2
   返回: 变化摘要、影响分析
```

---

## 🧪 使用场景

### 场景1: 初次分析大型项目

```
开发者: "帮我分析这个5万行的电商项目"

AI调用: analyze_project(
  project_path="/path/to/ecommerce",
  language="python",
  depth="deep"
)

结果:
  - 扫描532个文件
  - 识别86个模块
  - 提取1247个函数
  - 建立3891个关系
  - 构建知识图谱完成

AI: "项目分析完成！这是一个典型的微服务架构电商系统，
     包含用户服务、商品服务、订单服务、支付服务4个核心模块。
     现在我可以回答关于这个项目的任何问题，无需重新读代码。"
```

### 场景2: 理解模块功能

```
开发者: "订单模块都有什么功能？"

AI调用: query_architecture(
  project_id="ecommerce_v1",
  focus_module="order_service"
)

AI: "订单模块包含以下功能:
     1. 创建订单 (create_order) - 52行代码
     2. 取消订单 (cancel_order) - 38行
     3. 查询订单 (get_order_status) - 24行
     4. 订单列表 (list_orders) - 45行

     依赖关系:
     - 依赖用户服务验证用户
     - 依赖商品服务检查库存
     - 依赖支付服务处理支付

     数据表: orders (7个字段)"
```

### 场景3: 追踪调用链

```
开发者: "用户下单后的完整流程是什么？"

AI调用: trace_function_call(
  project_id="ecommerce_v1",
  function_name="create_order",
  depth=5
)

AI: "用户下单完整调用链:

     1. create_order(user_id, items)  [order_service/api.py:45]
        ├─ 2. validate_user(user_id)  [user_service/validator.py:12]
        ├─ 3. check_inventory(items)  [product_service/inventory.py:28]
        │     └─ 4. lock_stock(item_id, quantity)  [product_service/inventory.py:67]
        ├─ 5. calculate_price(items)  [order_service/pricing.py:15]
        │     └─ 6. apply_discount(user_id, total)  [promotion_service/discount.py:23]
        ├─ 7. create_payment(order_id, amount)  [payment_service/api.py:34]
        └─ 8. save_order(order_data)  [order_service/repository.py:56]
              └─ 9. insert_db(table='orders', data=...)  [database/orm.py:89]

     涉及4个服务，9次函数调用"
```

### 场景4: 影响分析

```
开发者: "如果我修改User类的email字段，会影响哪些地方？"

AI调用: find_dependencies(
  project_id="ecommerce_v1",
  entity="User.email",
  type="backward"  # 向后依赖
)

AI: "修改User.email字段会影响:

     读取email的位置(12处):
     ✅ auth_service/login.py:45 - 登录验证
     ✅ notification_service/email.py:23 - 发送邮件
     ✅ user_service/profile.py:67 - 个人资料
     ...

     写入email的位置(5处):
     ⚠️ auth_service/register.py:34 - 用户注册
     ⚠️ user_service/update.py:56 - 更新资料
     ...

     数据库表:
     ⚠️ users表的email列（唯一索引）

     API端点:
     ⚠️ POST /auth/register
     ⚠️ PUT /user/profile
     ⚠️ GET /user/{id}

     建议: 需要更新12个文件，修改5个API，迁移1个数据库字段"
```

---

## 📈 记忆更新策略

### 增量更新

```python
# 文件变化检测
1. 监听文件系统变化
2. Git diff分析
3. 只分析变化的文件
4. 更新相关节点和关系

# 示例:
修改: order_service/api.py
  ↓
检测: create_order函数新增了discount参数
  ↓
更新:
  - Function节点属性
  - 新增与discount_service的关系
  - 更新调用链
  - 重新生成embedding
```

### 版本管理

```python
# 每个版本独立快照
project_v1.0  ─┐
               ├─ 可对比
project_v1.1  ─┤
               ├─ 可回溯
project_v2.0  ─┘

# 变更历史
- v1.0 → v1.1: 新增支付功能
- v1.1 → v2.0: 重构订单模块
```

---

## 🎯 实现优先级

### Phase 1: 基础分析（必需）
- [x] Python代码AST解析
- [ ] 基础知识提取（类、函数、导入）
- [ ] Neo4j图数据库集成
- [ ] 基本查询接口

### Phase 2: 深度分析（重要）
- [ ] 调用链追踪
- [ ] 依赖关系分析
- [ ] 语义向量化
- [ ] Milvus集成

### Phase 3: 智能检索（高级）
- [ ] 自然语言查询
- [ ] 影响分析
- [ ] 相似代码检测
- [ ] 业务流程提取

### Phase 4: 多语言支持（扩展）
- [ ] JavaScript/TypeScript
- [ ] Java
- [ ] Go
- [ ] Rust

---

## 💡 技术选型

| 组件 | 技术 | 理由 |
|------|------|------|
| **代码解析** | tree-sitter | 快速、多语言 |
| **图数据库** | Neo4j | 最佳图查询性能 |
| **向量搜索** | Milvus | 已集成，扩展性好 |
| **文档存储** | MySQL | 现有基础设施 |
| **嵌入模型** | CodeBERT | 专门的代码理解模型 |
| **流程可视化** | Graphviz | 生成调用图 |

---

**下一步**: 实现代码分析引擎原型

---

**设计时间**: 2025-01-19
**设计者**: MCP Team

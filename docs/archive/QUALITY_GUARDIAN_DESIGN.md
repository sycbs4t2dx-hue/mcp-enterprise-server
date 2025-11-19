# MCP v1.7.0 - 质量守护者系统设计

> 持续监控项目质量，预测技术债务，提供智能重构建议

**设计日期**: 2025-01-19
**版本**: v1.7.0
**核心功能**: 代码质量分析 + 技术债务追踪 + 智能预警

---

## 🎯 设计目标

### 核心问题

当前系统已经解决了：
- ✅ 上下文丢失 → 持久化会话
- ✅ 知识碎片化 → 代码知识图谱
- ✅ 缺乏持续性 → 智能TODO管理

**但还未解决**：
- ❌ 代码质量监控 → 需要质量守护者
- ❌ 技术债务追踪 → 需要债务评估
- ❌ 重构时机判断 → 需要预测性分析
- ❌ 代码异味检测 → 需要模式识别

### v1.7.0 解决方案

```
代码知识图谱 + AI深度分析 = 智能质量守护系统
```

**核心能力**:
1. **实时质量监控** - 每次代码变更后自动评估
2. **技术债务追踪** - 量化债务，优先级排序
3. **预测性预警** - 基于趋势预测未来问题
4. **智能重构建议** - AI生成具体的重构方案

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────┐
│              质量守护者系统                               │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────┐ │
│  │代码异味检测     │  │技术债务评估     │  │预测分析  │ │
│  │- 循环依赖      │  │- TODO/FIXME    │  │- 趋势预测 │ │
│  │- 过长函数      │  │- 测试覆盖率     │  │- 瓶颈预警 │ │
│  │- 重复代码      │  │- 文档完整度     │  │- 复杂度  │ │
│  │- 过度耦合      │  │- 依赖老旧度     │  │  增长    │ │
│  └────────────────┘  └────────────────┘  └──────────┘ │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │            AI智能分析引擎                           │ │
│  │  - 根因分析                                         │ │
│  │  - 重构建议生成                                      │ │
│  │  - 最佳实践推荐                                      │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
└────────────────────┬────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────┐
│              质量报告和预警系统                           │
│  - 质量评分仪表盘                                         │
│  - 技术债务趋势图                                         │
│  - 重构优先级列表                                         │
│  - 自动预警通知                                           │
└─────────────────────────────────────────────────────────┘
```

---

## 🔧 核心功能设计

### 1. 代码异味检测器

**目标**: 自动识别常见的代码问题

**检测维度**:

```python
class CodeSmellDetector:
    """代码异味检测器"""

    def detect_circular_dependencies(self, project_id: str) -> List[Issue]:
        """检测循环依赖"""

        算法:
        1. 从代码关系图中提取所有imports/depends关系
        2. 使用深度优先搜索检测环
        3. 分析环的严重程度（环的长度、涉及模块数）

        输出:
        {
          "issue_type": "circular_dependency",
          "severity": "high",
          "modules": ["user_service", "order_service", "payment_service"],
          "cycle_path": ["user_service → order_service → payment_service → user_service"],
          "impact": "3个模块相互依赖，难以独立测试和部署",
          "suggestion": "引入事件总线或依赖注入解耦"
        }

    def detect_long_functions(self, project_id: str) -> List[Issue]:
        """检测过长函数"""

        规则:
        - 函数超过50行 → 警告
        - 函数超过100行 → 严重
        - 函数超过200行 → 紧急

        分析:
        1. 统计函数行数（排除空行和注释）
        2. 计算圈复杂度
        3. 识别可拆分的逻辑块

        输出:
        {
          "issue_type": "long_function",
          "severity": "high",
          "function": "process_order",
          "file_path": "services/order_service.py",
          "line_number": 156,
          "lines_of_code": 450,
          "cyclomatic_complexity": 28,
          "suggestion": "拆分为: validate_order, calculate_price, reserve_inventory, process_payment, complete_order"
        }

    def detect_duplicate_code(self, project_id: str) -> List[Issue]:
        """检测重复代码"""

        算法:
        1. 提取所有函数的AST
        2. 计算函数间的相似度（基于AST结构）
        3. 识别相似度>80%的函数对

        输出:
        {
          "issue_type": "duplicate_code",
          "severity": "medium",
          "duplicates": [
            {
              "function1": "validate_email",
              "file1": "user/validator.py:45",
              "function2": "check_email_format",
              "file2": "auth/helper.py:78",
              "similarity": 95%
            }
          ],
          "suggestion": "提取为公共工具函数 utils.email.validate()"
        }

    def detect_god_classes(self, project_id: str) -> List[Issue]:
        """检测上帝类（职责过多）"""

        规则:
        - 类的方法数 > 20 → 警告
        - 类的属性数 > 15 → 警告
        - 类的代码行数 > 500 → 严重

        分析:
        1. 统计类的方法数、属性数、代码行数
        2. 分析方法间的内聚度
        3. 识别可拆分的职责边界

        输出:
        {
          "issue_type": "god_class",
          "severity": "high",
          "class": "UserService",
          "methods_count": 35,
          "lines_of_code": 850,
          "responsibilities": ["认证", "用户管理", "权限检查", "会话管理", "日志"],
          "suggestion": "拆分为: AuthService, UserManagementService, PermissionService"
        }

    def detect_tight_coupling(self, project_id: str) -> List[Issue]:
        """检测过度耦合"""

        指标:
        - 入度 (被依赖数) > 10 → 高耦合
        - 出度 (依赖数) > 10 → 高耦合
        - 扇入扇出比 > 3 → 不平衡

        输出:
        {
          "issue_type": "tight_coupling",
          "severity": "medium",
          "entity": "DatabaseHelper",
          "fan_in": 25,  # 被25个模块依赖
          "fan_out": 3,   # 依赖3个模块
          "coupling_ratio": 8.3,
          "suggestion": "过度被依赖，考虑引入接口层解耦"
        }
```

### 2. 技术债务评估器

**目标**: 量化技术债务，提供优先级

```python
class TechnicalDebtAssessor:
    """技术债务评估器"""

    def assess_project_debt(self, project_id: str) -> Dict[str, Any]:
        """评估项目整体技术债务"""

        评估维度:
        1. 代码质量 (40%)
           - 代码异味数量
           - 复杂度指标
           - 重复代码比例

        2. 测试质量 (25%)
           - 测试覆盖率
           - 测试质量（断言数、mock使用）
           - 测试运行时间

        3. 文档完整度 (15%)
           - API文档覆盖率
           - 函数文档字符串
           - README完整性

        4. 依赖健康度 (10%)
           - 过期依赖数量
           - 安全漏洞数量
           - 许可证问题

        5. TODO/FIXME (10%)
           - 数量
           - 存在时间
           - 优先级

        输出:
        {
          "overall_score": 6.5,  # 0-10分，10为最好
          "debt_level": "medium",
          "breakdown": {
            "code_quality": 7.2,
            "test_quality": 5.8,
            "documentation": 6.0,
            "dependencies": 7.5,
            "todos": 6.0
          },
          "estimated_days_to_fix": 15,
          "trend": "increasing"  # increasing/stable/decreasing
        }

    def identify_debt_hotspots(self, project_id: str) -> List[Dict]:
        """识别技术债务热点"""

        算法:
        1. 综合代码异味、复杂度、变更频率
        2. 计算每个文件/模块的债务分数
        3. 按分数排序，识别Top 10

        输出:
        [
          {
            "file": "services/order_service.py",
            "debt_score": 8.5,  # 0-10，10最严重
            "issues_count": 12,
            "main_issues": [
              "3个过长函数",
              "2个循环依赖",
              "测试覆盖率仅30%"
            ],
            "estimated_hours": 8,
            "priority": "high"
          }
        ]

    def calculate_refactoring_roi(self, issue: Issue) -> Dict:
        """计算重构的投资回报率"""

        因素:
        - 问题严重程度
        - 影响范围（被多少代码使用）
        - 修复成本（预估工时）
        - 变更频率（经常改动的代码优先重构）

        输出:
        {
          "issue": "process_order函数过长",
          "severity": 8,
          "impact_scope": 15,  # 影响15处代码
          "fix_cost_hours": 4,
          "change_frequency": 0.3,  # 每周变更次数
          "roi_score": 9.2,  # ROI分数，越高越值得重构
          "recommendation": "强烈建议立即重构"
        }
```

### 3. 预测性分析器

**目标**: 基于历史趋势预测未来问题

```python
class PredictiveAnalyzer:
    """预测性分析器"""

    def predict_complexity_growth(self, project_id: str) -> List[Warning]:
        """预测复杂度增长"""

        数据:
        - 历史会话中的代码变更
        - 函数/类的大小变化趋势
        - 新增代码的速度

        算法:
        1. 分析最近5次会话的代码增长
        2. 计算平均增长率
        3. 线性外推未来2周

        输出:
        {
          "entity": "UserService",
          "current_lines": 450,
          "current_methods": 28,
          "growth_rate": "+50行/周",
          "predicted_lines_2weeks": 550,
          "threshold": 500,
          "warning": "预计2周后超过500行阈值",
          "suggestion": "现在开始拆分，避免未来更大的重构成本"
        }

    def predict_performance_bottlenecks(self, project_id: str) -> List[Warning]:
        """预测性能瓶颈"""

        分析:
        1. 数据库查询缺少索引
        2. N+1查询模式
        3. 循环中的重复计算
        4. 内存泄漏风险

        输出:
        {
          "type": "database_performance",
          "location": "order_service.py:get_user_orders",
          "issue": "查询缺少索引",
          "current_impact": "10ms/查询",
          "predicted_impact_at_scale": {
            "1000_users": "50ms/查询",
            "10000_users": "500ms/查询 (不可接受)",
            "100000_users": "5000ms/查询 (严重)"
          },
          "suggestion": "添加user_id和created_at的复合索引"
        }

    def predict_maintenance_burden(self, project_id: str) -> Dict:
        """预测维护负担"""

        指标:
        - 技术债务增长速度
        - 新功能开发速度下降
        - Bug修复时间增加

        输出:
        {
          "current_velocity": 8,  # 每周完成story点数
          "predicted_velocity_1month": 6,
          "predicted_velocity_3months": 4,
          "debt_acceleration": "fast",
          "tipping_point": "约6周后开发速度降低50%",
          "recommendation": "立即安排重构Sprint"
        }
```

### 4. 智能重构建议生成器

**目标**: AI生成具体的重构方案

```python
class RefactoringAdvisor:
    """智能重构建议"""

    async def generate_refactoring_plan(self, issue: Issue) -> Dict:
        """生成重构计划"""

        调用AI:
        """
        基于问题: {issue}
        当前代码: {code_snippet}
        代码图谱: {dependencies}

        生成重构方案:
        1. 具体步骤（step-by-step）
        2. 预期收益
        3. 风险评估
        4. 测试策略
        5. 回滚方案
        """

        输出:
        {
          "issue": "process_order函数过长",
          "refactoring_type": "Extract Method",
          "plan": {
            "steps": [
              {
                "step": 1,
                "action": "提取订单验证逻辑",
                "extract_to": "validate_order()",
                "lines": "156-180",
                "estimated_time": "30分钟"
              },
              {
                "step": 2,
                "action": "提取价格计算逻辑",
                "extract_to": "calculate_order_price()",
                "lines": "181-210",
                "estimated_time": "30分钟"
              }
            ],
            "benefits": [
              "降低圈复杂度: 28 → 12",
              "提高可测试性",
              "提高代码可读性"
            ],
            "risks": [
              "可能影响3个调用方",
              "需要更新单元测试"
            ],
            "test_strategy": "先为每个提取的方法编写单元测试",
            "rollback_plan": "保留原函数作为deprecated，渐进式迁移"
          }
        }

    async def suggest_design_patterns(self, smell: CodeSmell) -> List[str]:
        """推荐设计模式"""

        规则:
        - 循环依赖 → 依赖注入、事件驱动
        - 上帝类 → 单一职责、门面模式
        - 重复代码 → 模板方法、策略模式
        - 过度耦合 → 接口隔离、适配器模式

        输出:
        [
          {
            "pattern": "依赖注入",
            "reason": "解除循环依赖",
            "implementation": "使用构造函数注入UserService依赖",
            "example_code": "class OrderService:\n    def __init__(self, user_service: UserService):\n        self.user_service = user_service"
          }
        ]
```

---

## 📊 数据模型

### 新增数据表

```sql
-- 质量问题记录
quality_issues (
    issue_id,
    project_id,
    issue_type,  -- circular_dependency, long_function, duplicate_code, etc.
    severity,    -- low, medium, high, critical
    entity_id,   -- 关联的代码实体
    file_path,
    line_number,
    description,
    suggestion,
    metadata,    -- JSON详细信息
    status,      -- open, in_progress, resolved, ignored
    detected_at,
    resolved_at
)

-- 技术债务快照
debt_snapshots (
    snapshot_id,
    project_id,
    overall_score,
    code_quality_score,
    test_quality_score,
    documentation_score,
    dependencies_score,
    todos_score,
    issues_count,
    estimated_days_to_fix,
    created_at
)

-- 预警记录
quality_warnings (
    warning_id,
    project_id,
    warning_type,  -- complexity_growth, performance_bottleneck, etc.
    entity_id,
    severity,
    predicted_date,  -- 预测问题发生日期
    message,
    suggestion,
    created_at,
    acknowledged
)

-- 重构建议
refactoring_suggestions (
    suggestion_id,
    project_id,
    issue_id,
    refactoring_type,  -- extract_method, split_class, etc.
    plan,              -- JSON详细计划
    estimated_hours,
    roi_score,
    status,            -- pending, accepted, rejected, completed
    created_at,
    applied_at
)
```

---

## 🎯 MCP工具定义

### 新增8个质量守护工具

```python
QUALITY_GUARDIAN_TOOLS = [
    {
        "name": "detect_code_smells",
        "description": "检测代码异味（循环依赖、过长函数、重复代码等）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "smell_types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "要检测的异味类型（可选，默认全部）"
                }
            },
            "required": ["project_id"]
        }
    },
    {
        "name": "assess_technical_debt",
        "description": "评估项目技术债务，生成质量评分",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string"}
            },
            "required": ["project_id"]
        }
    },
    {
        "name": "identify_debt_hotspots",
        "description": "识别技术债务热点，找出最需要重构的代码",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "top_k": {"type": "integer", "description": "返回前K个热点"}
            },
            "required": ["project_id"]
        }
    },
    {
        "name": "predict_quality_issues",
        "description": "预测未来可能出现的质量问题（复杂度增长、性能瓶颈等）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "timeframe_weeks": {"type": "integer", "description": "预测时间范围（周）"}
            },
            "required": ["project_id"]
        }
    },
    {
        "name": "generate_refactoring_plan",
        "description": "为特定问题生成详细的重构计划",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "issue_id": {"type": "string", "description": "质量问题ID"}
            },
            "required": ["project_id", "issue_id"]
        }
    },
    {
        "name": "get_quality_trends",
        "description": "获取项目质量趋势（过去30天）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string"}
            },
            "required": ["project_id"]
        }
    },
    {
        "name": "apply_refactoring_suggestion",
        "description": "标记接受重构建议并创建TODO",
        "inputSchema": {
            "type": "object",
            "properties": {
                "suggestion_id": {"type": "string"}
            },
            "required": ["suggestion_id"]
        }
    },
    {
        "name": "generate_quality_report",
        "description": "生成完整的质量报告（Markdown格式）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string"}
            },
            "required": ["project_id"]
        }
    }
]
```

---

## 🎬 使用场景

### 场景1: 每日质量检查

```
开发者: "检查项目代码质量"

AI: 让我全面检查代码质量...

调用: detect_code_smells(project_id)

═══════════════════════════════════════
📊 代码质量检查报告

检测到 15 个问题:

严重 (3个):
1. 循环依赖: user_service ↔ order_service
   影响: 难以独立测试和部署
   建议: 引入事件总线解耦

2. 过长函数: process_order (450行)
   复杂度: 28
   建议: 拆分为5个子函数

3. 上帝类: UserService (35个方法, 850行)
   建议: 拆分职责

中等 (8个):
- 4处重复代码
- 3个过度耦合
- 1个命名不一致

轻微 (4个):
...

技术债务评分: 6.5/10 (中等)
═══════════════════════════════════════

建议: 优先处理3个严重问题
```

### 场景2: 预测性预警

```
AI: 基于代码增长趋势，检测到潜在风险...

调用: predict_quality_issues(project_id, timeframe_weeks=2)

═══════════════════════════════════════
⚠️  质量预警

预测未来2周可能出现的问题:

1. UserService将超过1000行 (预计12天后)
   当前: 850行
   增长率: +50行/周
   建议: 现在开始拆分

2. 订单查询性能将成为瓶颈 (预计用户数超过5000时)
   当前: 1000用户, 平均50ms
   预测: 5000用户, 平均250ms
   建议: 添加数据库索引

3. 测试运行时间将超过10分钟 (预计1个月后)
   当前: 6分钟
   增长率: +30秒/周
   建议: 并行化测试执行
═══════════════════════════════════════
```

### 场景3: 智能重构建议

```
开发者: "帮我重构process_order函数"

AI: 让我分析并生成重构方案...

调用: generate_refactoring_plan(issue_id="long_function_001")

═══════════════════════════════════════
🔧 重构方案: Extract Method

目标: 将450行的process_order拆分为小函数

步骤:
1. [30分钟] 提取订单验证逻辑
   → validate_order(order_data) -> ValidationResult

2. [30分钟] 提取价格计算逻辑
   → calculate_order_price(order) -> Decimal

3. [45分钟] 提取库存预留逻辑
   → reserve_inventory(order) -> ReservationId

4. [45分钟] 提取支付处理逻辑
   → process_payment(order, price) -> PaymentResult

5. [30分钟] 更新单元测试

总预估: 3小时

收益:
✅ 圈复杂度: 28 → 8
✅ 可测试性大幅提升
✅ 代码可读性提高

风险:
⚠️  影响3个调用方
⚠️  需要更新12个单元测试

测试策略:
1. 先为每个提取的方法编写单元测试
2. 保持原函数调用新方法，确保行为一致
3. 渐进式迁移调用方

是否接受此方案？
═══════════════════════════════════════
```

---

## 📈 实现优先级

### Phase 1: 核心检测 (v1.7.0)
- [x] 代码异味检测器
- [x] 技术债务评估器
- [x] 基础数据模型
- [x] 8个MCP工具

### Phase 2: 智能分析 (v1.7.1)
- [ ] 预测性分析器
- [ ] 趋势可视化
- [ ] 质量报告生成

### Phase 3: 重构助手 (v1.8.0)
- [ ] 智能重构建议
- [ ] 自动代码重构
- [ ] 重构影响分析

---

**设计完成，准备实现！** 🎯✨

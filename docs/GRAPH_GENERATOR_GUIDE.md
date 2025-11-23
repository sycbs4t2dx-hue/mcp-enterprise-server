# 📊 MCP 项目知识图谱生成器

## 🎯 功能介绍

MCP项目知识图谱生成器允许**任何使用MCP的项目**自动生成自己的交互式知识图谱。这个工具可以：

- 🔍 自动分析项目结构
- 🌐 可视化模块依赖关系
- 📈 统计代码复杂度
- 🎨 生成交互式HTML图谱
- 🌍 支持15+编程语言

## 🚀 快速开始

### 1. 基本使用

```python
from mcp_tools.graph_generator_tool import GraphGeneratorTool

# 创建工具实例
tool = GraphGeneratorTool()

# 生成项目图谱
result = await tool.execute(
    path="/path/to/your/project",  # 你的项目路径
    format="html"                   # 生成HTML可视化
)
```

### 2. 高级选项

```python
result = await tool.execute(
    path="/path/to/project",
    format="both",              # "json", "html", 或 "both"
    output_file="my_graph",     # 输出文件名
    include_tests=False,        # 是否包含测试文件
    max_depth=5,                # 最大目录深度
    languages=["python", "javascript"]  # 只分析特定语言
)
```

## 🎨 可视化效果

生成的HTML图谱包含：

- **力导向布局** - 节点自动排列
- **交互式操作** - 拖拽、缩放、搜索
- **多种布局** - 力导向、径向、层次、环形
- **节点信息** - 点击查看详细信息
- **依赖关系** - 可视化导入和调用关系

## 📋 支持的语言

- **Python** (.py) - 完整AST分析
- **JavaScript** (.js) - 导入和函数分析
- **TypeScript** (.ts, .tsx) - 接口和类型定义
- **Java** (.java) - 包和类结构
- **Go** (.go)
- **Rust** (.rs)
- **C/C++** (.c, .cpp, .h, .hpp)
- **C#** (.cs)
- **Ruby** (.rb)
- **PHP** (.php)
- **Swift** (.swift)
- **Kotlin** (.kt)
- **Scala** (.scala)
- **Vue** (.vue)
- **React** (.jsx, .tsx)

## 🛠️ 功能特性

### 自动分析
- 递归扫描项目文件
- 智能识别导入关系
- 提取类、函数、接口
- 计算代码复杂度
- 统计文件大小

### 可视化选项
- 节点大小反映文件复杂度
- 颜色区分文件类型/语言
- 箭头表示依赖方向
- 标签显示文件名

### 交互功能
- 搜索特定文件
- 切换布局算法
- 导出SVG图片
- 重置视图

## 📝 示例

### 分析Python项目
```python
# 分析Django项目
await tool.execute(
    path="/path/to/django/project",
    format="html",
    include_tests=False,
    languages=["python"]
)
```

### 分析前端项目
```python
# 分析React项目
await tool.execute(
    path="/path/to/react/app",
    format="html",
    languages=["javascript", "typescript"],
    output_file="react_app_graph"
)
```

### 分析混合项目
```python
# 分析全栈项目
await tool.execute(
    path="/path/to/fullstack/project",
    format="both",
    languages=["python", "javascript", "typescript"],
    max_depth=10
)
```

## 🔧 API使用

除了工具接口，还可以直接使用API：

```python
from mcp_core.services.project_graph_generator import get_graph_api

graph_api = get_graph_api()

# 创建图谱
result = await graph_api.create_graph(
    project_path="/path/to/project",
    options={
        "format": "json",
        "include_tests": False
    }
)

# 获取图谱
graph = await graph_api.get_graph(graph_id)

# 列出所有图谱
graphs = await graph_api.list_graphs()
```

## 📊 输出格式

### JSON格式
```json
{
    "nodes": [
        {
            "id": "abc123",
            "name": "main",
            "type": "file",
            "path": "src/main.py",
            "description": "主程序入口",
            "size": 2048,
            "complexity": 15,
            "metadata": {...}
        }
    ],
    "edges": [
        {
            "source": "abc123",
            "target": "def456",
            "type": "imports",
            "weight": 1.0
        }
    ],
    "metadata": {
        "project_name": "MyProject",
        "total_files": 42,
        "language_stats": {...}
    }
}
```

### HTML格式
- 完整的交互式网页
- 内嵌D3.js可视化
- 无需额外依赖
- 可直接在浏览器打开

## 💡 最佳实践

1. **大型项目** - 设置`max_depth`限制扫描深度
2. **性能优化** - 使用`languages`参数只分析需要的语言
3. **清理输出** - 设置`include_tests=False`排除测试文件
4. **版本控制** - 将生成的图谱添加到`.gitignore`

## 🎯 使用场景

- **项目文档** - 为新成员展示项目结构
- **代码审查** - 识别复杂依赖关系
- **重构规划** - 分析模块耦合度
- **技术债务** - 发现循环依赖
- **架构设计** - 可视化系统架构

## 🚦 运行测试

```bash
# 测试图谱生成器
python test_graph_generator.py

# 生成MCP项目自己的图谱
python -c "
import asyncio
from mcp_tools.graph_generator_tool import GraphGeneratorTool
tool = GraphGeneratorTool()
asyncio.run(tool.execute(path='.', format='html'))
"
```

## 📄 许可

MIT License

---

🎉 **现在，任何使用MCP的项目都可以轻松生成自己的知识图谱了！**
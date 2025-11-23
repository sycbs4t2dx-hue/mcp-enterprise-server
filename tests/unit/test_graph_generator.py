#!/usr/bin/env python3
"""
测试项目图谱生成器
演示任何项目如何使用MCP生成自己的知识图谱
"""

import asyncio
import os
import sys
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent))

from src.mcp_tools.graph_generator_tool import GraphGeneratorTool
from src.mcp_core.common.logger import get_logger

logger = get_logger(__name__)

async def test_graph_generation():
    """测试图谱生成功能"""

    print("=" * 60)
    print("🗺️  MCP项目图谱生成器测试")
    print("=" * 60)
    print()

    # 创建工具实例
    tool = GraphGeneratorTool()

    # 测试1: 分析当前MCP项目
    print("📊 测试1: 分析MCP项目本身")
    print("-" * 40)

    result = await tool.execute(
        path="/Users/mac/Downloads/MCP",
        format="both",  # 同时生成JSON和HTML
        output_file="mcp_project_graph",
        include_tests=False,
        languages=["python", "javascript", "typescript"]
    )

    if result.success:
        print("✅ 成功生成MCP项目图谱!")
        print(f"   输出文件: {result.result['outputs']}")
        print(f"   统计信息:")
        stats = result.result['statistics']
        print(f"   - 文件总数: {stats['total_files']}")
        print(f"   - 依赖关系: {stats['total_dependencies']}")
        print(f"   - 语言分布: {stats['languages']}")
        print(f"   - 总复杂度: {stats['total_complexity']}")
        print(f"   - 项目大小: {stats['total_size_mb']} MB")
    else:
        print(f"❌ 生成失败: {result.error}")

    print()

    # 测试2: 分析前端项目
    if os.path.exists("/Users/mac/Downloads/MCP/mcp-admin-ui"):
        print("📊 测试2: 分析前端UI项目")
        print("-" * 40)

        result = await tool.execute(
            path="/Users/mac/Downloads/MCP/mcp-admin-ui",
            format="html",
            output_file="frontend_graph",
            languages=["javascript", "typescript", "vue"]
        )

        if result.success:
            print("✅ 成功生成前端项目图谱!")
            print(f"   可视化页面: {result.result['preview_url']}")
        else:
            print(f"❌ 生成失败: {result.error}")

    print()

    # 测试3: 演示如何在任何项目中使用
    print("💡 如何在您的项目中使用:")
    print("-" * 40)
    print("""
    1. 在您的Python项目中导入工具:
       from mcp_tools.graph_generator_tool import GraphGeneratorTool

    2. 生成项目图谱:
       tool = GraphGeneratorTool()
       result = await tool.execute(
           path="/path/to/your/project",
           format="html"
       )

    3. 打开生成的HTML文件查看交互式图谱:
       open project_graph.html

    4. 支持的语言:
       Python, JavaScript, TypeScript, Java, Go, Rust, C/C++,
       C#, Ruby, PHP, Swift, Kotlin, Scala, Vue, React
    """)

    print()
    print("=" * 60)
    print("🎉 测试完成!")
    print("=" * 60)

async def demonstrate_api_usage():
    """演示API级别的使用"""

    print("\n📚 API使用示例:")
    print("-" * 40)

    from src.mcp_core.services.project_graph_generator import get_graph_api

    # 获取API实例
    graph_api = get_graph_api()

    # 创建图谱
    result = await graph_api.create_graph(
        project_path="/Users/mac/Downloads/MCP",
        options={
            "format": "json",
            "include_tests": False,
            "max_depth": 3
        }
    )

    if result["status"] == "success":
        print("✅ 通过API成功生成图谱")
        data = result["data"]
        print(f"   节点数: {len(data['nodes'])}")
        print(f"   边数: {len(data['edges'])}")

        # 显示前5个节点
        print("\n   示例节点:")
        for node in data['nodes'][:5]:
            print(f"   - {node['name']} ({node['type']}): {node['description']}")

    # 列出所有已生成的图谱
    graphs = await graph_api.list_graphs()
    if graphs["status"] == "success":
        print(f"\n📋 数据库中的图谱: {len(graphs['data'])}个")

if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║                                                          ║
    ║     MCP 项目知识图谱生成器 - 任何项目都能使用！         ║
    ║                                                          ║
    ║     自动分析项目结构，生成交互式知识图谱                ║
    ║     支持多种编程语言，可视化项目依赖关系                ║
    ║                                                          ║
    ╚══════════════════════════════════════════════════════════╝
    """)

    # 运行测试
    asyncio.run(test_graph_generation())

    # 演示API使用
    asyncio.run(demonstrate_api_usage())

    print("\n提示: 生成的HTML文件可以直接在浏览器中打开查看交互式图谱!")
    print("      JSON文件包含完整的图谱数据，可用于进一步分析。")
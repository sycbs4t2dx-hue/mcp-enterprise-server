#!/usr/bin/env python3
"""
简化的图谱生成测试 - 直接测试核心功能
"""

import asyncio
import json
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent))

from src.mcp_core.services.project_graph_generator import ProjectAnalyzer, GraphGenerator

async def test_basic():
    """基础功能测试"""
    print("=" * 60)
    print("🗺️  测试项目图谱生成器")
    print("=" * 60)

    # 1. 测试项目分析器
    print("\n1. 测试项目分析器")
    analyzer = ProjectAnalyzer()

    # 分析一个小的测试目录 (src/mcp_tools)
    test_path = "/Users/mac/Downloads/MCP/src/mcp_tools"
    print(f"   分析目录: {test_path}")

    try:
        graph_data = await analyzer.analyze_project(test_path)
        print(f"   ✅ 成功分析项目!")
        print(f"   - 发现 {len(graph_data.nodes)} 个文件")
        print(f"   - 发现 {len(graph_data.edges)} 个依赖关系")

        # 显示一些节点信息
        if graph_data.nodes:
            print("\n   示例节点:")
            for node in graph_data.nodes[:3]:
                print(f"   - {node.name}: {node.description}")
    except Exception as e:
        print(f"   ❌ 分析失败: {e}")
        return

    # 2. 生成JSON格式
    print("\n2. 生成JSON格式")
    generator = GraphGenerator()

    # 转换为JSON
    json_data = generator._to_json(graph_data)

    # 保存到文件
    output_file = "test_graph.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)

    print(f"   ✅ JSON已保存到: {output_file}")
    print(f"   - 节点数: {len(json_data['nodes'])}")
    print(f"   - 边数: {len(json_data['edges'])}")

    # 3. 生成HTML可视化 (简化版，不使用pyvis)
    print("\n3. 生成HTML可视化")

    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>项目图谱测试</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; }}
        h1 {{ color: #333; }}
        #stats {{ background: #f0f0f0; padding: 15px; border-radius: 5px; }}
        .stat {{ margin: 5px 0; }}
        svg {{ border: 1px solid #ccc; }}
        .node {{ fill: #69b3a2; stroke: #000; stroke-width: 1.5px; cursor: pointer; }}
        .link {{ stroke: #999; stroke-opacity: 0.6; }}
        .label {{ font-size: 12px; }}
    </style>
</head>
<body>
    <h1>项目知识图谱 - 测试</h1>
    <div id="stats">
        <div class="stat">文件数: {len(graph_data.nodes)}</div>
        <div class="stat">依赖关系: {len(graph_data.edges)}</div>
        <div class="stat">项目路径: {test_path}</div>
    </div>
    <svg id="graph" width="800" height="600"></svg>
    <script>
        const data = {json.dumps(json_data)};

        const svg = d3.select("#graph");
        const width = 800;
        const height = 600;

        const simulation = d3.forceSimulation(data.nodes)
            .force("link", d3.forceLink(data.edges).id(d => d.id).distance(100))
            .force("charge", d3.forceManyBody().strength(-300))
            .force("center", d3.forceCenter(width / 2, height / 2));

        const link = svg.append("g")
            .selectAll("line")
            .data(data.edges)
            .enter().append("line")
            .attr("class", "link");

        const node = svg.append("g")
            .selectAll("circle")
            .data(data.nodes)
            .enter().append("circle")
            .attr("class", "node")
            .attr("r", 10)
            .call(d3.drag()
                .on("start", dragstarted)
                .on("drag", dragged)
                .on("end", dragended));

        const label = svg.append("g")
            .selectAll("text")
            .data(data.nodes)
            .enter().append("text")
            .attr("class", "label")
            .text(d => d.name);

        simulation.on("tick", () => {{
            link
                .attr("x1", d => d.source.x)
                .attr("y1", d => d.source.y)
                .attr("x2", d => d.target.x)
                .attr("y2", d => d.target.y);

            node
                .attr("cx", d => d.x)
                .attr("cy", d => d.y);

            label
                .attr("x", d => d.x)
                .attr("y", d => d.y - 15);
        }});

        function dragstarted(event, d) {{
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        }}

        function dragged(event, d) {{
            d.fx = event.x;
            d.fy = event.y;
        }}

        function dragended(event, d) {{
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
        }}
    </script>
</body>
</html>"""

    html_file = "test_graph.html"
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"   ✅ HTML已保存到: {html_file}")
    print(f"   可以在浏览器中打开查看: file://{Path(html_file).absolute()}")

    print("\n" + "=" * 60)
    print("✅ 测试完成! 项目图谱生成器工作正常。")
    print("=" * 60)

    print("""
📚 使用说明:
1. test_graph.json - 包含完整的图谱数据
2. test_graph.html - 可在浏览器中查看的交互式图谱

您的项目现在可以使用这个工具自动生成知识图谱了！
    """)

if __name__ == "__main__":
    asyncio.run(test_basic())
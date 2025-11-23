#!/usr/bin/env python3
"""
生成MCP项目完整知识图谱
展示任何项目都可以使用这个工具生成自己的图谱
"""

import asyncio
import json
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent))

from src.mcp_core.services.project_graph_generator import ProjectAnalyzer, GraphGenerator

async def generate_full_graph():
    """生成完整的MCP项目图谱"""
    print("=" * 60)
    print("🗺️  生成MCP项目完整知识图谱")
    print("=" * 60)

    # 创建分析器和生成器
    analyzer = ProjectAnalyzer()
    generator = GraphGenerator()

    # 分析整个MCP项目
    project_path = "/Users/mac/Downloads/MCP"
    print(f"\n📊 分析项目: {project_path}")
    print("   这可能需要几秒钟...")

    graph_data = await analyzer.analyze_project(project_path)

    print(f"\n✅ 分析完成!")
    print(f"   - 文件数: {len(graph_data.nodes)}")
    print(f"   - 依赖关系: {len(graph_data.edges)}")

    # 统计语言分布
    lang_stats = {}
    for node in graph_data.nodes:
        lang = node.metadata.get("language", "unknown")
        lang_stats[lang] = lang_stats.get(lang, 0) + 1

    print(f"\n📈 语言分布:")
    for lang, count in sorted(lang_stats.items(), key=lambda x: x[1], reverse=True):
        if count > 0:
            print(f"   - {lang}: {count} 个文件")

    # 应用布局
    print(f"\n🎨 应用布局算法...")
    graph_data = generator._apply_layout(graph_data)

    # 生成JSON
    json_data = generator._to_json(graph_data)
    json_file = "mcp_full_graph.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    print(f"   ✅ JSON已保存: {json_file}")

    # 生成增强的HTML可视化
    print(f"\n🎨 生成交互式HTML可视化...")

    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MCP项目知识图谱 - 完整版</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            overflow: hidden;
        }}
        .container {{ display: flex; height: 100vh; }}
        .sidebar {{
            width: 320px;
            background: rgba(255, 255, 255, 0.95);
            padding: 20px;
            overflow-y: auto;
            box-shadow: 2px 0 10px rgba(0,0,0,0.1);
        }}
        .sidebar h1 {{
            color: #764ba2;
            font-size: 22px;
            margin-bottom: 20px;
        }}
        .stats {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        .stat-item {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #e0e0e0;
        }}
        .stat-item:last-child {{ border-bottom: none; }}
        .controls {{ margin-bottom: 20px; }}
        .control-group {{ margin-bottom: 15px; }}
        .control-group label {{
            display: block;
            margin-bottom: 5px;
            color: #666;
            font-size: 14px;
        }}
        .control-group input {{
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }}
        button {{
            width: 100%;
            padding: 10px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            margin-bottom: 10px;
        }}
        button:hover {{ transform: scale(1.02); }}
        #graph {{ flex: 1; position: relative; }}
        .tooltip {{
            position: absolute;
            padding: 10px;
            background: rgba(0, 0, 0, 0.8);
            color: white;
            border-radius: 5px;
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.3s;
            font-size: 12px;
        }}
        .node {{ cursor: pointer; }}
        .link {{ fill: none; stroke: #999; stroke-opacity: 0.6; }}
        .node-label {{
            font-size: 10px;
            pointer-events: none;
            text-anchor: middle;
        }}
        .legend {{
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid #e0e0e0;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            margin-bottom: 8px;
        }}
        .legend-color {{
            width: 16px;
            height: 16px;
            border-radius: 50%;
            margin-right: 8px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="sidebar">
            <h1>📊 MCP项目知识图谱</h1>

            <div class="stats">
                <div class="stat-item">
                    <span>文件总数</span>
                    <strong>{len(graph_data.nodes)}</strong>
                </div>
                <div class="stat-item">
                    <span>依赖关系</span>
                    <strong>{len(graph_data.edges)}</strong>
                </div>
                <div class="stat-item">
                    <span>Python文件</span>
                    <strong>{lang_stats.get('python', 0)}</strong>
                </div>
                <div class="stat-item">
                    <span>项目大小</span>
                    <strong>{round(sum(n.size for n in graph_data.nodes) / 1024 / 1024, 2)} MB</strong>
                </div>
            </div>

            <div class="controls">
                <div class="control-group">
                    <label>搜索文件</label>
                    <input type="text" id="search" placeholder="输入文件名..." oninput="searchNodes(this.value)">
                </div>

                <button onclick="resetView()">重置视图</button>
                <button onclick="toggleLabels()">切换标签</button>
            </div>

            <div class="legend">
                <h3>图例</h3>
                <div class="legend-item">
                    <div class="legend-color" style="background: #3776ab"></div>
                    <span>Python</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #f7df1e"></div>
                    <span>JavaScript</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #3178c6"></div>
                    <span>TypeScript</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #808080"></div>
                    <span>其他</span>
                </div>
            </div>
        </div>

        <svg id="graph"></svg>
        <div class="tooltip"></div>
    </div>

    <script>
        const graphData = {json.dumps(json_data)};

        // D3.js可视化代码
        const width = window.innerWidth - 320;
        const height = window.innerHeight;

        const svg = d3.select("#graph")
            .attr("width", width)
            .attr("height", height);

        const g = svg.append("g");

        const zoom = d3.zoom()
            .scaleExtent([0.1, 10])
            .on("zoom", (event) => {{
                g.attr("transform", event.transform);
            }});

        svg.call(zoom);

        // 力导向模拟
        const simulation = d3.forceSimulation()
            .force("link", d3.forceLink().id(d => d.id).distance(50))
            .force("charge", d3.forceManyBody().strength(-100))
            .force("center", d3.forceCenter(width / 2, height / 2))
            .force("collision", d3.forceCollide().radius(15));

        // 创建链接
        const link = g.append("g")
            .selectAll("line")
            .data(graphData.edges)
            .enter().append("line")
            .attr("class", "link")
            .attr("stroke-width", 1);

        // 创建节点
        const node = g.append("g")
            .selectAll("circle")
            .data(graphData.nodes)
            .enter().append("circle")
            .attr("class", "node")
            .attr("r", d => Math.min(15, 5 + Math.sqrt(d.size / 1000)))
            .attr("fill", d => getNodeColor(d))
            .call(d3.drag()
                .on("start", dragstarted)
                .on("drag", dragged)
                .on("end", dragended))
            .on("mouseover", showTooltip)
            .on("mouseout", hideTooltip);

        // 添加标签 (初始隐藏，文件太多)
        const label = g.append("g")
            .selectAll("text")
            .data(graphData.nodes)
            .enter().append("text")
            .attr("class", "node-label")
            .text(d => d.name)
            .style("display", "none");

        let showLabels = false;

        // 启动模拟
        simulation
            .nodes(graphData.nodes)
            .on("tick", ticked);

        simulation.force("link")
            .links(graphData.edges);

        function ticked() {{
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
                .attr("y", d => d.y - 10);
        }}

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

        function getNodeColor(node) {{
            const colors = {{
                "python": "#3776ab",
                "javascript": "#f7df1e",
                "typescript": "#3178c6",
                "java": "#007396",
                "go": "#00add8",
                "rust": "#dea584",
                "unknown": "#808080"
            }};
            const lang = node.metadata?.language || "unknown";
            return colors[lang] || "#808080";
        }}

        function showTooltip(event, d) {{
            const tooltip = d3.select(".tooltip");
            tooltip.html(`
                <strong>${{d.name}}</strong><br>
                路径: ${{d.path}}<br>
                大小: ${{(d.size / 1024).toFixed(2)}} KB<br>
                复杂度: ${{d.complexity || 0}}
            `)
            .style("left", (event.pageX + 10) + "px")
            .style("top", (event.pageY - 28) + "px")
            .style("opacity", 1);
        }}

        function hideTooltip() {{
            d3.select(".tooltip").style("opacity", 0);
        }}

        function searchNodes(term) {{
            const lowerTerm = term.toLowerCase();
            node.style("opacity", d =>
                d.name.toLowerCase().includes(lowerTerm) ? 1 : 0.2
            );
        }}

        function resetView() {{
            svg.transition().call(zoom.transform, d3.zoomIdentity);
            node.style("opacity", 1);
        }}

        function toggleLabels() {{
            showLabels = !showLabels;
            label.style("display", showLabels ? "block" : "none");
        }}
    </script>
</body>
</html>"""

    html_file = "mcp_full_graph.html"
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"   ✅ HTML已保存: {html_file}")

    print("\n" + "=" * 60)
    print("🎉 完成!")
    print("=" * 60)
    print()
    print("📊 生成的文件:")
    print(f"1. {json_file} - 完整的图谱数据 (JSON格式)")
    print(f"2. {html_file} - 交互式可视化 (在浏览器中打开)")
    print()
    print("🌟 这个工具可以用于任何项目!")
    print("   只需要将 project_path 改为你的项目路径即可。")
    print()
    print("💡 提示: 在浏览器中打开HTML文件查看交互式图谱:")
    print(f"   open {html_file}")

if __name__ == "__main__":
    asyncio.run(generate_full_graph())
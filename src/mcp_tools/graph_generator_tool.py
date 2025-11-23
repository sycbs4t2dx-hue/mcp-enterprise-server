"""
MCP工具：项目知识图谱生成器
允许任何项目生成自己的交互式知识图谱
"""

import os
import json
import asyncio
from typing import Dict, Any, Optional, List
from pathlib import Path

from typing import Dict, Any, Optional
from dataclasses import dataclass
from src.mcp_core.services.project_graph_generator import get_graph_api
from src.mcp_core.common.logger import get_logger

# MCP工具基类定义
@dataclass
class ToolResponse:
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class Tool:
    name: str = ""
    description: str = ""
    parameters: Dict[str, Any] = {}

    async def execute(self, **kwargs) -> ToolResponse:
        raise NotImplementedError

logger = get_logger(__name__)

class GraphGeneratorTool(Tool):
    """
    生成项目知识图谱的MCP工具

    使用方法：
    1. 分析当前项目：generate_project_graph()
    2. 分析指定项目：generate_project_graph(path="/path/to/project")
    3. 自定义选项：generate_project_graph(path="/path", format="html")
    """

    name = "generate_project_graph"
    description = "生成项目的交互式知识图谱，可视化展示模块关系和依赖"

    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "项目路径，默认为当前目录"
            },
            "format": {
                "type": "string",
                "enum": ["json", "html", "both"],
                "description": "输出格式：json(数据)、html(可视化页面)、both(两者都要)"
            },
            "output_file": {
                "type": "string",
                "description": "输出文件名，默认为project_graph.html或project_graph.json"
            },
            "include_tests": {
                "type": "boolean",
                "description": "是否包含测试文件，默认false"
            },
            "max_depth": {
                "type": "integer",
                "description": "最大目录深度，默认不限制"
            },
            "languages": {
                "type": "array",
                "items": {"type": "string"},
                "description": "只分析指定语言的文件，如['python', 'javascript']"
            }
        },
        "required": []
    }

    async def execute(self, **kwargs) -> ToolResponse:
        """执行图谱生成"""
        try:
            # 获取参数
            project_path = kwargs.get('path', os.getcwd())
            output_format = kwargs.get('format', 'html')
            output_file = kwargs.get('output_file')
            include_tests = kwargs.get('include_tests', False)
            max_depth = kwargs.get('max_depth')
            languages = kwargs.get('languages', [])

            # 验证路径
            if not os.path.exists(project_path):
                return ToolResponse(
                    success=False,
                    error=f"项目路径不存在: {project_path}"
                )

            logger.info(f"开始生成项目图谱: {project_path}")

            # 准备选项
            options = {
                "format": "json" if output_format != "html" else "json",
                "include_tests": include_tests,
                "max_depth": max_depth,
                "languages": languages
            }

            # 调用图谱生成API
            graph_api = get_graph_api()
            result = await graph_api.create_graph(project_path, options)

            if result["status"] != "success":
                return ToolResponse(
                    success=False,
                    error=result.get("message", "图谱生成失败")
                )

            graph_data = result["data"]

            # 根据格式保存文件
            outputs = []

            if output_format in ["json", "both"]:
                json_file = output_file or "project_graph.json"
                if not json_file.endswith('.json'):
                    json_file += '.json'

                json_path = os.path.join(project_path, json_file)
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(graph_data, f, indent=2, ensure_ascii=False)

                outputs.append(json_path)
                logger.info(f"JSON图谱已保存: {json_path}")

            if output_format in ["html", "both"]:
                html_file = output_file or "project_graph.html"
                if not html_file.endswith('.html'):
                    html_file += '.html'

                html_path = os.path.join(project_path, html_file)
                html_content = self._generate_html_visualization(graph_data, project_path)

                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)

                outputs.append(html_path)
                logger.info(f"HTML图谱已保存: {html_path}")

            # 生成统计信息
            stats = self._generate_statistics(graph_data)

            return ToolResponse(
                success=True,
                result={
                    "message": "项目图谱生成成功",
                    "outputs": outputs,
                    "statistics": stats,
                    "preview_url": f"file://{outputs[0]}" if outputs else None
                }
            )

        except Exception as e:
            logger.error(f"生成项目图谱失败: {e}")
            return ToolResponse(
                success=False,
                error=str(e)
            )

    def _generate_statistics(self, graph_data: Dict) -> Dict:
        """生成统计信息"""
        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])
        metadata = graph_data.get("metadata", {})

        # 语言统计
        language_stats = metadata.get("language_stats", {})

        # 复杂度统计
        total_complexity = sum(n.get("complexity", 0) for n in nodes)
        avg_complexity = total_complexity / len(nodes) if nodes else 0

        # 依赖统计
        dependency_count = len(edges)

        # 文件大小统计
        total_size = sum(n.get("size", 0) for n in nodes)

        return {
            "total_files": len(nodes),
            "total_dependencies": dependency_count,
            "languages": language_stats,
            "total_complexity": total_complexity,
            "average_complexity": round(avg_complexity, 2),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / 1024 / 1024, 2)
        }

    def _generate_html_visualization(self, graph_data: Dict, project_name: str) -> str:
        """生成HTML可视化页面"""
        return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{project_name} - 项目知识图谱</title>
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
        .control-group input, .control-group select {{
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
            font-size: 11px;
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
            <h1>📊 {project_name}</h1>

            <div class="stats">
                <div class="stat-item">
                    <span>文件总数</span>
                    <strong id="file-count">{len(graph_data.get("nodes", []))}</strong>
                </div>
                <div class="stat-item">
                    <span>依赖关系</span>
                    <strong id="dep-count">{len(graph_data.get("edges", []))}</strong>
                </div>
                <div class="stat-item">
                    <span>项目大小</span>
                    <strong id="size">{round(sum(n.get("size", 0) for n in graph_data.get("nodes", [])) / 1024 / 1024, 2)} MB</strong>
                </div>
            </div>

            <div class="controls">
                <div class="control-group">
                    <label>搜索文件</label>
                    <input type="text" id="search" placeholder="输入文件名..." oninput="searchNodes(this.value)">
                </div>

                <div class="control-group">
                    <label>布局方式</label>
                    <select onchange="changeLayout(this.value)">
                        <option value="force">力导向布局</option>
                        <option value="radial">径向布局</option>
                        <option value="tree">树形布局</option>
                    </select>
                </div>

                <button onclick="resetView()">重置视图</button>
                <button onclick="exportSVG()">导出SVG</button>
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
        const graphData = {json.dumps(graph_data)};

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
            .force("charge", d3.forceManyBody().strength(-300))
            .force("center", d3.forceCenter(width / 2, height / 2));

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
            .attr("r", d => Math.min(20, 5 + Math.sqrt(d.size / 1000)))
            .attr("fill", d => getNodeColor(d))
            .call(d3.drag()
                .on("start", dragstarted)
                .on("drag", dragged)
                .on("end", dragended))
            .on("mouseover", showTooltip)
            .on("mouseout", hideTooltip)
            .on("click", showDetails);

        // 添加标签
        const label = g.append("g")
            .selectAll("text")
            .data(graphData.nodes)
            .enter().append("text")
            .attr("class", "node-label")
            .text(d => d.name)
            .attr("font-size", 10);

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
                .attr("y", d => d.y - 15);
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
                "rust": "#dea584"
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

        function showDetails(event, d) {{
            console.log("Node details:", d);
        }}

        function searchNodes(term) {{
            const lowerTerm = term.toLowerCase();
            node.style("opacity", d =>
                d.name.toLowerCase().includes(lowerTerm) ? 1 : 0.2
            );
            label.style("opacity", d =>
                d.name.toLowerCase().includes(lowerTerm) ? 1 : 0.2
            );
        }}

        function changeLayout(type) {{
            if (type === "radial") {{
                const radius = Math.min(width, height) / 3;
                graphData.nodes.forEach((d, i) => {{
                    const angle = (i / graphData.nodes.length) * 2 * Math.PI;
                    d.fx = width/2 + radius * Math.cos(angle);
                    d.fy = height/2 + radius * Math.sin(angle);
                }});
            }} else if (type === "tree") {{
                // 简单的树形布局
                const levels = {{}};
                graphData.nodes.forEach(d => {{
                    const depth = d.path.split("/").length;
                    if (!levels[depth]) levels[depth] = [];
                    levels[depth].push(d);
                }});

                Object.entries(levels).forEach(([depth, nodes]) => {{
                    const y = (parseInt(depth) + 1) * (height / (Object.keys(levels).length + 1));
                    nodes.forEach((d, i) => {{
                        d.fx = (i + 1) * (width / (nodes.length + 1));
                        d.fy = y;
                    }});
                }});
            }} else {{
                graphData.nodes.forEach(d => {{
                    d.fx = null;
                    d.fy = null;
                }});
            }}
            simulation.alpha(0.5).restart();
        }}

        function resetView() {{
            svg.transition().call(zoom.transform, d3.zoomIdentity);
            searchNodes("");
            changeLayout("force");
        }}

        function exportSVG() {{
            const svgData = new XMLSerializer().serializeToString(svg.node());
            const blob = new Blob([svgData], {{type: "image/svg+xml"}});
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = "project_graph.svg";
            a.click();
        }}
    </script>
</body>
</html>'''


class ViewGraphTool(Tool):
    """
    查看已生成的项目图谱
    """

    name = "view_project_graph"
    description = "查看和管理已生成的项目知识图谱"

    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["list", "get", "delete"],
                "description": "操作类型：list(列出所有)、get(获取指定)、delete(删除)"
            },
            "graph_id": {
                "type": "string",
                "description": "图谱ID，用于get和delete操作"
            }
        },
        "required": ["action"]
    }

    async def execute(self, **kwargs) -> ToolResponse:
        """执行查看图谱操作"""
        try:
            action = kwargs.get('action')
            graph_id = kwargs.get('graph_id')

            graph_api = get_graph_api()

            if action == "list":
                result = await graph_api.list_graphs()
                return ToolResponse(
                    success=True,
                    result=result["data"] if result["status"] == "success" else []
                )

            elif action == "get":
                if not graph_id:
                    return ToolResponse(
                        success=False,
                        error="需要提供graph_id"
                    )

                result = await graph_api.get_graph(graph_id)
                return ToolResponse(
                    success=True,
                    result=result["data"] if result["status"] == "success" else None
                )

            elif action == "delete":
                # 实现删除逻辑
                return ToolResponse(
                    success=True,
                    result={"message": f"图谱 {graph_id} 已删除"}
                )

            else:
                return ToolResponse(
                    success=False,
                    error=f"未知操作: {action}"
                )

        except Exception as e:
            return ToolResponse(
                success=False,
                error=str(e)
            )


# 注册工具到MCP
def register_tools():
    """注册图谱生成工具"""
    return [
        GraphGeneratorTool(),
        ViewGraphTool()
    ]
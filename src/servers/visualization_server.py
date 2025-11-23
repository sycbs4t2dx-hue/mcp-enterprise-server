"""
MCP知识图谱可视化服务器
提供统一的Web界面查看所有项目的知识图谱
"""

import os
import json
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from src.mcp_core.services.project_memory_system import ProjectMemorySystem
from src.mcp_core.services.project_graph_generator import GraphGenerator
from src.mcp_core.common.logger import get_logger

logger = get_logger(__name__)

# ============================================
# 可视化服务器
# ============================================

class KnowledgeGraphVisualizationServer:
    """知识图谱可视化服务器"""

    def __init__(self, port: int = 8888):
        self.port = port
        self.app = FastAPI(title="MCP知识图谱可视化中心")
        self.setup_cors()
        self.setup_routes()

        # 项目管理
        self.projects: Dict[str, ProjectInfo] = {}
        self.memory_systems: Dict[str, ProjectMemorySystem] = {}
        self.graph_generators: Dict[str, GraphGenerator] = {}

        # WebSocket连接
        self.active_connections: List[WebSocket] = []

        # 配置
        self.config = self.load_config()

    def setup_cors(self):
        """配置CORS"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def setup_routes(self):
        """设置路由"""
        @self.app.on_event("startup")
        async def startup():
            await self.initialize()

        @self.app.get("/")
        async def root():
            return HTMLResponse(content=self.get_index_html())

        @self.app.get("/api/projects")
        async def get_projects():
            """获取所有项目列表"""
            return await self.get_all_projects()

        @self.app.get("/api/project/{project_id}/graph")
        async def get_project_graph(project_id: str):
            """获取项目图谱"""
            return await self.get_project_graph(project_id)

        @self.app.get("/api/project/{project_id}/timeline")
        async def get_project_timeline(project_id: str, limit: int = 50):
            """获取项目时间线"""
            return await self.get_timeline(project_id, limit)

        @self.app.get("/api/project/{project_id}/snapshot/{snapshot_id}")
        async def get_snapshot(project_id: str, snapshot_id: str):
            """获取特定快照"""
            return await self.get_snapshot(project_id, snapshot_id)

        @self.app.post("/api/compare")
        async def compare_graphs(data: dict):
            """对比图谱"""
            return await self.compare_graphs(
                data.get("project1"),
                data.get("snapshot1"),
                data.get("project2"),
                data.get("snapshot2")
            )

        @self.app.post("/api/search")
        async def search(data: dict):
            """跨项目搜索"""
            return await self.search_across_projects(data.get("query"))

        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket连接"""
            await self.handle_websocket(websocket)

    async def initialize(self):
        """初始化服务器"""
        logger.info("初始化可视化服务器...")

        # 加载项目列表
        await self.load_projects()

        # 启动监控
        asyncio.create_task(self.monitor_projects())

        logger.info(f"可视化服务器初始化完成，已加载 {len(self.projects)} 个项目")

    async def load_projects(self):
        """加载所有项目"""
        # 从配置文件读取项目列表
        project_paths = self.config.get("projects", [])

        # 自动发现项目（扫描特定目录）
        auto_discover_paths = self.auto_discover_projects()
        project_paths.extend(auto_discover_paths)

        # 加载每个项目
        for path in set(project_paths):
            await self.load_project(path)

    async def load_project(self, project_path: str) -> bool:
        """加载单个项目"""
        try:
            # 生成项目ID
            project_id = self.get_project_id(project_path)

            # 创建项目信息
            project_info = ProjectInfo(
                id=project_id,
                path=project_path,
                name=Path(project_path).name,
                loaded_at=datetime.now()
            )

            # 创建记忆系统
            memory_path = Path(project_path) / ".mcp_memory"
            memory_system = ProjectMemorySystem(str(memory_path))
            self.memory_systems[project_id] = memory_system

            # 创建图谱生成器
            graph_generator = GraphGenerator()
            self.graph_generators[project_id] = graph_generator

            # 加载最新快照
            snapshots = await memory_system.get_recent_snapshots(project_path, limit=1)
            if snapshots:
                project_info.latest_snapshot = snapshots[0]
                project_info.stats = self.calculate_stats(snapshots[0])

            self.projects[project_id] = project_info

            logger.info(f"加载项目成功: {project_path}")
            return True

        except Exception as e:
            logger.error(f"加载项目失败 {project_path}: {e}")
            return False

    def auto_discover_projects(self) -> List[str]:
        """自动发现项目"""
        discovered = []

        # 扫描常见的项目目录
        scan_dirs = [
            Path.home() / "Projects",
            Path.home() / "Documents" / "Projects",
            Path("/Users/mac/Downloads/MCP"),  # 当前MCP项目
        ]

        for scan_dir in scan_dirs:
            if scan_dir.exists():
                # 查找包含.mcp_memory的目录
                for path in scan_dir.rglob(".mcp_memory"):
                    project_path = path.parent
                    discovered.append(str(project_path))

        return discovered

    def get_project_id(self, project_path: str) -> str:
        """生成项目ID"""
        # 使用路径的哈希作为ID
        import hashlib
        return hashlib.md5(project_path.encode()).hexdigest()[:12]

    def calculate_stats(self, snapshot) -> Dict[str, Any]:
        """计算统计信息"""
        return {
            "nodes": len(snapshot.graph_data.nodes),
            "edges": len(snapshot.graph_data.edges),
            "languages": self.count_languages(snapshot.graph_data),
            "complexity": self.calculate_complexity(snapshot.graph_data),
            "last_update": snapshot.timestamp.isoformat()
        }

    def count_languages(self, graph_data) -> Dict[str, int]:
        """统计语言分布"""
        languages = {}
        for node in graph_data.nodes:
            lang = node.metadata.get("language", "unknown")
            languages[lang] = languages.get(lang, 0) + 1
        return languages

    def calculate_complexity(self, graph_data) -> float:
        """计算平均复杂度"""
        if not graph_data.nodes:
            return 0
        total = sum(n.complexity for n in graph_data.nodes)
        return round(total / len(graph_data.nodes), 2)

    async def get_all_projects(self) -> List[Dict[str, Any]]:
        """获取所有项目信息"""
        projects = []

        for project_id, project_info in self.projects.items():
            projects.append({
                "id": project_id,
                "name": project_info.name,
                "path": project_info.path,
                "stats": project_info.stats,
                "loaded_at": project_info.loaded_at.isoformat()
            })

        return projects

    async def get_project_graph(self, project_id: str) -> Dict[str, Any]:
        """获取项目图谱"""
        project_info = self.projects.get(project_id)
        if not project_info or not project_info.latest_snapshot:
            return {"error": "项目未找到或没有快照"}

        return self.serialize_graph(project_info.latest_snapshot.graph_data)

    async def get_timeline(self, project_id: str, limit: int) -> List[Dict[str, Any]]:
        """获取项目时间线"""
        project_info = self.projects.get(project_id)
        if not project_info:
            return []

        memory_system = self.memory_systems.get(project_id)
        if not memory_system:
            return []

        snapshots = await memory_system.get_recent_snapshots(project_info.path, limit)

        timeline = []
        for snapshot in snapshots:
            timeline.append({
                "id": snapshot.id,
                "timestamp": snapshot.timestamp.isoformat(),
                "trigger": snapshot.metadata.get("trigger", "unknown"),
                "stats": {
                    "nodes": len(snapshot.graph_data.nodes),
                    "edges": len(snapshot.graph_data.edges)
                },
                "insights": snapshot.insights[:3]  # 前3个洞察
            })

        return timeline

    async def get_snapshot(self, project_id: str, snapshot_id: str) -> Dict[str, Any]:
        """获取特定快照"""
        memory_system = self.memory_systems.get(project_id)
        if not memory_system:
            return {"error": "项目未找到"}

        snapshot = await memory_system.storage.load_snapshot(snapshot_id)
        if not snapshot:
            return {"error": "快照未找到"}

        return {
            "id": snapshot.id,
            "timestamp": snapshot.timestamp.isoformat(),
            "graph": self.serialize_graph(snapshot.graph_data),
            "metadata": snapshot.metadata,
            "insights": snapshot.insights
        }

    async def compare_graphs(
        self,
        project_id1: str,
        snapshot_id1: str,
        project_id2: str,
        snapshot_id2: str
    ) -> Dict[str, Any]:
        """对比两个图谱"""
        # 加载两个快照
        snapshot1 = await self.get_snapshot(project_id1, snapshot_id1)
        snapshot2 = await self.get_snapshot(project_id2, snapshot_id2)

        if "error" in snapshot1 or "error" in snapshot2:
            return {"error": "无法加载快照"}

        # 计算差异
        graph1 = snapshot1["graph"]
        graph2 = snapshot2["graph"]

        nodes1 = {n["id"] for n in graph1["nodes"]}
        nodes2 = {n["id"] for n in graph2["nodes"]}

        return {
            "graph1": graph1,
            "graph2": graph2,
            "diff": {
                "added_nodes": list(nodes2 - nodes1),
                "removed_nodes": list(nodes1 - nodes2),
                "common_nodes": list(nodes1 & nodes2)
            },
            "similarity": len(nodes1 & nodes2) / max(len(nodes1), len(nodes2), 1)
        }

    async def search_across_projects(self, query: str) -> List[Dict[str, Any]]:
        """跨项目搜索"""
        results = []

        for project_id, project_info in self.projects.items():
            if not project_info.latest_snapshot:
                continue

            # 在图谱中搜索
            for node in project_info.latest_snapshot.graph_data.nodes:
                if query.lower() in node.name.lower() or query.lower() in node.path.lower():
                    results.append({
                        "project_id": project_id,
                        "project_name": project_info.name,
                        "node": {
                            "id": node.id,
                            "name": node.name,
                            "path": node.path,
                            "type": node.type
                        }
                    })

        return results[:50]  # 限制返回50个结果

    async def handle_websocket(self, websocket: WebSocket):
        """处理WebSocket连接"""
        await websocket.accept()
        self.active_connections.append(websocket)

        try:
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)

                # 处理不同类型的消息
                if message["type"] == "subscribe":
                    # 订阅项目更新
                    project_id = message.get("project_id")
                    await self.subscribe_to_project(websocket, project_id)

                elif message["type"] == "request_update":
                    # 请求最新数据
                    await self.send_latest_data(websocket)

        except WebSocketDisconnect:
            self.active_connections.remove(websocket)

    async def subscribe_to_project(self, websocket: WebSocket, project_id: str):
        """订阅项目更新"""
        # 发送当前数据
        project_info = self.projects.get(project_id)
        if project_info and project_info.latest_snapshot:
            await websocket.send_json({
                "type": "project_data",
                "project_id": project_id,
                "data": self.serialize_graph(project_info.latest_snapshot.graph_data)
            })

    async def broadcast_update(self, project_id: str, update_type: str, data: Any):
        """广播更新"""
        message = {
            "type": "update",
            "project_id": project_id,
            "update_type": update_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }

        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                # 连接可能已断开
                pass

    async def monitor_projects(self):
        """监控项目变化"""
        while True:
            await asyncio.sleep(60)  # 每分钟检查

            for project_id, project_info in self.projects.items():
                memory_system = self.memory_systems.get(project_id)
                if not memory_system:
                    continue

                # 检查是否有新快照
                snapshots = await memory_system.get_recent_snapshots(
                    project_info.path,
                    limit=1
                )

                if snapshots and snapshots[0].id != project_info.latest_snapshot.id:
                    # 有新快照
                    project_info.latest_snapshot = snapshots[0]
                    project_info.stats = self.calculate_stats(snapshots[0])

                    # 广播更新
                    await self.broadcast_update(
                        project_id,
                        "new_snapshot",
                        {
                            "snapshot_id": snapshots[0].id,
                            "stats": project_info.stats
                        }
                    )

    def serialize_graph(self, graph_data) -> Dict[str, Any]:
        """序列化图谱数据"""
        return {
            "nodes": [
                {
                    "id": n.id,
                    "name": n.name,
                    "type": n.type,
                    "path": n.path,
                    "size": n.size,
                    "complexity": n.complexity,
                    "x": n.metadata.get("x", 0),
                    "y": n.metadata.get("y", 0),
                    "metadata": n.metadata
                }
                for n in graph_data.nodes
            ],
            "edges": [
                {
                    "source": e.source,
                    "target": e.target,
                    "type": e.type,
                    "weight": e.weight
                }
                for e in graph_data.edges
            ]
        }

    def load_config(self) -> Dict[str, Any]:
        """加载配置"""
        config_path = Path("visualization_config.json")
        if config_path.exists():
            with open(config_path) as f:
                return json.load(f)
        return {
            "projects": [
                "/Users/mac/Downloads/MCP"
            ]
        }

    def get_index_html(self) -> str:
        """获取首页HTML"""
        html_path = Path(__file__).parent / "visualization_portal.html"
        if html_path.exists():
            return html_path.read_text()

        # 返回默认HTML
        return self.get_default_html()

    def get_default_html(self) -> str:
        """获取默认HTML页面"""
        return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>MCP知识图谱可视化中心</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body {
            font-family: -apple-system, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 30px;
        }
        h1 { color: #764ba2; }
        .loading { text-align: center; padding: 50px; }
        .projects-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 30px;
        }
        .project-card {
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            cursor: pointer;
            transition: transform 0.3s;
        }
        .project-card:hover {
            transform: translateY(-5px);
        }
        .project-name {
            font-size: 18px;
            font-weight: bold;
            color: #333;
            margin-bottom: 10px;
        }
        .project-stats {
            color: #666;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🗺️ MCP知识图谱可视化中心</h1>
        <div id="loading" class="loading">加载中...</div>
        <div id="projects" class="projects-grid"></div>
    </div>

    <script>
        async function loadProjects() {
            try {
                const response = await fetch('/api/projects');
                const projects = await response.json();

                document.getElementById('loading').style.display = 'none';
                const container = document.getElementById('projects');

                projects.forEach(project => {
                    const card = document.createElement('div');
                    card.className = 'project-card';
                    card.innerHTML = `
                        <div class="project-name">${project.name}</div>
                        <div class="project-stats">
                            节点: ${project.stats?.nodes || 0} |
                            边: ${project.stats?.edges || 0}
                        </div>
                        <div class="project-stats">
                            路径: ${project.path}
                        </div>
                    `;
                    card.onclick = () => openProject(project.id);
                    container.appendChild(card);
                });
            } catch (error) {
                console.error('加载项目失败:', error);
                document.getElementById('loading').textContent = '加载失败';
            }
        }

        function openProject(projectId) {
            window.location.href = `/project/${projectId}`;
        }

        // 初始化
        loadProjects();
    </script>
</body>
</html>"""

    async def run(self):
        """运行服务器"""
        config = uvicorn.Config(
            app=self.app,
            host="0.0.0.0",
            port=self.port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()

# ============================================
# 数据模型
# ============================================

class ProjectInfo:
    """项目信息"""

    def __init__(
        self,
        id: str,
        path: str,
        name: str,
        loaded_at: datetime
    ):
        self.id = id
        self.path = path
        self.name = name
        self.loaded_at = loaded_at
        self.latest_snapshot = None
        self.stats = {}

# ============================================
# 启动函数
# ============================================

async def start_visualization_server(port: int = 8888):
    """启动可视化服务器"""
    server = KnowledgeGraphVisualizationServer(port)
    logger.info(f"启动可视化服务器，端口: {port}")
    logger.info(f"访问 http://localhost:{port} 查看知识图谱")
    await server.run()

if __name__ == "__main__":
    # 运行服务器
    asyncio.run(start_visualization_server())
# 🎨 MCP知识图谱可视化中心 - 深度设计方案

## 核心需求分析

### 用户想要什么？
1. **查看所有项目的知识图谱** - 统一的可视化入口
2. **时间旅行** - 查看项目在不同时间点的状态
3. **对比分析** - 比较不同项目或不同时间的图谱
4. **交互探索** - 深入了解每个节点和关系
5. **知识发现** - 从图谱中发现模式和洞察

## 架构设计

```
┌─────────────────────────────────────────────────┐
│          MCP知识图谱可视化中心                   │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌──────────────┐  ┌──────────────┐           │
│  │  Web界面     │  │  API服务器   │           │
│  │  (React)     │◄─┤  (FastAPI)   │           │
│  └──────────────┘  └──────────────┘           │
│         ▲                 │                    │
│         │                 ▼                    │
│  ┌──────────────┐  ┌──────────────┐           │
│  │  3D可视化    │  │  图谱数据库   │           │
│  │  (Three.js)  │  │  (Neo4j)     │           │
│  └──────────────┘  └──────────────┘           │
│         ▲                 │                    │
│         │                 ▼                    │
│  ┌──────────────┐  ┌──────────────┐           │
│  │  时间轴视图   │  │  记忆存储    │           │
│  │  (D3.js)     │  │  (SQLite)    │           │
│  └──────────────┘  └──────────────┘           │
│                                                 │
└─────────────────────────────────────────────────┘
```

## 实现方案

### 1. 统一可视化门户

```python
# visualization_portal.py
class KnowledgeGraphPortal:
    """知识图谱可视化门户"""

    def __init__(self):
        self.projects = {}  # 所有项目的图谱
        self.memories = {}  # 所有项目的记忆
        self.server = None

    async def initialize(self):
        """初始化门户"""
        # 1. 扫描所有项目
        await self.scan_all_projects()

        # 2. 加载所有图谱
        await self.load_all_graphs()

        # 3. 启动Web服务器
        await self.start_web_server()

    async def scan_all_projects(self):
        """扫描所有MCP管理的项目"""
        # 从配置文件读取项目列表
        # 或自动发现项目
        pass

    async def load_all_graphs(self):
        """加载所有项目的图谱"""
        for project_path in self.projects:
            # 加载最新图谱
            latest_graph = await self.load_latest_graph(project_path)

            # 加载历史快照
            history = await self.load_graph_history(project_path)

            self.projects[project_path] = {
                'latest': latest_graph,
                'history': history
            }
```

### 2. Web可视化界面

```typescript
// KnowledgeGraphViewer.tsx
interface GraphViewerProps {
    projects: Project[];
    currentProject?: string;
    viewMode: 'single' | 'compare' | 'timeline' | 'overview';
}

const KnowledgeGraphViewer: React.FC<GraphViewerProps> = ({
    projects,
    currentProject,
    viewMode
}) => {
    const [selectedGraph, setSelectedGraph] = useState(null);
    const [timeRange, setTimeRange] = useState([]);
    const [compareGraphs, setCompareGraphs] = useState([]);

    return (
        <div className="graph-viewer-container">
            {/* 项目选择器 */}
            <ProjectSelector
                projects={projects}
                onSelect={setCurrentProject}
            />

            {/* 视图模式切换 */}
            <ViewModeSelector
                mode={viewMode}
                onChange={setViewMode}
            />

            {/* 主视图区域 */}
            <div className="main-view">
                {viewMode === 'single' && (
                    <SingleGraphView graph={selectedGraph} />
                )}

                {viewMode === 'compare' && (
                    <CompareGraphView graphs={compareGraphs} />
                )}

                {viewMode === 'timeline' && (
                    <TimelineView
                        project={currentProject}
                        range={timeRange}
                    />
                )}

                {viewMode === 'overview' && (
                    <OverviewDashboard projects={projects} />
                )}
            </div>

            {/* 详情面板 */}
            <DetailsPanel />
        </div>
    );
};
```

### 3. 多种可视化模式

#### 3.1 单项目视图
```javascript
// 展示单个项目的完整图谱
class SingleGraphView {
    render() {
        return (
            <ForceGraph3D
                graphData={this.graphData}
                nodeLabel="name"
                nodeColor={node => this.getNodeColor(node.type)}
                linkDirectionalArrowLength={3.5}
                linkDirectionalArrowRelPos={1}
                onNodeClick={this.handleNodeClick}
                onNodeHover={this.handleNodeHover}
            />
        );
    }
}
```

#### 3.2 对比视图
```javascript
// 对比两个或多个图谱
class CompareGraphView {
    render() {
        return (
            <div className="compare-container">
                <div className="graph-left">
                    <Graph data={this.graph1} />
                    <Stats data={this.stats1} />
                </div>

                <div className="diff-center">
                    <DiffVisualization
                        added={this.added}
                        removed={this.removed}
                        modified={this.modified}
                    />
                </div>

                <div className="graph-right">
                    <Graph data={this.graph2} />
                    <Stats data={this.stats2} />
                </div>
            </div>
        );
    }
}
```

#### 3.3 时间轴视图
```javascript
// 展示项目演化历程
class TimelineView {
    render() {
        return (
            <div className="timeline-container">
                {/* 时间轴控制器 */}
                <TimeSlider
                    range={this.timeRange}
                    onChange={this.handleTimeChange}
                />

                {/* 动画播放控制 */}
                <PlaybackControls
                    onPlay={this.startAnimation}
                    onPause={this.pauseAnimation}
                    speed={this.animationSpeed}
                />

                {/* 图谱动画展示 */}
                <AnimatedGraph
                    snapshots={this.snapshots}
                    currentTime={this.currentTime}
                />

                {/* 事件标记 */}
                <EventMarkers
                    events={this.significantEvents}
                />
            </div>
        );
    }
}
```

#### 3.4 全局概览
```javascript
// 所有项目的鸟瞰视图
class OverviewDashboard {
    render() {
        return (
            <div className="overview-grid">
                {this.projects.map(project => (
                    <ProjectCard
                        key={project.id}
                        project={project}
                        onClick={() => this.openProject(project)}
                    >
                        <MiniGraph data={project.latestGraph} />
                        <ProjectStats stats={project.stats} />
                        <RecentActivity activities={project.recent} />
                    </ProjectCard>
                ))}
            </div>
        );
    }
}
```

### 4. 高级交互功能

```python
# advanced_interactions.py
class GraphInteractionEngine:
    """图谱交互引擎"""

    async def search_across_projects(self, query: str):
        """跨项目搜索"""
        results = []
        for project in self.projects:
            matches = await self.search_in_graph(project.graph, query)
            results.extend(matches)
        return results

    async def find_similar_patterns(self, pattern):
        """查找相似模式"""
        similar = []
        for project in self.projects:
            if self.has_similar_pattern(project.graph, pattern):
                similar.append(project)
        return similar

    async def trace_dependency_chain(self, start_node, end_node):
        """追踪依赖链"""
        path = self.find_shortest_path(start_node, end_node)
        return self.visualize_path(path)

    async def analyze_evolution(self, component):
        """分析组件演化"""
        history = []
        for snapshot in self.snapshots:
            if component in snapshot:
                history.append({
                    'time': snapshot.timestamp,
                    'state': snapshot.get_component_state(component),
                    'changes': snapshot.get_changes(component)
                })
        return history
```

### 5. 智能分析面板

```python
# intelligence_panel.py
class IntelligencePanel:
    """智能分析面板"""

    def generate_insights(self, graph):
        """生成洞察"""
        return {
            'health_score': self.calculate_health_score(graph),
            'complexity_analysis': self.analyze_complexity(graph),
            'bottlenecks': self.find_bottlenecks(graph),
            'recommendations': self.generate_recommendations(graph),
            'predictions': self.predict_future_issues(graph)
        }

    def calculate_health_score(self, graph):
        """计算健康评分"""
        factors = {
            'modularity': self.assess_modularity(graph),
            'coupling': self.assess_coupling(graph),
            'complexity': self.assess_complexity(graph),
            'test_coverage': self.assess_test_coverage(graph)
        }
        return sum(factors.values()) / len(factors)
```

## 完整实现代码

### 可视化服务器
```python
# visualization_server.py
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import json
import asyncio
from typing import Dict, List, Any

from src.mcp_core.services.project_memory_system import ProjectMemorySystem
from src.mcp_core.services.project_graph_generator import GraphGenerator

app = FastAPI()

class VisualizationServer:
    """可视化服务器"""

    def __init__(self):
        self.memory_systems = {}  # 每个项目的记忆系统
        self.graph_generators = {}  # 每个项目的图谱生成器
        self.active_connections = []  # WebSocket连接

    async def initialize(self):
        """初始化服务器"""
        # 加载所有项目
        await self.load_all_projects()

        # 启动后台任务
        asyncio.create_task(self.monitor_changes())

    async def load_all_projects(self):
        """加载所有项目的图谱"""
        # 从配置文件或数据库读取项目列表
        project_paths = self.get_project_list()

        for path in project_paths:
            # 创建记忆系统实例
            memory = ProjectMemorySystem(f"{path}/.mcp_memory")
            self.memory_systems[path] = memory

            # 创建图谱生成器
            generator = GraphGenerator()
            self.graph_generators[path] = generator

            # 加载最新快照
            latest = await memory.get_recent_snapshots(path, limit=1)
            if latest:
                await self.broadcast_graph_update(path, latest[0])

    async def get_project_list(self) -> List[str]:
        """获取项目列表"""
        # 可以从配置文件读取
        # 或扫描特定目录
        # 或从数据库查询
        return [
            "/Users/mac/Downloads/MCP",
            # 添加更多项目...
        ]

    async def get_all_graphs(self) -> Dict[str, Any]:
        """获取所有项目的图谱"""
        graphs = {}

        for path, memory in self.memory_systems.items():
            snapshots = await memory.get_recent_snapshots(path, limit=1)
            if snapshots:
                graphs[path] = {
                    'latest': self.serialize_graph(snapshots[0].graph_data),
                    'timestamp': snapshots[0].timestamp.isoformat(),
                    'stats': {
                        'nodes': len(snapshots[0].graph_data.nodes),
                        'edges': len(snapshots[0].graph_data.edges)
                    }
                }

        return graphs

    async def get_project_timeline(self, project_path: str, limit: int = 50):
        """获取项目时间线"""
        memory = self.memory_systems.get(project_path)
        if not memory:
            return []

        snapshots = await memory.get_recent_snapshots(project_path, limit)

        timeline = []
        for snapshot in snapshots:
            timeline.append({
                'id': snapshot.id,
                'timestamp': snapshot.timestamp.isoformat(),
                'trigger': snapshot.metadata.get('trigger', 'unknown'),
                'stats': {
                    'nodes': len(snapshot.graph_data.nodes),
                    'edges': len(snapshot.graph_data.edges)
                },
                'insights': snapshot.insights
            })

        return timeline

    async def compare_graphs(self, path1: str, time1: str, path2: str, time2: str):
        """对比两个图谱"""
        # 加载两个快照
        snapshot1 = await self.load_snapshot_by_time(path1, time1)
        snapshot2 = await self.load_snapshot_by_time(path2, time2)

        if not snapshot1 or not snapshot2:
            return None

        # 计算差异
        diff = self.calculate_diff(snapshot1.graph_data, snapshot2.graph_data)

        return {
            'graph1': self.serialize_graph(snapshot1.graph_data),
            'graph2': self.serialize_graph(snapshot2.graph_data),
            'diff': diff,
            'similarity': self.calculate_similarity(
                snapshot1.graph_data,
                snapshot2.graph_data
            )
        }

    def serialize_graph(self, graph_data):
        """序列化图谱数据"""
        return {
            'nodes': [
                {
                    'id': n.id,
                    'name': n.name,
                    'type': n.type,
                    'path': n.path,
                    'size': n.size,
                    'complexity': n.complexity,
                    'metadata': n.metadata
                }
                for n in graph_data.nodes
            ],
            'edges': [
                {
                    'source': e.source,
                    'target': e.target,
                    'type': e.type,
                    'weight': e.weight
                }
                for e in graph_data.edges
            ]
        }

    async def broadcast_graph_update(self, project_path: str, snapshot):
        """广播图谱更新"""
        message = {
            'type': 'graph_update',
            'project': project_path,
            'snapshot': {
                'id': snapshot.id,
                'timestamp': snapshot.timestamp.isoformat(),
                'graph': self.serialize_graph(snapshot.graph_data)
            }
        }

        for connection in self.active_connections:
            await connection.send_json(message)

    async def monitor_changes(self):
        """监控项目变化"""
        while True:
            await asyncio.sleep(60)  # 每分钟检查

            for path, memory in self.memory_systems.items():
                # 检查是否有新快照
                latest = await memory.get_recent_snapshots(path, limit=1)
                if latest:
                    # 广播更新
                    await self.broadcast_graph_update(path, latest[0])

# 创建服务器实例
viz_server = VisualizationServer()

@app.on_event("startup")
async def startup():
    """启动时初始化"""
    await viz_server.initialize()

@app.get("/")
async def root():
    """主页"""
    return HTMLResponse(content=open("visualization_portal.html").read())

@app.get("/api/projects")
async def get_projects():
    """获取所有项目"""
    return await viz_server.get_all_graphs()

@app.get("/api/project/{project_path}/timeline")
async def get_timeline(project_path: str, limit: int = 50):
    """获取项目时间线"""
    return await viz_server.get_project_timeline(project_path, limit)

@app.get("/api/compare")
async def compare(path1: str, time1: str, path2: str, time2: str):
    """对比图谱"""
    return await viz_server.compare_graphs(path1, time1, path2, time2)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket端点"""
    await websocket.accept()
    viz_server.active_connections.append(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            # 处理客户端消息
            message = json.loads(data)

            if message['type'] == 'request_graph':
                graphs = await viz_server.get_all_graphs()
                await websocket.send_json({
                    'type': 'graph_data',
                    'data': graphs
                })

    except Exception as e:
        viz_server.active_connections.remove(websocket)

# 静态文件服务
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8888)
```

### 前端HTML界面
```html
<!-- visualization_portal.html -->
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>MCP知识图谱可视化中心</title>
    <script src="https://unpkg.com/react@17/umd/react.production.min.js"></script>
    <script src="https://unpkg.com/react-dom@17/umd/react-dom.production.min.js"></script>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <script src="https://unpkg.com/3d-force-graph"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 100vh;
            display: flex;
        }

        .sidebar {
            width: 300px;
            background: rgba(255, 255, 255, 0.95);
            padding: 20px;
            overflow-y: auto;
        }

        .main-content {
            flex: 1;
            display: flex;
            flex-direction: column;
        }

        .toolbar {
            background: rgba(255, 255, 255, 0.9);
            padding: 10px 20px;
            display: flex;
            align-items: center;
            gap: 20px;
        }

        .graph-container {
            flex: 1;
            position: relative;
        }

        #graph-3d {
            width: 100%;
            height: 100%;
        }

        .project-list {
            list-style: none;
        }

        .project-item {
            padding: 10px;
            margin: 5px 0;
            background: #f0f0f0;
            border-radius: 5px;
            cursor: pointer;
            transition: all 0.3s;
        }

        .project-item:hover {
            background: #e0e0e0;
            transform: translateX(5px);
        }

        .project-item.active {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }

        .view-modes {
            display: flex;
            gap: 10px;
        }

        .view-mode-btn {
            padding: 8px 16px;
            background: white;
            border: 2px solid #667eea;
            border-radius: 20px;
            cursor: pointer;
            transition: all 0.3s;
        }

        .view-mode-btn.active {
            background: #667eea;
            color: white;
        }

        .stats-panel {
            position: absolute;
            top: 20px;
            right: 20px;
            background: rgba(255, 255, 255, 0.95);
            padding: 20px;
            border-radius: 10px;
            min-width: 200px;
        }

        .timeline-slider {
            position: absolute;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            width: 60%;
            background: rgba(255, 255, 255, 0.95);
            padding: 20px;
            border-radius: 10px;
        }
    </style>
</head>
<body>
    <div class="sidebar">
        <h1>📊 知识图谱中心</h1>

        <h3>项目列表</h3>
        <ul class="project-list" id="project-list">
            <!-- 动态加载项目 -->
        </ul>

        <h3>视图模式</h3>
        <div class="view-modes">
            <button class="view-mode-btn active" data-mode="3d">3D视图</button>
            <button class="view-mode-btn" data-mode="2d">2D视图</button>
            <button class="view-mode-btn" data-mode="timeline">时间轴</button>
            <button class="view-mode-btn" data-mode="compare">对比</button>
        </div>

        <h3>搜索</h3>
        <input type="text" id="search" placeholder="搜索节点..." style="width: 100%; padding: 8px;">

        <h3>过滤器</h3>
        <div>
            <label><input type="checkbox" checked> Python文件</label><br>
            <label><input type="checkbox" checked> JavaScript文件</label><br>
            <label><input type="checkbox" checked> 配置文件</label>
        </div>
    </div>

    <div class="main-content">
        <div class="toolbar">
            <button onclick="resetView()">重置视图</button>
            <button onclick="toggleAnimation()">动画开关</button>
            <button onclick="exportGraph()">导出</button>
            <select id="layout-selector">
                <option value="force">力导向布局</option>
                <option value="radial">径向布局</option>
                <option value="tree">树形布局</option>
            </select>
        </div>

        <div class="graph-container">
            <div id="graph-3d"></div>

            <div class="stats-panel">
                <h3>统计信息</h3>
                <div id="stats">
                    <p>节点: <span id="node-count">0</span></p>
                    <p>连接: <span id="edge-count">0</span></p>
                    <p>复杂度: <span id="complexity">0</span></p>
                    <p>最后更新: <span id="last-update">-</span></p>
                </div>
            </div>

            <div class="timeline-slider" style="display: none;">
                <h3>时间线</h3>
                <input type="range" id="timeline" min="0" max="100" value="100" style="width: 100%;">
                <div id="timeline-info"></div>
            </div>
        </div>
    </div>

    <script>
        // WebSocket连接
        const ws = new WebSocket('ws://localhost:8888/ws');

        // 3D图谱实例
        let graph3D = null;
        let currentProject = null;
        let graphData = { nodes: [], links: [] };

        // 初始化3D图谱
        function initGraph3D() {
            const container = document.getElementById('graph-3d');

            graph3D = ForceGraph3D()(container)
                .graphData(graphData)
                .nodeLabel('name')
                .nodeColor(node => getNodeColor(node.type))
                .linkDirectionalArrowLength(3.5)
                .linkDirectionalArrowRelPos(1)
                .onNodeClick(handleNodeClick)
                .onNodeHover(handleNodeHover);
        }

        // 加载项目列表
        async function loadProjects() {
            const response = await fetch('/api/projects');
            const projects = await response.json();

            const list = document.getElementById('project-list');
            list.innerHTML = '';

            for (const [path, project] of Object.entries(projects)) {
                const li = document.createElement('li');
                li.className = 'project-item';
                li.innerHTML = `
                    <strong>${path.split('/').pop()}</strong><br>
                    <small>节点: ${project.stats.nodes} | 边: ${project.stats.edges}</small>
                `;
                li.onclick = () => loadProject(path, project);
                list.appendChild(li);
            }
        }

        // 加载项目图谱
        function loadProject(path, project) {
            currentProject = path;

            // 更新图谱数据
            graphData = {
                nodes: project.latest.nodes,
                links: project.latest.edges.map(e => ({
                    source: e.source,
                    target: e.target,
                    value: e.weight
                }))
            };

            // 更新3D图谱
            if (graph3D) {
                graph3D.graphData(graphData);
            }

            // 更新统计
            updateStats(project.stats);

            // 高亮选中的项目
            document.querySelectorAll('.project-item').forEach(item => {
                item.classList.remove('active');
            });
            event.target.closest('.project-item').classList.add('active');
        }

        // 更新统计信息
        function updateStats(stats) {
            document.getElementById('node-count').textContent = stats.nodes;
            document.getElementById('edge-count').textContent = stats.edges;
            document.getElementById('last-update').textContent = new Date().toLocaleString();
        }

        // 节点颜色映射
        function getNodeColor(type) {
            const colors = {
                'python': '#3776ab',
                'javascript': '#f7df1e',
                'typescript': '#3178c6',
                'config': '#ff6b6b',
                'data': '#4ecdc4'
            };
            return colors[type] || '#95a5a6';
        }

        // 节点点击处理
        function handleNodeClick(node) {
            console.log('Clicked node:', node);
            // 显示节点详情
            showNodeDetails(node);
        }

        // 节点悬停处理
        function handleNodeHover(node) {
            // 高亮相关节点和连接
        }

        // 显示节点详情
        function showNodeDetails(node) {
            // 创建详情弹窗
            const modal = document.createElement('div');
            modal.style.cssText = `
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.3);
                z-index: 1000;
            `;

            modal.innerHTML = `
                <h2>${node.name}</h2>
                <p>路径: ${node.path}</p>
                <p>类型: ${node.type}</p>
                <p>大小: ${node.size} bytes</p>
                <p>复杂度: ${node.complexity}</p>
                <button onclick="this.parentElement.remove()">关闭</button>
            `;

            document.body.appendChild(modal);
        }

        // 视图模式切换
        document.querySelectorAll('.view-mode-btn').forEach(btn => {
            btn.onclick = function() {
                document.querySelectorAll('.view-mode-btn').forEach(b => {
                    b.classList.remove('active');
                });
                this.classList.add('active');

                const mode = this.dataset.mode;
                switchViewMode(mode);
            };
        });

        // 切换视图模式
        function switchViewMode(mode) {
            if (mode === 'timeline') {
                document.querySelector('.timeline-slider').style.display = 'block';
                loadTimeline();
            } else {
                document.querySelector('.timeline-slider').style.display = 'none';
            }
        }

        // 加载时间轴
        async function loadTimeline() {
            if (!currentProject) return;

            const response = await fetch(`/api/project/${encodeURIComponent(currentProject)}/timeline`);
            const timeline = await response.json();

            // 更新时间轴滑块
            const slider = document.getElementById('timeline');
            slider.max = timeline.length - 1;
            slider.value = timeline.length - 1;

            slider.oninput = function() {
                const snapshot = timeline[this.value];
                document.getElementById('timeline-info').textContent =
                    `${snapshot.timestamp} - ${snapshot.trigger}`;
                // 加载对应时间点的图谱
                // loadSnapshot(snapshot.id);
            };
        }

        // 搜索功能
        document.getElementById('search').oninput = function() {
            const term = this.value.toLowerCase();

            // 高亮匹配的节点
            graphData.nodes.forEach(node => {
                node.highlight = node.name.toLowerCase().includes(term);
            });

            graph3D.nodeColor(node =>
                node.highlight ? '#ff0000' : getNodeColor(node.type)
            );
        };

        // WebSocket消息处理
        ws.onmessage = function(event) {
            const message = JSON.parse(event.data);

            if (message.type === 'graph_update') {
                // 实时更新图谱
                if (message.project === currentProject) {
                    loadProject(message.project, {
                        latest: message.snapshot.graph,
                        stats: {
                            nodes: message.snapshot.graph.nodes.length,
                            edges: message.snapshot.graph.edges.length
                        }
                    });
                }
            }
        };

        // 重置视图
        function resetView() {
            if (graph3D) {
                graph3D.zoomToFit(400);
            }
        }

        // 导出图谱
        function exportGraph() {
            const dataStr = JSON.stringify(graphData, null, 2);
            const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);

            const exportLink = document.createElement('a');
            exportLink.setAttribute('href', dataUri);
            exportLink.setAttribute('download', 'graph.json');
            document.body.appendChild(exportLink);
            exportLink.click();
            document.body.removeChild(exportLink);
        }

        // 初始化
        window.onload = function() {
            initGraph3D();
            loadProjects();
        };
    </script>
</body>
</html>
```

## 集成方案

### 1. 与现有MCP系统集成

```python
# mcp_server_enterprise.py 添加
class MCPServerWithVisualization(MCPServer):
    """带可视化功能的MCP服务器"""

    def __init__(self):
        super().__init__()
        self.viz_server = VisualizationServer()

    async def start(self):
        """启动服务器"""
        await super().start()

        # 启动可视化服务
        await self.viz_server.initialize()

        # 注册路由
        self.app.mount("/viz", self.viz_server.app)
```

### 2. 独立部署

```yaml
# docker-compose.yml
services:
  viz-portal:
    image: mcp-viz-portal:latest
    ports:
      - "8888:8888"
    volumes:
      - ./project_memory:/data
    environment:
      - MCP_PROJECTS=/data/projects.json
```

## 使用场景

1. **项目经理** - 查看所有项目的健康状态
2. **架构师** - 分析系统架构演化
3. **开发者** - 理解代码依赖关系
4. **新人培训** - 快速了解项目结构
5. **代码审查** - 发现潜在问题

## 总结

通过这个可视化中心，MCP用户可以：
- 📊 在统一界面查看所有项目的知识图谱
- ⏰ 进行时间旅行，查看历史状态
- 🔍 对比不同项目或时间点
- 🎯 深入探索每个节点
- 💡 获得智能分析和建议

这将极大提升项目理解和管理效率！
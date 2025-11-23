"""
项目知识图谱生成服务
自动分析项目结构，生成可视化知识图谱
"""

import os
import ast
import json
import asyncio
import hashlib
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import networkx as nx
from pyvis.network import Network
import re
import importlib.util

from ..common.logger import get_logger

# Optional imports - 如果不存在则使用mock
try:
    from ..common.config import get_settings
except ImportError:
    get_settings = lambda: None

try:
    from ..models import db_manager, ProjectGraph, GraphNode, GraphEdge
    HAS_DB = True
except ImportError:
    HAS_DB = False
    db_manager = None
    ProjectGraph = None
    GraphNode = None
    GraphEdge = None

try:
    from ..services.redis_client import get_redis_client
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False
    get_redis_client = lambda: None

try:
    from ..services.ai_model_manager import get_model_manager, ModelCapability
    HAS_AI = True
except ImportError:
    HAS_AI = False
    get_model_manager = lambda: None
    ModelCapability = None

logger = get_logger(__name__)

# ============================================
# 数据结构
# ============================================

@dataclass
class NodeInfo:
    """节点信息"""
    id: str
    name: str
    type: str  # file, class, function, module, package
    path: str
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    dependencies: Set[str] = field(default_factory=set)
    size: int = 0
    complexity: int = 0
    last_modified: Optional[datetime] = None

@dataclass
class EdgeInfo:
    """边信息"""
    source: str
    target: str
    type: str  # import, extends, implements, calls, uses, creates
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class GraphData:
    """图谱数据"""
    nodes: List[NodeInfo] = field(default_factory=list)
    edges: List[EdgeInfo] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

# ============================================
# 代码分析器
# ============================================

class ProjectAnalyzer:
    """项目分析器"""

    def __init__(self):
        self.file_handlers = {
            '.py': self.analyze_python,
            '.js': self.analyze_javascript,
            '.ts': self.analyze_typescript,
            '.java': self.analyze_java,
            '.go': self.analyze_go,
            '.rs': self.analyze_rust,
            '.cpp': self.analyze_cpp,
            '.c': self.analyze_c,
            '.cs': self.analyze_csharp,
            '.rb': self.analyze_ruby,
            '.php': self.analyze_php,
            '.swift': self.analyze_swift,
            '.kt': self.analyze_kotlin,
            '.scala': self.analyze_scala,
            '.vue': self.analyze_vue,
            '.jsx': self.analyze_react,
            '.tsx': self.analyze_react,
        }
        self.ignore_patterns = [
            '__pycache__', '.git', 'node_modules', 'venv', 'env',
            '.env', 'dist', 'build', 'target', '.idea', '.vscode',
            '*.pyc', '*.pyo', '*.pyd', '.DS_Store', 'Thumbs.db'
        ]

    async def analyze_project(self, project_path: str) -> GraphData:
        """分析整个项目"""
        graph_data = GraphData()
        project_path = Path(project_path)

        if not project_path.exists():
            raise ValueError(f"项目路径不存在: {project_path}")

        # 递归分析所有文件
        for file_path in self._get_project_files(project_path):
            try:
                node_info = await self.analyze_file(file_path, project_path)
                if node_info:
                    graph_data.nodes.append(node_info)
            except Exception as e:
                logger.error(f"分析文件失败 {file_path}: {e}")

        # 分析依赖关系
        graph_data.edges = await self._analyze_dependencies(graph_data.nodes)

        # 添加元数据
        graph_data.metadata = {
            "project_name": project_path.name,
            "project_path": str(project_path),
            "total_files": len(graph_data.nodes),
            "total_dependencies": len(graph_data.edges),
            "analysis_time": datetime.now().isoformat(),
            "language_stats": self._calculate_language_stats(graph_data.nodes)
        }

        return graph_data

    def _get_project_files(self, project_path: Path) -> List[Path]:
        """获取项目中的所有文件"""
        files = []

        for item in project_path.rglob('*'):
            # 跳过忽略的文件和目录
            if any(pattern in str(item) for pattern in self.ignore_patterns):
                continue

            if item.is_file():
                files.append(item)

        return files

    async def analyze_file(self, file_path: Path, project_root: Path) -> Optional[NodeInfo]:
        """分析单个文件"""
        suffix = file_path.suffix

        if suffix not in self.file_handlers:
            return None

        handler = self.file_handlers[suffix]
        relative_path = file_path.relative_to(project_root)

        node = NodeInfo(
            id=self._generate_node_id(str(relative_path)),
            name=file_path.stem,
            type="file",
            path=str(relative_path),
            size=file_path.stat().st_size,
            last_modified=datetime.fromtimestamp(file_path.stat().st_mtime)
        )

        try:
            # 调用对应的语言分析器
            analysis_result = await handler(file_path, node)
            return analysis_result
        except Exception as e:
            logger.error(f"分析文件 {file_path} 时出错: {e}")
            return node

    def _generate_node_id(self, path: str) -> str:
        """生成节点ID"""
        return hashlib.md5(path.encode()).hexdigest()[:12]

    async def analyze_python(self, file_path: Path, node: NodeInfo) -> NodeInfo:
        """分析Python文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content)

            # 提取导入
            imports = []
            for node_ast in ast.walk(tree):
                if isinstance(node_ast, ast.Import):
                    for alias in node_ast.names:
                        imports.append(alias.name)
                        node.dependencies.add(alias.name)
                elif isinstance(node_ast, ast.ImportFrom):
                    if node_ast.module:
                        imports.append(node_ast.module)
                        node.dependencies.add(node_ast.module)

            # 提取类和函数
            classes = []
            functions = []

            for node_ast in tree.body:
                if isinstance(node_ast, ast.ClassDef):
                    classes.append({
                        "name": node_ast.name,
                        "methods": [n.name for n in node_ast.body if isinstance(n, ast.FunctionDef)],
                        "docstring": ast.get_docstring(node_ast)
                    })
                elif isinstance(node_ast, ast.FunctionDef):
                    functions.append({
                        "name": node_ast.name,
                        "args": [arg.arg for arg in node_ast.args.args],
                        "docstring": ast.get_docstring(node_ast)
                    })

            # 计算复杂度
            node.complexity = len(classes) * 10 + len(functions) * 5 + len(imports)

            # 更新元数据
            node.metadata = {
                "language": "python",
                "imports": imports,
                "classes": classes,
                "functions": functions,
                "lines": len(content.splitlines())
            }

            # 生成描述
            node.description = f"Python模块，包含{len(classes)}个类，{len(functions)}个函数"

        except Exception as e:
            logger.error(f"Python分析失败: {e}")

        return node

    async def analyze_javascript(self, file_path: Path, node: NodeInfo) -> NodeInfo:
        """分析JavaScript文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 提取导入
            import_pattern = r'import\s+.*?\s+from\s+[\'"]([^\'"]+)[\'"]'
            require_pattern = r'require\([\'"]([^\'"]+)[\'"]\)'

            imports = re.findall(import_pattern, content) + re.findall(require_pattern, content)
            node.dependencies.update(imports)

            # 提取函数和类
            function_pattern = r'function\s+(\w+)\s*\('
            class_pattern = r'class\s+(\w+)'

            functions = re.findall(function_pattern, content)
            classes = re.findall(class_pattern, content)

            # 提取React组件
            component_pattern = r'(?:const|let|var)\s+(\w+)\s*=\s*\([^)]*\)\s*=>'
            components = re.findall(component_pattern, content)

            node.complexity = len(classes) * 10 + len(functions) * 5 + len(components) * 7

            node.metadata = {
                "language": "javascript",
                "imports": imports,
                "functions": functions,
                "classes": classes,
                "components": components,
                "lines": len(content.splitlines())
            }

            node.description = f"JavaScript模块，包含{len(classes)}个类，{len(functions)}个函数，{len(components)}个组件"

        except Exception as e:
            logger.error(f"JavaScript分析失败: {e}")

        return node

    async def analyze_typescript(self, file_path: Path, node: NodeInfo) -> NodeInfo:
        """分析TypeScript文件"""
        # 使用类似JavaScript的分析，但添加类型信息
        node = await self.analyze_javascript(file_path, node)
        node.metadata["language"] = "typescript"

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 提取接口
            interface_pattern = r'interface\s+(\w+)'
            interfaces = re.findall(interface_pattern, content)

            # 提取类型定义
            type_pattern = r'type\s+(\w+)\s*='
            types = re.findall(type_pattern, content)

            node.metadata["interfaces"] = interfaces
            node.metadata["types"] = types

            node.description = f"TypeScript模块，包含{len(interfaces)}个接口，{len(types)}个类型定义"

        except Exception as e:
            logger.error(f"TypeScript分析失败: {e}")

        return node

    async def analyze_java(self, file_path: Path, node: NodeInfo) -> NodeInfo:
        """分析Java文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 提取包名
            package_pattern = r'package\s+([\w.]+);'
            package = re.findall(package_pattern, content)

            # 提取导入
            import_pattern = r'import\s+([\w.]+);'
            imports = re.findall(import_pattern, content)
            node.dependencies.update(imports)

            # 提取类和接口
            class_pattern = r'(?:public\s+)?(?:abstract\s+)?class\s+(\w+)'
            interface_pattern = r'(?:public\s+)?interface\s+(\w+)'

            classes = re.findall(class_pattern, content)
            interfaces = re.findall(interface_pattern, content)

            node.metadata = {
                "language": "java",
                "package": package[0] if package else None,
                "imports": imports,
                "classes": classes,
                "interfaces": interfaces,
                "lines": len(content.splitlines())
            }

            node.description = f"Java模块，包含{len(classes)}个类，{len(interfaces)}个接口"

        except Exception as e:
            logger.error(f"Java分析失败: {e}")

        return node

    # 其他语言分析器...
    async def analyze_go(self, file_path: Path, node: NodeInfo) -> NodeInfo:
        node.metadata["language"] = "go"
        return node

    async def analyze_rust(self, file_path: Path, node: NodeInfo) -> NodeInfo:
        node.metadata["language"] = "rust"
        return node

    async def analyze_cpp(self, file_path: Path, node: NodeInfo) -> NodeInfo:
        node.metadata["language"] = "cpp"
        return node

    async def analyze_c(self, file_path: Path, node: NodeInfo) -> NodeInfo:
        node.metadata["language"] = "c"
        return node

    async def analyze_csharp(self, file_path: Path, node: NodeInfo) -> NodeInfo:
        node.metadata["language"] = "csharp"
        return node

    async def analyze_ruby(self, file_path: Path, node: NodeInfo) -> NodeInfo:
        node.metadata["language"] = "ruby"
        return node

    async def analyze_php(self, file_path: Path, node: NodeInfo) -> NodeInfo:
        node.metadata["language"] = "php"
        return node

    async def analyze_swift(self, file_path: Path, node: NodeInfo) -> NodeInfo:
        node.metadata["language"] = "swift"
        return node

    async def analyze_kotlin(self, file_path: Path, node: NodeInfo) -> NodeInfo:
        node.metadata["language"] = "kotlin"
        return node

    async def analyze_scala(self, file_path: Path, node: NodeInfo) -> NodeInfo:
        node.metadata["language"] = "scala"
        return node

    async def analyze_vue(self, file_path: Path, node: NodeInfo) -> NodeInfo:
        node.metadata["language"] = "vue"
        return node

    async def analyze_react(self, file_path: Path, node: NodeInfo) -> NodeInfo:
        node = await self.analyze_javascript(file_path, node)
        node.metadata["framework"] = "react"
        return node

    async def _analyze_dependencies(self, nodes: List[NodeInfo]) -> List[EdgeInfo]:
        """分析节点间的依赖关系"""
        edges = []
        node_map = {node.path: node for node in nodes}

        for node in nodes:
            for dep in node.dependencies:
                # 尝试解析依赖路径
                dep_path = self._resolve_dependency(dep, node.path, node_map)
                if dep_path and dep_path in node_map:
                    edge = EdgeInfo(
                        source=node.id,
                        target=node_map[dep_path].id,
                        type="imports",
                        metadata={"dependency": dep}
                    )
                    edges.append(edge)

        return edges

    def _resolve_dependency(self, dep: str, current_path: str, node_map: Dict[str, NodeInfo]) -> Optional[str]:
        """解析依赖路径"""
        # 相对路径导入
        if dep.startswith('.'):
            current_dir = Path(current_path).parent
            if dep.startswith('..'):
                # 父目录导入
                levels = dep.count('../')
                for _ in range(levels):
                    current_dir = current_dir.parent
                dep_name = dep.replace('../', '')
            else:
                # 当前目录导入
                dep_name = dep.replace('./', '').replace('.', '')

            possible_paths = [
                str(current_dir / f"{dep_name}.py"),
                str(current_dir / f"{dep_name}.js"),
                str(current_dir / f"{dep_name}.ts"),
                str(current_dir / dep_name / "__init__.py"),
                str(current_dir / dep_name / "index.js"),
                str(current_dir / dep_name / "index.ts"),
            ]

            for path in possible_paths:
                if path in node_map:
                    return path

        return None

    def _calculate_language_stats(self, nodes: List[NodeInfo]) -> Dict[str, int]:
        """计算语言统计"""
        stats = {}
        for node in nodes:
            lang = node.metadata.get("language", "unknown")
            stats[lang] = stats.get(lang, 0) + 1
        return stats

# ============================================
# 图谱生成器
# ============================================

class GraphGenerator:
    """图谱生成器"""

    def __init__(self):
        self.analyzer = ProjectAnalyzer()
        self.model_manager = get_model_manager() if HAS_AI else None
        self.redis_client = get_redis_client() if HAS_REDIS else None

    async def generate_graph(self, project_path: str, output_format: str = "json") -> Dict[str, Any]:
        """生成项目图谱"""
        logger.info(f"开始生成项目图谱: {project_path}")

        # 分析项目
        graph_data = await self.analyzer.analyze_project(project_path)

        # 使用AI增强节点描述
        graph_data = await self._enhance_with_ai(graph_data)

        # 应用布局算法
        graph_data = self._apply_layout(graph_data)

        # 保存到数据库
        await self._save_to_database(graph_data)

        # 缓存结果
        await self._cache_result(project_path, graph_data)

        # 根据格式返回
        if output_format == "json":
            return self._to_json(graph_data)
        elif output_format == "html":
            return self._to_html(graph_data)
        elif output_format == "networkx":
            return self._to_networkx(graph_data)
        else:
            return self._to_json(graph_data)

    async def _enhance_with_ai(self, graph_data: GraphData) -> GraphData:
        """使用AI增强图谱数据"""
        if not HAS_AI or not self.model_manager:
            # 如果没有AI模块，跳过增强
            return graph_data

        try:
            # 为每个节点生成更好的描述
            for node in graph_data.nodes[:10]:  # 限制数量避免过多API调用
                if not node.description or len(node.description) < 20:
                    prompt = f"""
                    为这个代码文件生成简短描述：
                    文件: {node.name}
                    路径: {node.path}
                    类型: {node.metadata.get('language', 'unknown')}
                    包含: {node.metadata.get('classes', [])} 类, {node.metadata.get('functions', [])} 函数

                    用一句话描述这个文件的主要功能。
                    """

                    response = await self.model_manager.generate(
                        prompt=prompt,
                        capability=ModelCapability.EXPLANATION,
                        max_tokens=50
                    )

                    if not response.error:
                        node.description = response.content.strip()

        except Exception as e:
            logger.error(f"AI增强失败: {e}")

        return graph_data

    def _apply_layout(self, graph_data: GraphData) -> GraphData:
        """应用布局算法"""
        # 创建NetworkX图
        G = nx.DiGraph()

        for node in graph_data.nodes:
            G.add_node(node.id, **{
                "label": node.name,
                "type": node.type,
                "size": node.size,
                "complexity": node.complexity
            })

        for edge in graph_data.edges:
            G.add_edge(edge.source, edge.target, **{
                "type": edge.type,
                "weight": edge.weight
            })

        # 计算布局
        if len(G.nodes) < 50:
            pos = nx.spring_layout(G, k=2, iterations=50)
        else:
            pos = nx.kamada_kawai_layout(G)

        # 更新节点位置
        for node in graph_data.nodes:
            if node.id in pos:
                node.metadata["x"] = float(pos[node.id][0]) * 1000
                node.metadata["y"] = float(pos[node.id][1]) * 1000

        return graph_data

    async def _save_to_database(self, graph_data: GraphData):
        """保存到数据库"""
        if not HAS_DB or not db_manager:
            # 如果没有数据库模块，跳过保存
            logger.info("数据库模块不可用，跳过保存")
            return

        try:
            with db_manager.get_session() as session:
                # 保存图谱
                project_graph = ProjectGraph(
                    name=graph_data.metadata.get("project_name", "Unknown"),
                    path=graph_data.metadata.get("project_path", ""),
                    node_count=len(graph_data.nodes),
                    edge_count=len(graph_data.edges),
                    metadata=json.dumps(graph_data.metadata)
                )
                session.add(project_graph)
                session.flush()

                # 保存节点
                for node in graph_data.nodes:
                    graph_node = GraphNode(
                        graph_id=project_graph.id,
                        node_id=node.id,
                        name=node.name,
                        type=node.type,
                        path=node.path,
                        description=node.description,
                        metadata=json.dumps(node.metadata)
                    )
                    session.add(graph_node)

                # 保存边
                for edge in graph_data.edges:
                    graph_edge = GraphEdge(
                        graph_id=project_graph.id,
                        source_id=edge.source,
                        target_id=edge.target,
                        edge_type=edge.type,
                        weight=edge.weight,
                        metadata=json.dumps(edge.metadata)
                    )
                    session.add(graph_edge)

                session.commit()
                logger.info(f"图谱已保存到数据库: {project_graph.id}")

        except Exception as e:
            logger.error(f"保存图谱失败: {e}")

    async def _cache_result(self, project_path: str, graph_data: GraphData):
        """缓存结果"""
        if not HAS_REDIS or not self.redis_client:
            # 如果没有Redis，跳过缓存
            return

        cache_key = f"graph:{hashlib.md5(project_path.encode()).hexdigest()}"
        cache_value = self._to_json(graph_data)

        await self.redis_client.setex(
            cache_key,
            3600,  # 1小时过期
            json.dumps(cache_value)
        )

    def _to_json(self, graph_data: GraphData) -> Dict[str, Any]:
        """转换为JSON格式"""
        return {
            "nodes": [
                {
                    "id": node.id,
                    "name": node.name,
                    "type": node.type,
                    "path": node.path,
                    "description": node.description,
                    "size": node.size,
                    "complexity": node.complexity,
                    "x": node.metadata.get("x", 0),
                    "y": node.metadata.get("y", 0),
                    "metadata": node.metadata
                }
                for node in graph_data.nodes
            ],
            "edges": [
                {
                    "source": edge.source,
                    "target": edge.target,
                    "type": edge.type,
                    "weight": edge.weight,
                    "metadata": edge.metadata
                }
                for edge in graph_data.edges
            ],
            "metadata": graph_data.metadata
        }

    def _to_html(self, graph_data: GraphData) -> str:
        """生成HTML可视化"""
        # 使用pyvis生成交互式HTML
        net = Network(height="100vh", width="100%", directed=True)

        # 设置物理引擎
        net.set_options("""
        {
            "physics": {
                "enabled": true,
                "barnesHut": {
                    "gravitationalConstant": -8000,
                    "centralGravity": 0.3,
                    "springLength": 95
                }
            },
            "interaction": {
                "hover": true,
                "tooltipDelay": 100
            }
        }
        """)

        # 添加节点
        for node in graph_data.nodes:
            color = self._get_node_color(node.type, node.metadata.get("language"))
            net.add_node(
                node.id,
                label=node.name,
                title=f"{node.description}\n路径: {node.path}",
                color=color,
                size=max(10, min(50, node.complexity))
            )

        # 添加边
        for edge in graph_data.edges:
            net.add_edge(edge.source, edge.target, title=edge.type)

        # 生成HTML
        html = net.generate_html()
        return html

    def _to_networkx(self, graph_data: GraphData) -> nx.DiGraph:
        """转换为NetworkX图"""
        G = nx.DiGraph()

        for node in graph_data.nodes:
            G.add_node(node.id, **node.__dict__)

        for edge in graph_data.edges:
            G.add_edge(edge.source, edge.target, **edge.__dict__)

        return G

    def _get_node_color(self, node_type: str, language: Optional[str]) -> str:
        """获取节点颜色"""
        # 根据语言设置颜色
        language_colors = {
            "python": "#3776ab",
            "javascript": "#f7df1e",
            "typescript": "#3178c6",
            "java": "#007396",
            "go": "#00add8",
            "rust": "#dea584",
            "cpp": "#00599c",
            "c": "#a8b9cc",
            "csharp": "#239120",
            "ruby": "#cc342d",
            "php": "#777bb4",
            "swift": "#fa7343",
            "kotlin": "#7f52ff",
            "scala": "#dc322f",
            "vue": "#4fc08d",
            "react": "#61dafb"
        }

        return language_colors.get(language, "#808080")

# ============================================
# API接口
# ============================================

class ProjectGraphAPI:
    """项目图谱API"""

    def __init__(self):
        self.generator = GraphGenerator()

    async def create_graph(self, project_path: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """创建项目图谱"""
        options = options or {}
        output_format = options.get("format", "json")

        result = await self.generator.generate_graph(project_path, output_format)

        return {
            "status": "success",
            "data": result,
            "message": "图谱生成成功"
        }

    async def update_graph(self, graph_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """更新图谱"""
        # 实现图谱更新逻辑
        pass

    async def get_graph(self, graph_id: str) -> Dict[str, Any]:
        """获取图谱"""
        if not HAS_DB or not db_manager:
            return {"status": "error", "message": "数据库不可用"}

        with db_manager.get_session() as session:
            graph = session.query(ProjectGraph).filter_by(id=graph_id).first()
            if not graph:
                return {"status": "error", "message": "图谱不存在"}

            nodes = session.query(GraphNode).filter_by(graph_id=graph_id).all()
            edges = session.query(GraphEdge).filter_by(graph_id=graph_id).all()

            return {
                "status": "success",
                "data": {
                    "graph": graph.to_dict(),
                    "nodes": [n.to_dict() for n in nodes],
                    "edges": [e.to_dict() for e in edges]
                }
            }

    async def list_graphs(self) -> Dict[str, Any]:
        """列出所有图谱"""
        if not HAS_DB or not db_manager:
            return {"status": "success", "data": []}

        with db_manager.get_session() as session:
            graphs = session.query(ProjectGraph).all()

            return {
                "status": "success",
                "data": [g.to_dict() for g in graphs]
            }

# ============================================
# 单例实例
# ============================================

_graph_api_instance: Optional[ProjectGraphAPI] = None

def get_graph_api() -> ProjectGraphAPI:
    """获取图谱API单例"""
    global _graph_api_instance
    if _graph_api_instance is None:
        _graph_api_instance = ProjectGraphAPI()
    return _graph_api_instance
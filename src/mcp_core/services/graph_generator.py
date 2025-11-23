"""
项目图谱生成器 - 智能代码结构可视化
将项目代码转化为可视化知识图谱，让人和AI都能更好理解项目
"""

import os
import json
import hashlib
import ast
import networkx as nx
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass, asdict
import numpy as np
from sqlalchemy import create_engine, select, and_, or_, desc, func
from sqlalchemy.orm import Session, sessionmaker

from ..models.base import Base
from ..common.config import get_settings
from ..common.logger import get_logger
from ..code_analyzer import PythonCodeAnalyzer, CodeEntity, CodeRelation
from ..java_analyzer import JavaCodeAnalyzer
from ..multi_lang_analyzer import MultiLanguageAnalyzer
from ..services.embedding_service import get_embedding_service
from ..services.redis_client import get_redis_client

logger = get_logger(__name__)

# ============================================
# 数据模型
# ============================================

@dataclass
class GraphNode:
    """图谱节点"""
    node_id: str
    node_type: str  # module, class, function, variable, data, pattern
    node_name: str
    qualified_name: str
    file_path: str
    properties: Dict[str, Any]
    metrics: Dict[str, float]  # complexity, importance, stability
    position: Tuple[float, float, float] = (0, 0, 0)  # x, y, z
    cluster_id: Optional[str] = None
    color: str = "#4A90E2"
    size: float = 1.0

@dataclass
class GraphEdge:
    """图谱边"""
    edge_id: str
    source_id: str
    target_id: str
    edge_type: str  # calls, imports, inherits, depends, contains, dataflow
    weight: float = 1.0
    properties: Dict[str, Any] = None
    style: str = "solid"
    color: str = "#999999"

@dataclass
class ProjectGraph:
    """项目知识图谱"""
    project_id: str
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    clusters: List[Dict[str, Any]]
    layers: List[Dict[str, Any]]
    statistics: Dict[str, Any]
    metadata: Dict[str, Any]

# ============================================
# 项目图谱生成器
# ============================================

class ProjectGraphGenerator:
    """项目图谱生成器 - 让人和AI都懂项目"""

    def __init__(self):
        """初始化图谱生成器"""
        settings = get_settings()
        self.db_engine = create_engine(settings.database.url)
        self.SessionLocal = sessionmaker(bind=self.db_engine)

        # 嵌入服务
        self.embedding_service = get_embedding_service()

        # Redis缓存
        self.redis_client = get_redis_client()

        # NetworkX图
        self.nx_graph = None

        # 分析器
        self.analyzers = {
            ".py": PythonCodeAnalyzer,
            ".java": JavaCodeAnalyzer,
            # 可扩展更多语言
        }

        # 配置参数
        self.max_depth = 10  # 最大分析深度
        self.min_importance = 0.1  # 最小重要性阈值
        self.clustering_threshold = 0.7  # 聚类阈值

        logger.info("项目图谱生成器初始化完成")

    # ============================================
    # 核心功能
    # ============================================

    def generate_graph(
        self,
        project_path: str,
        project_id: Optional[str] = None
    ) -> Tuple[ProjectGraph, Dict[str, Any]]:
        """
        生成项目知识图谱

        Args:
            project_path: 项目路径
            project_id: 项目ID

        Returns:
            (项目图谱, 可视化数据)
        """
        try:
            logger.info(f"开始生成项目图谱: {project_path}")

            # 1. 初始化项目
            if not project_id:
                project_id = self.generate_project_id(project_path)

            self.nx_graph = nx.DiGraph()

            # 2. 代码结构分析
            logger.info("分析代码结构...")
            entities, relations = self.analyze_codebase(project_path)
            logger.info(f"发现 {len(entities)} 个实体, {len(relations)} 个关系")

            # 3. 构建基础图谱
            logger.info("构建基础图谱...")
            graph_nodes = self.build_nodes(entities, project_id)
            graph_edges = self.build_edges(relations, entities, project_id)

            # 4. 增强语义信息
            logger.info("增强语义信息...")
            self.enhance_with_semantics(graph_nodes)

            # 5. 计算重要性指标
            logger.info("计算重要性指标...")
            self.calculate_importance_metrics(graph_nodes, graph_edges)

            # 6. 识别架构模式
            logger.info("识别架构模式...")
            patterns = self.identify_architectural_patterns(graph_nodes, graph_edges)

            # 7. 聚类分析
            logger.info("进行聚类分析...")
            clusters = self.perform_clustering(graph_nodes, graph_edges)

            # 8. 分层布局
            logger.info("计算分层布局...")
            layers = self.extract_layers(graph_nodes, graph_edges)

            # 9. 生成可视化布局
            logger.info("生成可视化布局...")
            self.calculate_layout(graph_nodes, graph_edges, clusters, layers)

            # 10. 统计分析
            statistics = self.generate_statistics(graph_nodes, graph_edges)

            # 11. 存储到数据库
            logger.info("存储图谱数据...")
            self.store_graph(project_id, graph_nodes, graph_edges)

            # 12. 创建图谱对象
            graph = ProjectGraph(
                project_id=project_id,
                nodes=graph_nodes,
                edges=graph_edges,
                clusters=clusters,
                layers=layers,
                statistics=statistics,
                metadata={
                    "project_path": project_path,
                    "generated_at": datetime.now().isoformat(),
                    "patterns": patterns
                }
            )

            # 13. 生成可视化数据
            visualization_data = self.generate_visualization(graph)

            logger.info(f"图谱生成完成: {len(graph_nodes)} 节点, {len(graph_edges)} 边")

            return graph, visualization_data

        except Exception as e:
            logger.error(f"图谱生成失败: {e}")
            raise

    def analyze_codebase(self, project_path: str) -> Tuple[List[CodeEntity], List[CodeRelation]]:
        """分析代码库"""
        all_entities = []
        all_relations = []

        # 遍历项目文件
        for root, dirs, files in os.walk(project_path):
            # 跳过特定目录
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__' and d != 'node_modules']

            for file in files:
                file_path = os.path.join(root, file)
                ext = os.path.splitext(file)[1]

                if ext in self.analyzers:
                    try:
                        # 读取文件内容
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()

                        # 选择合适的分析器
                        analyzer_class = self.analyzers[ext]
                        analyzer = analyzer_class(file_path, project_path)

                        # 分析代码
                        entities, relations = analyzer.analyze(content)

                        all_entities.extend(entities)
                        all_relations.extend(relations)

                    except Exception as e:
                        logger.warning(f"分析文件失败 {file_path}: {e}")

        return all_entities, all_relations

    def build_nodes(self, entities: List[CodeEntity], project_id: str) -> List[GraphNode]:
        """构建图谱节点"""
        nodes = []

        for entity in entities:
            node = GraphNode(
                node_id=entity.id,
                node_type=entity.type,
                node_name=entity.name,
                qualified_name=entity.qualified_name,
                file_path=entity.file_path,
                properties={
                    "line_start": entity.line_number,
                    "line_end": entity.end_line,
                    "signature": entity.signature,
                    "docstring": entity.docstring,
                    "parent_id": entity.parent_id,
                    **entity.metadata
                },
                metrics={
                    "complexity": 0.0,
                    "importance": 0.0,
                    "stability": 1.0,
                    "quality": 0.0
                },
                color=self.get_node_color(entity.type),
                size=self.get_node_size(entity.type)
            )

            nodes.append(node)

            # 添加到NetworkX图
            self.nx_graph.add_node(
                entity.id,
                **asdict(node)
            )

        return nodes

    def build_edges(
        self,
        relations: List[CodeRelation],
        entities: List[CodeEntity],
        project_id: str
    ) -> List[GraphEdge]:
        """构建图谱边"""
        edges = []
        entity_map = {e.id: e for e in entities}

        for relation in relations:
            # 验证源和目标节点存在
            if relation.source_id not in entity_map:
                # 尝试通过名称查找
                source_entity = self.find_entity_by_name(relation.source_id, entities)
                if not source_entity:
                    continue
                source_id = source_entity.id
            else:
                source_id = relation.source_id

            if relation.target_id not in entity_map:
                target_entity = self.find_entity_by_name(relation.target_id, entities)
                if not target_entity:
                    continue
                target_id = target_entity.id
            else:
                target_id = relation.target_id

            edge = GraphEdge(
                edge_id=self.generate_edge_id(source_id, target_id, relation.relation_type),
                source_id=source_id,
                target_id=target_id,
                edge_type=relation.relation_type,
                weight=self.calculate_edge_weight(relation),
                properties=relation.metadata,
                style=self.get_edge_style(relation.relation_type),
                color=self.get_edge_color(relation.relation_type)
            )

            edges.append(edge)

            # 添加到NetworkX图
            self.nx_graph.add_edge(
                source_id,
                target_id,
                **asdict(edge)
            )

        return edges

    # ============================================
    # 增强功能
    # ============================================

    def enhance_with_semantics(self, nodes: List[GraphNode]) -> None:
        """增强语义信息"""
        for node in nodes:
            # 生成语义嵌入
            text = f"{node.node_name} {node.properties.get('docstring', '')}"
            embedding = self.embedding_service.encode_single(text)

            # 存储嵌入(简化为前10维)
            node.properties["embedding"] = embedding[:10].tolist()

            # 提取关键词
            node.properties["keywords"] = self.extract_keywords(text)

            # 分析代码复杂度
            if node.properties.get("signature"):
                node.metrics["complexity"] = self.calculate_code_complexity(
                    node.properties["signature"]
                )

    def calculate_importance_metrics(
        self,
        nodes: List[GraphNode],
        edges: List[GraphEdge]
    ) -> None:
        """计算重要性指标"""
        # 使用PageRank算法
        if self.nx_graph.number_of_nodes() > 0:
            try:
                pagerank = nx.pagerank(self.nx_graph, weight='weight')

                for node in nodes:
                    if node.node_id in pagerank:
                        node.metrics["importance"] = pagerank[node.node_id]

                        # 更新节点大小
                        node.size = 1 + node.metrics["importance"] * 5

            except Exception as e:
                logger.warning(f"PageRank计算失败: {e}")

        # 计算度中心性
        in_degree = dict(self.nx_graph.in_degree())
        out_degree = dict(self.nx_graph.out_degree())

        for node in nodes:
            node_id = node.node_id
            node.properties["in_degree"] = in_degree.get(node_id, 0)
            node.properties["out_degree"] = out_degree.get(node_id, 0)

            # 稳定性：入度高、出度低的节点更稳定
            if node.properties["out_degree"] > 0:
                node.metrics["stability"] = node.properties["in_degree"] / node.properties["out_degree"]
            else:
                node.metrics["stability"] = float(node.properties["in_degree"])

    def identify_architectural_patterns(
        self,
        nodes: List[GraphNode],
        edges: List[GraphEdge]
    ) -> List[Dict[str, Any]]:
        """识别架构模式"""
        patterns = []

        # 1. 识别MVC模式
        mvc_pattern = self.detect_mvc_pattern(nodes)
        if mvc_pattern:
            patterns.append(mvc_pattern)

        # 2. 识别分层架构
        layered_pattern = self.detect_layered_architecture(nodes)
        if layered_pattern:
            patterns.append(layered_pattern)

        # 3. 识别微服务
        microservice_pattern = self.detect_microservices(nodes, edges)
        if microservice_pattern:
            patterns.append(microservice_pattern)

        # 4. 识别设计模式
        design_patterns = self.detect_design_patterns(nodes, edges)
        patterns.extend(design_patterns)

        return patterns

    def perform_clustering(
        self,
        nodes: List[GraphNode],
        edges: List[GraphEdge]
    ) -> List[Dict[str, Any]]:
        """聚类分析"""
        clusters = []

        try:
            # 使用Louvain算法进行社区发现
            if self.nx_graph.number_of_nodes() > 0:
                import community
                partition = community.best_partition(self.nx_graph.to_undirected())

                # 整理聚类结果
                cluster_map = {}
                for node_id, cluster_id in partition.items():
                    if cluster_id not in cluster_map:
                        cluster_map[cluster_id] = []
                    cluster_map[cluster_id].append(node_id)

                # 为每个聚类生成信息
                for cluster_id, node_ids in cluster_map.items():
                    cluster_nodes = [n for n in nodes if n.node_id in node_ids]

                    if cluster_nodes:
                        cluster = {
                            "cluster_id": f"cluster_{cluster_id}",
                            "nodes": node_ids,
                            "size": len(node_ids),
                            "name": self.generate_cluster_name(cluster_nodes),
                            "dominant_type": self.get_dominant_type(cluster_nodes),
                            "cohesion": self.calculate_cluster_cohesion(node_ids, edges)
                        }
                        clusters.append(cluster)

                        # 更新节点的聚类ID
                        for node in cluster_nodes:
                            node.cluster_id = cluster["cluster_id"]

        except ImportError:
            logger.warning("community库未安装,跳过聚类分析")
        except Exception as e:
            logger.warning(f"聚类分析失败: {e}")

        return clusters

    def extract_layers(
        self,
        nodes: List[GraphNode],
        edges: List[GraphEdge]
    ) -> List[Dict[str, Any]]:
        """提取分层结构"""
        layers = []

        # 基于文件路径和模块结构分层
        layer_map = {}

        for node in nodes:
            # 根据路径深度确定层级
            path_parts = node.file_path.split(os.sep)
            depth = len(path_parts) - 1

            # 根据节点类型调整层级
            if node.node_type == "module":
                layer = 0
            elif node.node_type == "class":
                layer = 1
            elif node.node_type in ["function", "method"]:
                layer = 2
            else:
                layer = 3

            layer = min(layer + depth, self.max_depth)

            if layer not in layer_map:
                layer_map[layer] = []
            layer_map[layer].append(node.node_id)

            # 更新节点层级
            node.properties["layer"] = layer

        # 生成层级信息
        for layer_idx, node_ids in sorted(layer_map.items()):
            layer = {
                "layer_id": f"layer_{layer_idx}",
                "level": layer_idx,
                "nodes": node_ids,
                "name": self.get_layer_name(layer_idx),
                "node_count": len(node_ids)
            }
            layers.append(layer)

        return layers

    def calculate_layout(
        self,
        nodes: List[GraphNode],
        edges: List[GraphEdge],
        clusters: List[Dict[str, Any]],
        layers: List[Dict[str, Any]]
    ) -> None:
        """计算可视化布局"""
        if self.nx_graph.number_of_nodes() == 0:
            return

        # 使用spring layout作为基础
        pos = nx.spring_layout(
            self.nx_graph,
            k=2,
            iterations=50,
            weight='weight',
            scale=100
        )

        # 应用层级约束
        layer_y_positions = {}
        for i, layer in enumerate(layers):
            layer_y_positions[layer["level"]] = i * 50

        # 更新节点位置
        for node in nodes:
            node_id = node.node_id
            if node_id in pos:
                x, y = pos[node_id]
                layer = node.properties.get("layer", 0)
                z = layer * 10  # Z轴表示层级

                # 应用层级Y坐标
                if layer in layer_y_positions:
                    y = layer_y_positions[layer] + y * 10

                node.position = (x * 100, y, z)

    # ============================================
    # 可视化生成
    # ============================================

    def generate_visualization(self, graph: ProjectGraph) -> Dict[str, Any]:
        """生成可视化数据"""
        # 准备节点数据
        nodes_data = []
        for node in graph.nodes:
            nodes_data.append({
                "id": node.node_id,
                "label": node.node_name,
                "type": node.node_type,
                "x": node.position[0],
                "y": node.position[1],
                "z": node.position[2],
                "size": node.size,
                "color": node.color,
                "cluster": node.cluster_id,
                "properties": node.properties,
                "metrics": node.metrics
            })

        # 准备边数据
        edges_data = []
        for edge in graph.edges:
            edges_data.append({
                "id": edge.edge_id,
                "source": edge.source_id,
                "target": edge.target_id,
                "type": edge.edge_type,
                "weight": edge.weight,
                "style": edge.style,
                "color": edge.color,
                "properties": edge.properties
            })

        # 生成热力图数据
        heatmap_data = self.generate_heatmap(graph)

        # 生成导航树
        navigation_tree = self.create_navigation_tree(graph)

        return {
            "nodes": nodes_data,
            "edges": edges_data,
            "clusters": graph.clusters,
            "layers": graph.layers,
            "heatmap": heatmap_data,
            "navigation": navigation_tree,
            "statistics": graph.statistics,
            "metadata": graph.metadata
        }

    def generate_heatmap(self, graph: ProjectGraph) -> Dict[str, Any]:
        """生成复杂度热力图"""
        heatmap_data = {
            "complexity": [],
            "changes": [],
            "bugs": []
        }

        for node in graph.nodes:
            if node.metrics["complexity"] > 0:
                heatmap_data["complexity"].append({
                    "id": node.node_id,
                    "value": node.metrics["complexity"],
                    "x": node.position[0],
                    "y": node.position[1]
                })

        return heatmap_data

    def create_navigation_tree(self, graph: ProjectGraph) -> Dict[str, Any]:
        """创建导航树"""
        tree = {
            "name": "root",
            "children": []
        }

        # 按文件路径组织树结构
        path_tree = {}
        for node in graph.nodes:
            parts = node.file_path.split(os.sep)

            current = path_tree
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]

            # 添加节点
            file_name = parts[-1] if parts else node.node_name
            if file_name not in current:
                current[file_name] = []
            current[file_name].append({
                "id": node.node_id,
                "name": node.node_name,
                "type": node.node_type
            })

        # 转换为树形结构
        def build_tree(data, name="root"):
            children = []
            for key, value in data.items():
                if isinstance(value, dict):
                    children.append(build_tree(value, key))
                else:
                    children.append({
                        "name": key,
                        "nodes": value
                    })
            return {"name": name, "children": children}

        tree = build_tree(path_tree)
        return tree

    # ============================================
    # 存储功能
    # ============================================

    def store_graph(
        self,
        project_id: str,
        nodes: List[GraphNode],
        edges: List[GraphEdge]
    ) -> None:
        """存储图谱到数据库"""
        with self.SessionLocal() as session:
            # 存储节点
            for node in nodes:
                embedding_json = json.dumps(node.properties.get("embedding", []))

                session.execute(
                    """
                    INSERT INTO graph_nodes (
                        node_id, project_id, node_type, node_name,
                        node_path, qualified_name, file_path,
                        line_start, line_end,
                        properties, docstring, signature,
                        complexity_score, importance_score, stability_score,
                        in_degree, out_degree, centrality,
                        layout_x, layout_y, layout_z,
                        cluster_id, color, size,
                        embedding
                    ) VALUES (
                        :node_id, :project_id, :node_type, :node_name,
                        :node_path, :qualified_name, :file_path,
                        :line_start, :line_end,
                        :properties, :docstring, :signature,
                        :complexity, :importance, :stability,
                        :in_degree, :out_degree, :centrality,
                        :x, :y, :z,
                        :cluster_id, :color, :size,
                        :embedding
                    )
                    ON DUPLICATE KEY UPDATE
                        properties = :properties,
                        complexity_score = :complexity,
                        importance_score = :importance,
                        stability_score = :stability,
                        layout_x = :x, layout_y = :y, layout_z = :z,
                        cluster_id = :cluster_id,
                        updated_at = NOW()
                    """,
                    {
                        "node_id": node.node_id,
                        "project_id": project_id,
                        "node_type": node.node_type,
                        "node_name": node.node_name,
                        "node_path": node.file_path,
                        "qualified_name": node.qualified_name,
                        "file_path": node.file_path,
                        "line_start": node.properties.get("line_start"),
                        "line_end": node.properties.get("line_end"),
                        "properties": json.dumps(node.properties),
                        "docstring": node.properties.get("docstring"),
                        "signature": node.properties.get("signature"),
                        "complexity": node.metrics["complexity"],
                        "importance": node.metrics["importance"],
                        "stability": node.metrics["stability"],
                        "in_degree": node.properties.get("in_degree", 0),
                        "out_degree": node.properties.get("out_degree", 0),
                        "centrality": node.metrics["importance"],
                        "x": node.position[0],
                        "y": node.position[1],
                        "z": node.position[2],
                        "cluster_id": node.cluster_id,
                        "color": node.color,
                        "size": node.size,
                        "embedding": embedding_json
                    }
                )

            # 存储边
            for edge in edges:
                session.execute(
                    """
                    INSERT INTO graph_edges (
                        edge_id, project_id,
                        source_node_id, target_node_id, edge_type,
                        weight, confidence,
                        metadata, edge_style, edge_color
                    ) VALUES (
                        :edge_id, :project_id,
                        :source, :target, :edge_type,
                        :weight, :confidence,
                        :metadata, :style, :color
                    )
                    ON DUPLICATE KEY UPDATE
                        weight = :weight,
                        metadata = :metadata,
                        updated_at = NOW()
                    """,
                    {
                        "edge_id": edge.edge_id,
                        "project_id": project_id,
                        "source": edge.source_id,
                        "target": edge.target_id,
                        "edge_type": edge.edge_type,
                        "weight": edge.weight,
                        "confidence": 1.0,
                        "metadata": json.dumps(edge.properties or {}),
                        "style": edge.style,
                        "color": edge.color
                    }
                )

            session.commit()
            logger.info(f"存储图谱: {len(nodes)} 节点, {len(edges)} 边")

    # ============================================
    # 辅助功能
    # ============================================

    def generate_project_id(self, project_path: str) -> str:
        """生成项目ID"""
        project_name = os.path.basename(project_path)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        hash_suffix = hashlib.md5(project_path.encode()).hexdigest()[:8]
        return f"proj_{project_name}_{timestamp}_{hash_suffix}"

    def generate_edge_id(self, source: str, target: str, edge_type: str) -> str:
        """生成边ID"""
        content = f"{source}_{target}_{edge_type}"
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def get_node_color(self, node_type: str) -> str:
        """获取节点颜色"""
        colors = {
            "module": "#FF6B6B",
            "class": "#4ECDC4",
            "function": "#45B7D1",
            "method": "#96CEB4",
            "variable": "#FFEAA7",
            "import": "#DDA0DD"
        }
        return colors.get(node_type, "#95A5A6")

    def get_node_size(self, node_type: str) -> float:
        """获取节点大小"""
        sizes = {
            "module": 3.0,
            "class": 2.5,
            "function": 2.0,
            "method": 1.8,
            "variable": 1.0
        }
        return sizes.get(node_type, 1.0)

    def get_edge_style(self, edge_type: str) -> str:
        """获取边样式"""
        styles = {
            "inherits": "dashed",
            "implements": "dotted",
            "calls": "solid",
            "imports": "solid",
            "contains": "solid"
        }
        return styles.get(edge_type, "solid")

    def get_edge_color(self, edge_type: str) -> str:
        """获取边颜色"""
        colors = {
            "inherits": "#E74C3C",
            "implements": "#3498DB",
            "calls": "#2ECC71",
            "imports": "#F39C12",
            "contains": "#95A5A6"
        }
        return colors.get(edge_type, "#BDC3C7")

    def calculate_edge_weight(self, relation: CodeRelation) -> float:
        """计算边权重"""
        # 基于关系类型的基础权重
        base_weights = {
            "inherits": 3.0,
            "implements": 2.5,
            "calls": 1.5,
            "imports": 1.0,
            "contains": 2.0,
            "uses": 1.0
        }
        return base_weights.get(relation.relation_type, 1.0)

    def find_entity_by_name(self, name: str, entities: List[CodeEntity]) -> Optional[CodeEntity]:
        """通过名称查找实体"""
        for entity in entities:
            if entity.name == name or entity.qualified_name == name:
                return entity
        return None

    def extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        import re
        words = re.findall(r'\b\w+\b', text.lower())
        stopwords = {'the', 'is', 'at', 'which', 'on', 'and', 'a', 'an', 'as', 'are', 'was', 'were', 'in', 'of', 'to'}
        keywords = [w for w in words if w not in stopwords and len(w) > 2]
        return list(set(keywords))[:10]

    def calculate_code_complexity(self, code: str) -> float:
        """计算代码复杂度"""
        # 简化的复杂度计算
        complexity = 1.0

        # 条件语句
        complexity += code.count('if ') * 0.5
        complexity += code.count('elif ') * 0.3
        complexity += code.count('else:') * 0.2

        # 循环
        complexity += code.count('for ') * 0.8
        complexity += code.count('while ') * 0.8

        # 异常处理
        complexity += code.count('try:') * 0.3
        complexity += code.count('except ') * 0.3

        return min(complexity, 10.0)

    def detect_mvc_pattern(self, nodes: List[GraphNode]) -> Optional[Dict[str, Any]]:
        """检测MVC模式"""
        # 查找Model、View、Controller相关节点
        models = [n for n in nodes if 'model' in n.node_name.lower()]
        views = [n for n in nodes if 'view' in n.node_name.lower()]
        controllers = [n for n in nodes if 'controller' in n.node_name.lower()]

        if models and views and controllers:
            return {
                "pattern": "MVC",
                "description": "Model-View-Controller架构",
                "components": {
                    "models": [m.node_id for m in models],
                    "views": [v.node_id for v in views],
                    "controllers": [c.node_id for c in controllers]
                }
            }
        return None

    def detect_layered_architecture(self, nodes: List[GraphNode]) -> Optional[Dict[str, Any]]:
        """检测分层架构"""
        # 查找典型的分层名称
        layers_found = {}
        layer_keywords = {
            "presentation": ["ui", "view", "frontend", "web"],
            "business": ["service", "business", "logic", "domain"],
            "data": ["repository", "dao", "database", "model"]
        }

        for layer_name, keywords in layer_keywords.items():
            layer_nodes = []
            for node in nodes:
                node_lower = node.node_name.lower()
                if any(kw in node_lower for kw in keywords):
                    layer_nodes.append(node.node_id)
            if layer_nodes:
                layers_found[layer_name] = layer_nodes

        if len(layers_found) >= 2:
            return {
                "pattern": "Layered Architecture",
                "description": "分层架构模式",
                "layers": layers_found
            }
        return None

    def detect_microservices(
        self,
        nodes: List[GraphNode],
        edges: List[GraphEdge]
    ) -> Optional[Dict[str, Any]]:
        """检测微服务模式"""
        # 查找服务相关节点
        services = [n for n in nodes if 'service' in n.node_name.lower()]

        if len(services) >= 3:
            # 检查服务间的低耦合
            service_ids = {s.node_id for s in services}
            inter_service_edges = [
                e for e in edges
                if e.source_id in service_ids and e.target_id in service_ids
            ]

            # 如果服务间连接较少，可能是微服务
            if len(inter_service_edges) < len(services) * 2:
                return {
                    "pattern": "Microservices",
                    "description": "微服务架构",
                    "services": [s.node_id for s in services],
                    "coupling": "low"
                }
        return None

    def detect_design_patterns(
        self,
        nodes: List[GraphNode],
        edges: List[GraphEdge]
    ) -> List[Dict[str, Any]]:
        """检测设计模式"""
        patterns = []

        # Singleton模式
        singletons = [n for n in nodes if 'singleton' in n.node_name.lower() or 'instance' in n.properties.get('signature', '').lower()]
        if singletons:
            patterns.append({
                "pattern": "Singleton",
                "nodes": [s.node_id for s in singletons]
            })

        # Factory模式
        factories = [n for n in nodes if 'factory' in n.node_name.lower()]
        if factories:
            patterns.append({
                "pattern": "Factory",
                "nodes": [f.node_id for f in factories]
            })

        # Observer模式
        observers = [n for n in nodes if 'observer' in n.node_name.lower() or 'listener' in n.node_name.lower()]
        if observers:
            patterns.append({
                "pattern": "Observer",
                "nodes": [o.node_id for o in observers]
            })

        return patterns

    def generate_cluster_name(self, nodes: List[GraphNode]) -> str:
        """生成聚类名称"""
        # 基于最常见的节点类型或名称模式
        type_counts = {}
        for node in nodes:
            type_counts[node.node_type] = type_counts.get(node.node_type, 0) + 1

        if type_counts:
            dominant_type = max(type_counts, key=type_counts.get)
            return f"{dominant_type}_cluster"
        return "unnamed_cluster"

    def get_dominant_type(self, nodes: List[GraphNode]) -> str:
        """获取主导类型"""
        type_counts = {}
        for node in nodes:
            type_counts[node.node_type] = type_counts.get(node.node_type, 0) + 1

        if type_counts:
            return max(type_counts, key=type_counts.get)
        return "mixed"

    def calculate_cluster_cohesion(
        self,
        node_ids: List[str],
        edges: List[GraphEdge]
    ) -> float:
        """计算聚类内聚度"""
        internal_edges = 0
        external_edges = 0

        for edge in edges:
            source_in = edge.source_id in node_ids
            target_in = edge.target_id in node_ids

            if source_in and target_in:
                internal_edges += 1
            elif source_in or target_in:
                external_edges += 1

        total = internal_edges + external_edges
        if total == 0:
            return 0.0

        return internal_edges / total

    def get_layer_name(self, layer_idx: int) -> str:
        """获取层级名称"""
        layer_names = [
            "Infrastructure",
            "Core",
            "Domain",
            "Application",
            "Interface"
        ]
        if layer_idx < len(layer_names):
            return layer_names[layer_idx]
        return f"Layer {layer_idx}"

    def generate_statistics(
        self,
        nodes: List[GraphNode],
        edges: List[GraphEdge]
    ) -> Dict[str, Any]:
        """生成统计信息"""
        # 节点统计
        node_types = {}
        for node in nodes:
            node_types[node.node_type] = node_types.get(node.node_type, 0) + 1

        # 边统计
        edge_types = {}
        for edge in edges:
            edge_types[edge.edge_type] = edge_types.get(edge.edge_type, 0) + 1

        # 复杂度统计
        complexities = [n.metrics["complexity"] for n in nodes]
        avg_complexity = np.mean(complexities) if complexities else 0

        # 重要性统计
        importances = [n.metrics["importance"] for n in nodes]
        avg_importance = np.mean(importances) if importances else 0

        return {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "node_types": node_types,
            "edge_types": edge_types,
            "avg_complexity": float(avg_complexity),
            "avg_importance": float(avg_importance),
            "max_in_degree": max([n.properties.get("in_degree", 0) for n in nodes]) if nodes else 0,
            "max_out_degree": max([n.properties.get("out_degree", 0) for n in nodes]) if nodes else 0
        }


# ============================================
# 单例模式
# ============================================

_graph_generator_instance: Optional[ProjectGraphGenerator] = None

def get_graph_generator() -> ProjectGraphGenerator:
    """获取图谱生成器单例"""
    global _graph_generator_instance
    if _graph_generator_instance is None:
        _graph_generator_instance = ProjectGraphGenerator()
    return _graph_generator_instance
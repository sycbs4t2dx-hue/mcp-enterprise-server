"""
项目记忆系统 - 自动保存和恢复项目知识
通过图谱快照实现项目的"时光机"功能
"""

import os
import json
import hashlib
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass, field
import pickle
import sqlite3
import difflib

from src.mcp_core.services.project_graph_generator import (
    ProjectAnalyzer, GraphGenerator, GraphData
)
from src.mcp_core.common.logger import get_logger

logger = get_logger(__name__)

# ============================================
# 数据结构
# ============================================

@dataclass
class MemorySnapshot:
    """记忆快照"""
    id: str
    timestamp: datetime
    graph_data: GraphData
    metadata: Dict[str, Any]
    context: Dict[str, Any] = field(default_factory=dict)
    insights: List[str] = field(default_factory=list)
    hash: str = ""

    def __post_init__(self):
        if not self.hash:
            self.hash = self.calculate_hash()

    def calculate_hash(self) -> str:
        """计算图谱哈希值"""
        data = f"{len(self.graph_data.nodes)}:{len(self.graph_data.edges)}"
        return hashlib.md5(data.encode()).hexdigest()

@dataclass
class MemoryQuery:
    """记忆查询"""
    query_type: str  # 'similarity', 'time_range', 'pattern', 'file_history'
    parameters: Dict[str, Any]
    context: Optional[Dict[str, Any]] = None

@dataclass
class MemoryRecoveryResult:
    """记忆恢复结果"""
    success: bool
    snapshots: List[MemorySnapshot]
    insights: List[str]
    suggestions: List[str]
    confidence: float = 0.0

# ============================================
# 记忆存储
# ============================================

class MemoryStorage:
    """记忆存储系统"""

    def __init__(self, storage_path: str = "./project_memory"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
        self.db_path = self.storage_path / "memory.db"
        self.init_database()

    def init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory_snapshots (
                id TEXT PRIMARY KEY,
                timestamp REAL,
                project_path TEXT,
                hash TEXT,
                node_count INTEGER,
                edge_count INTEGER,
                metadata TEXT,
                context TEXT,
                insights TEXT,
                file_path TEXT
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON memory_snapshots(timestamp)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_hash ON memory_snapshots(hash)
        """)

        conn.commit()
        conn.close()

    async def save_snapshot(self, snapshot: MemorySnapshot, project_path: str) -> bool:
        """保存记忆快照"""
        try:
            # 保存图谱数据到文件
            file_name = f"snapshot_{snapshot.id}.pkl"
            file_path = self.storage_path / file_name

            with open(file_path, 'wb') as f:
                pickle.dump(snapshot, f)

            # 保存元数据到数据库
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO memory_snapshots
                (id, timestamp, project_path, hash, node_count, edge_count,
                 metadata, context, insights, file_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                snapshot.id,
                snapshot.timestamp.timestamp(),
                project_path,
                snapshot.hash,
                len(snapshot.graph_data.nodes),
                len(snapshot.graph_data.edges),
                json.dumps(snapshot.metadata),
                json.dumps(snapshot.context),
                json.dumps(snapshot.insights),
                str(file_path)
            ))

            conn.commit()
            conn.close()

            logger.info(f"保存记忆快照: {snapshot.id}")
            return True

        except Exception as e:
            logger.error(f"保存快照失败: {e}")
            return False

    async def load_snapshot(self, snapshot_id: str) -> Optional[MemorySnapshot]:
        """加载记忆快照"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT file_path FROM memory_snapshots WHERE id = ?",
            (snapshot_id,)
        )
        result = cursor.fetchone()
        conn.close()

        if result:
            file_path = result[0]
            if os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    return pickle.load(f)

        return None

    async def search_snapshots(
        self,
        project_path: str,
        time_range: Optional[tuple] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """搜索快照"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = "SELECT * FROM memory_snapshots WHERE project_path = ?"
        params = [project_path]

        if time_range:
            query += " AND timestamp BETWEEN ? AND ?"
            params.extend([time_range[0].timestamp(), time_range[1].timestamp()])

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        columns = [column[0] for column in cursor.description]
        results = []

        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))

        conn.close()
        return results

# ============================================
# 记忆分析器
# ============================================

class MemoryAnalyzer:
    """记忆分析器"""

    def __init__(self):
        self.patterns = {}

    def calculate_similarity(
        self,
        graph1: GraphData,
        graph2: GraphData
    ) -> float:
        """计算两个图谱的相似度"""
        # 1. 节点相似度
        nodes1 = {n.path for n in graph1.nodes}
        nodes2 = {n.path for n in graph2.nodes}
        node_similarity = len(nodes1 & nodes2) / max(len(nodes1), len(nodes2))

        # 2. 边相似度
        edges1 = {(e.source, e.target) for e in graph1.edges}
        edges2 = {(e.source, e.target) for e in graph2.edges}
        edge_similarity = len(edges1 & edges2) / max(len(edges1), len(edges2), 1)

        # 3. 结构相似度
        struct_sim = self.calculate_structural_similarity(graph1, graph2)

        # 加权平均
        return 0.4 * node_similarity + 0.3 * edge_similarity + 0.3 * struct_sim

    def calculate_structural_similarity(
        self,
        graph1: GraphData,
        graph2: GraphData
    ) -> float:
        """计算结构相似度"""
        # 简化版：比较节点度分布
        degree1 = self.get_degree_distribution(graph1)
        degree2 = self.get_degree_distribution(graph2)

        if not degree1 or not degree2:
            return 0.0

        # 计算分布相似度
        all_degrees = set(degree1.keys()) | set(degree2.keys())
        similarity = 0
        for degree in all_degrees:
            d1 = degree1.get(degree, 0)
            d2 = degree2.get(degree, 0)
            similarity += 1 - abs(d1 - d2) / max(d1, d2, 1)

        return similarity / len(all_degrees)

    def get_degree_distribution(self, graph: GraphData) -> Dict[int, int]:
        """获取度分布"""
        degrees = {}
        for node in graph.nodes:
            degree = sum(1 for e in graph.edges
                        if e.source == node.id or e.target == node.id)
            degrees[degree] = degrees.get(degree, 0) + 1
        return degrees

    def find_changes(
        self,
        old_graph: GraphData,
        new_graph: GraphData
    ) -> Dict[str, List]:
        """找出两个图谱之间的变化"""
        old_nodes = {n.path: n for n in old_graph.nodes}
        new_nodes = {n.path: n for n in new_graph.nodes}

        added_nodes = set(new_nodes.keys()) - set(old_nodes.keys())
        removed_nodes = set(old_nodes.keys()) - set(new_nodes.keys())

        modified_nodes = []
        for path in set(old_nodes.keys()) & set(new_nodes.keys()):
            if old_nodes[path].size != new_nodes[path].size:
                modified_nodes.append(path)

        return {
            "added": list(added_nodes),
            "removed": list(removed_nodes),
            "modified": modified_nodes
        }

    def generate_insights(
        self,
        current_graph: GraphData,
        historical_graphs: List[GraphData]
    ) -> List[str]:
        """生成洞察"""
        insights = []

        # 1. 增长趋势
        if historical_graphs:
            old_size = len(historical_graphs[0].nodes)
            new_size = len(current_graph.nodes)
            growth = ((new_size - old_size) / old_size) * 100
            insights.append(f"项目规模增长: {growth:.1f}%")

        # 2. 复杂度分析
        avg_complexity = sum(n.complexity for n in current_graph.nodes) / len(current_graph.nodes)
        insights.append(f"平均复杂度: {avg_complexity:.1f}")

        # 3. 依赖密度
        density = len(current_graph.edges) / (len(current_graph.nodes) * (len(current_graph.nodes) - 1))
        insights.append(f"依赖密度: {density:.3f}")

        return insights

# ============================================
# 项目记忆系统
# ============================================

class ProjectMemorySystem:
    """项目记忆系统 - 主类"""

    def __init__(self, storage_path: str = "./project_memory"):
        self.storage = MemoryStorage(storage_path)
        self.analyzer = MemoryAnalyzer()
        self.graph_analyzer = ProjectAnalyzer()
        self.graph_generator = GraphGenerator()
        self.auto_snapshot_enabled = False
        self.snapshot_interval = 3600  # 1小时

    async def create_snapshot(
        self,
        project_path: str,
        trigger: str = "manual",
        context: Optional[Dict] = None
    ) -> MemorySnapshot:
        """创建记忆快照"""
        logger.info(f"创建记忆快照: {project_path}")

        # 生成图谱
        graph_data = await self.graph_analyzer.analyze_project(project_path)

        # 生成ID
        snapshot_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 收集上下文
        if not context:
            context = await self.collect_context(project_path)

        # 生成洞察
        historical = await self.get_recent_snapshots(project_path, limit=5)
        historical_graphs = [s.graph_data for s in historical]
        insights = self.analyzer.generate_insights(graph_data, historical_graphs)

        # 创建快照
        snapshot = MemorySnapshot(
            id=snapshot_id,
            timestamp=datetime.now(),
            graph_data=graph_data,
            metadata={
                "project_path": project_path,
                "trigger": trigger,
                "node_count": len(graph_data.nodes),
                "edge_count": len(graph_data.edges),
            },
            context=context,
            insights=insights
        )

        # 保存快照
        await self.storage.save_snapshot(snapshot, project_path)

        return snapshot

    async def recover_memory(
        self,
        query: MemoryQuery,
        project_path: str
    ) -> MemoryRecoveryResult:
        """恢复记忆"""
        logger.info(f"恢复记忆: {query.query_type}")

        if query.query_type == "similarity":
            # 基于相似度恢复
            return await self.recover_by_similarity(query, project_path)

        elif query.query_type == "time_range":
            # 基于时间范围恢复
            return await self.recover_by_time(query, project_path)

        elif query.query_type == "file_history":
            # 恢复文件历史
            return await self.recover_file_history(query, project_path)

        elif query.query_type == "pattern":
            # 基于模式恢复
            return await self.recover_by_pattern(query, project_path)

        else:
            return MemoryRecoveryResult(
                success=False,
                snapshots=[],
                insights=["未知的查询类型"],
                suggestions=[]
            )

    async def recover_by_similarity(
        self,
        query: MemoryQuery,
        project_path: str
    ) -> MemoryRecoveryResult:
        """基于相似度恢复记忆"""
        current_graph = query.parameters.get("current_graph")
        if not current_graph:
            # 生成当前图谱
            current_graph = await self.graph_analyzer.analyze_project(project_path)

        # 获取历史快照
        snapshots = await self.get_all_snapshots(project_path)

        # 计算相似度
        similarities = []
        for snapshot in snapshots:
            sim = self.analyzer.calculate_similarity(
                current_graph,
                snapshot.graph_data
            )
            similarities.append((snapshot, sim))

        # 排序并返回最相似的
        similarities.sort(key=lambda x: x[1], reverse=True)
        similar_snapshots = [s[0] for s in similarities[:5]]

        # 生成洞察
        insights = []
        if similar_snapshots:
            insights.append(
                f"找到 {len(similar_snapshots)} 个相似的历史状态"
            )
            insights.append(
                f"最相似的是 {similar_snapshots[0].timestamp.strftime('%Y-%m-%d %H:%M')}"
            )

        return MemoryRecoveryResult(
            success=True,
            snapshots=similar_snapshots,
            insights=insights,
            suggestions=self.generate_suggestions(similar_snapshots),
            confidence=similarities[0][1] if similarities else 0.0
        )

    async def recover_file_history(
        self,
        query: MemoryQuery,
        project_path: str
    ) -> MemoryRecoveryResult:
        """恢复文件历史"""
        file_path = query.parameters.get("file_path")
        if not file_path:
            return MemoryRecoveryResult(
                success=False,
                snapshots=[],
                insights=["需要提供文件路径"],
                suggestions=[]
            )

        # 获取所有包含该文件的快照
        all_snapshots = await self.get_all_snapshots(project_path)
        file_snapshots = []

        for snapshot in all_snapshots:
            for node in snapshot.graph_data.nodes:
                if node.path == file_path:
                    file_snapshots.append((snapshot, node))
                    break

        # 分析文件演变
        insights = []
        if file_snapshots:
            insights.append(f"文件出现在 {len(file_snapshots)} 个历史快照中")

            # 分析大小变化
            sizes = [node.size for _, node in file_snapshots]
            if len(sizes) > 1:
                size_change = sizes[-1] - sizes[0]
                insights.append(f"文件大小变化: {size_change} 字节")

            # 分析复杂度变化
            complexities = [node.complexity for _, node in file_snapshots]
            if len(complexities) > 1:
                complexity_change = complexities[-1] - complexities[0]
                insights.append(f"复杂度变化: {complexity_change}")

        return MemoryRecoveryResult(
            success=True,
            snapshots=[s for s, _ in file_snapshots],
            insights=insights,
            suggestions=["考虑重构" if len(file_snapshots) > 10 else "保持现状"],
            confidence=1.0 if file_snapshots else 0.0
        )

    async def get_recent_snapshots(
        self,
        project_path: str,
        limit: int = 10
    ) -> List[MemorySnapshot]:
        """获取最近的快照"""
        results = await self.storage.search_snapshots(project_path, limit=limit)
        snapshots = []

        for result in results:
            snapshot = await self.storage.load_snapshot(result['id'])
            if snapshot:
                snapshots.append(snapshot)

        return snapshots

    async def get_all_snapshots(self, project_path: str) -> List[MemorySnapshot]:
        """获取所有快照"""
        return await self.get_recent_snapshots(project_path, limit=1000)

    async def collect_context(self, project_path: str) -> Dict[str, Any]:
        """收集上下文信息"""
        context = {
            "timestamp": datetime.now().isoformat(),
            "project_path": project_path,
        }

        # 尝试获取Git信息
        try:
            import subprocess
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=project_path,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                context["git_commit"] = result.stdout.strip()

            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=project_path,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                context["git_branch"] = result.stdout.strip()
        except Exception:
            pass

        return context

    def generate_suggestions(
        self,
        snapshots: List[MemorySnapshot]
    ) -> List[str]:
        """生成建议"""
        suggestions = []

        if not snapshots:
            return ["创建初始快照以开始记录项目历史"]

        # 基于历史快照生成建议
        latest = snapshots[0]

        if len(latest.graph_data.nodes) > 100:
            suggestions.append("项目规模较大，考虑模块化重构")

        if len(latest.graph_data.edges) > len(latest.graph_data.nodes) * 2:
            suggestions.append("依赖关系复杂，考虑解耦")

        if latest.insights:
            suggestions.extend([
                f"基于洞察: {insight}"
                for insight in latest.insights[:2]
            ])

        return suggestions

    async def enable_auto_snapshot(
        self,
        project_path: str,
        interval: int = 3600
    ):
        """启用自动快照"""
        self.auto_snapshot_enabled = True
        self.snapshot_interval = interval

        logger.info(f"启用自动快照: 每 {interval} 秒")

        while self.auto_snapshot_enabled:
            await asyncio.sleep(interval)
            await self.create_snapshot(project_path, trigger="auto")

    def disable_auto_snapshot(self):
        """禁用自动快照"""
        self.auto_snapshot_enabled = False
        logger.info("禁用自动快照")

# ============================================
# 记忆恢复助手
# ============================================

class MemoryRecoveryAssistant:
    """记忆恢复助手 - 提供高级查询功能"""

    def __init__(self, memory_system: ProjectMemorySystem):
        self.memory_system = memory_system

    async def find_when_file_added(
        self,
        project_path: str,
        file_path: str
    ) -> Optional[datetime]:
        """查找文件何时添加"""
        snapshots = await self.memory_system.get_all_snapshots(project_path)

        for snapshot in reversed(snapshots):  # 从旧到新
            for node in snapshot.graph_data.nodes:
                if node.path == file_path:
                    return snapshot.timestamp

        return None

    async def find_when_dependency_added(
        self,
        project_path: str,
        source: str,
        target: str
    ) -> Optional[datetime]:
        """查找依赖何时添加"""
        snapshots = await self.memory_system.get_all_snapshots(project_path)

        for snapshot in reversed(snapshots):
            for edge in snapshot.graph_data.edges:
                if edge.source == source and edge.target == target:
                    return snapshot.timestamp

        return None

    async def explain_growth(
        self,
        project_path: str,
        time_range: Optional[tuple] = None
    ) -> Dict[str, Any]:
        """解释项目增长"""
        snapshots = await self.memory_system.get_all_snapshots(project_path)

        if not snapshots:
            return {"error": "没有历史快照"}

        # 过滤时间范围
        if time_range:
            snapshots = [
                s for s in snapshots
                if time_range[0] <= s.timestamp <= time_range[1]
            ]

        if len(snapshots) < 2:
            return {"error": "快照不足以分析增长"}

        oldest = snapshots[-1]
        newest = snapshots[0]

        # 计算增长指标
        node_growth = len(newest.graph_data.nodes) - len(oldest.graph_data.nodes)
        edge_growth = len(newest.graph_data.edges) - len(oldest.graph_data.edges)

        # 找出新增的主要文件
        old_paths = {n.path for n in oldest.graph_data.nodes}
        new_paths = {n.path for n in newest.graph_data.nodes}
        added_files = new_paths - old_paths

        return {
            "time_period": f"{oldest.timestamp} 到 {newest.timestamp}",
            "node_growth": node_growth,
            "edge_growth": edge_growth,
            "added_files": list(added_files)[:10],  # 前10个
            "growth_rate": f"{(node_growth / len(oldest.graph_data.nodes)) * 100:.1f}%"
        }

# ============================================
# 使用示例
# ============================================

async def demo():
    """演示记忆系统的使用"""
    print("=" * 60)
    print("🧠 项目记忆系统演示")
    print("=" * 60)

    # 创建记忆系统
    memory_system = ProjectMemorySystem()

    # 项目路径
    project_path = "/Users/mac/Downloads/MCP"

    print("\n1. 创建记忆快照...")
    snapshot = await memory_system.create_snapshot(
        project_path,
        trigger="demo",
        context={"reason": "演示记忆系统"}
    )
    print(f"   ✅ 快照创建成功: {snapshot.id}")
    print(f"   - 节点数: {len(snapshot.graph_data.nodes)}")
    print(f"   - 边数: {len(snapshot.graph_data.edges)}")
    print(f"   - 洞察: {snapshot.insights}")

    print("\n2. 恢复相似记忆...")
    query = MemoryQuery(
        query_type="similarity",
        parameters={"current_graph": snapshot.graph_data}
    )
    result = await memory_system.recover_memory(query, project_path)
    print(f"   ✅ 找到 {len(result.snapshots)} 个相似快照")
    print(f"   - 置信度: {result.confidence:.2f}")
    print(f"   - 洞察: {result.insights}")
    print(f"   - 建议: {result.suggestions}")

    print("\n3. 查询文件历史...")
    query = MemoryQuery(
        query_type="file_history",
        parameters={"file_path": "src/mcp_core/services/ai_model_manager.py"}
    )
    result = await memory_system.recover_memory(query, project_path)
    print(f"   ✅ 文件历史恢复")
    print(f"   - 快照数: {len(result.snapshots)}")
    print(f"   - 洞察: {result.insights}")

    print("\n4. 使用恢复助手...")
    assistant = MemoryRecoveryAssistant(memory_system)
    growth = await assistant.explain_growth(project_path)
    print(f"   ✅ 项目增长分析")
    for key, value in growth.items():
        if key != "added_files":
            print(f"   - {key}: {value}")

    print("\n" + "=" * 60)
    print("💡 记忆系统可以:")
    print("   1. 自动保存项目状态快照")
    print("   2. 基于相似度恢复历史")
    print("   3. 追踪文件演变历程")
    print("   4. 分析项目增长趋势")
    print("   5. 提供智能建议")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(demo())
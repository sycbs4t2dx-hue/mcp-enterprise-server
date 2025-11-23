"""
混合存储与项目记忆系统集成
将HybridStorageManager与ProjectMemorySystem无缝连接
提供统一的记忆管理接口
"""

import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

from src.mcp_core.services.hybrid_storage_system import (
    HybridStorageManager,
    create_storage
)
from src.mcp_core.services.project_memory_system import (
    ProjectMemorySystem,
    MemorySnapshot,
    MemoryQuery,
    MemoryRecoveryResult
)
from src.mcp_core.services.project_graph_generator import GraphData
from src.mcp_core.common.logger import get_logger

logger = get_logger(__name__)


class IntegratedMemoryManager:
    """
    集成记忆管理器
    结合混合存储(HybridStorage)和项目记忆(ProjectMemory)的优势
    """

    def __init__(self, project_path: str, storage_mode: str = 'auto'):
        """
        初始化集成记忆管理器

        Args:
            project_path: 项目路径
            storage_mode: 存储模式 ('auto', 'hybrid', 'local', 'central')
        """
        self.project_path = project_path

        # 初始化混合存储 (SQLite + MySQL)
        self.hybrid_storage = create_storage(project_path, mode=storage_mode)

        # 初始化项目记忆系统 (图谱分析)
        memory_storage_path = str(Path(project_path) / ".mcp_memory" / "project_memory")
        self.memory_system = ProjectMemorySystem(storage_path=memory_storage_path)

        # 统计信息
        self.stats = {
            'total_snapshots': 0,
            'total_searches': 0,
            'cache_hits': 0,
            'sync_count': 0
        }

        logger.info(f"集成记忆管理器初始化完成: {project_path}")

    async def create_snapshot(
        self,
        trigger: str = "manual",
        context: Optional[Dict] = None,
        sync_options: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        创建记忆快照 - 同时使用两个系统

        Args:
            trigger: 触发器类型 (manual/auto/milestone/commit)
            context: 上下文信息
            sync_options: 同步选项 (importance, team_mode等)

        Returns:
            快照信息
        """
        logger.info(f"创建记忆快照: {trigger}")

        try:
            # 1. 使用ProjectMemorySystem生成图谱快照
            memory_snapshot = await self.memory_system.create_snapshot(
                project_path=self.project_path,
                trigger=trigger,
                context=context
            )

            # 2. 转换为混合存储格式
            storage_data = self._convert_memory_to_storage(memory_snapshot)

            # 3. 保存到混合存储 (本地SQLite + 可选MySQL同步)
            sync_opts = sync_options or {}
            sync_opts['trigger'] = trigger

            snapshot_id = await self.hybrid_storage.save(storage_data, sync_opts)

            # 4. 更新统计
            self.stats['total_snapshots'] += 1

            logger.info(f"快照创建成功: {snapshot_id}")

            return {
                'success': True,
                'snapshot_id': snapshot_id,
                'memory_snapshot_id': memory_snapshot.id,
                'node_count': len(memory_snapshot.graph_data.nodes),
                'edge_count': len(memory_snapshot.graph_data.edges),
                'insights': memory_snapshot.insights,
                'storage': {
                    'local': True,
                    'synced': sync_opts.get('sync', False)
                }
            }

        except Exception as e:
            logger.error(f"创建快照失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def search_memories(
        self,
        query: str,
        search_options: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        智能搜索记忆 - 并行搜索多个源

        Args:
            query: 搜索查询
            search_options: 搜索选项 (local, central, team, limit)

        Returns:
            搜索结果列表
        """
        logger.info(f"搜索记忆: {query}")

        options = search_options or {}

        try:
            # 使用混合存储的并行搜索能力
            results = await self.hybrid_storage.search(query, options)

            # 增强结果 - 添加图谱上下文
            enhanced_results = []
            for result in results:
                enhanced = self._enhance_search_result(result)
                enhanced_results.append(enhanced)

            # 更新统计
            self.stats['total_searches'] += 1

            logger.info(f"搜索完成: 找到 {len(enhanced_results)} 个结果")

            return enhanced_results

        except Exception as e:
            logger.error(f"搜索失败: {e}")
            return []

    async def recover_memory(
        self,
        query_type: str,
        parameters: Dict[str, Any]
    ) -> MemoryRecoveryResult:
        """
        恢复记忆 - 基于不同策略

        Args:
            query_type: 查询类型 (similarity/time_range/file_history/pattern)
            parameters: 查询参数

        Returns:
            恢复结果
        """
        logger.info(f"恢复记忆: {query_type}")

        try:
            # 构建查询
            query = MemoryQuery(
                query_type=query_type,
                parameters=parameters
            )

            # 使用项目记忆系统的高级恢复功能
            result = await self.memory_system.recover_memory(query, self.project_path)

            logger.info(f"恢复完成: {len(result.snapshots)} 个快照")

            return result

        except Exception as e:
            logger.error(f"恢复失败: {e}")
            return MemoryRecoveryResult(
                success=False,
                snapshots=[],
                insights=[f"恢复失败: {str(e)}"],
                suggestions=[]
            )

    async def sync_to_team(self) -> Dict[str, Any]:
        """
        同步本地记忆到团队中央存储

        Returns:
            同步结果
        """
        logger.info("同步到团队存储...")

        try:
            synced_count = await self.hybrid_storage.sync_to_central()

            # 更新统计
            self.stats['sync_count'] += synced_count

            return {
                'success': True,
                'synced_count': synced_count,
                'message': f"成功同步 {synced_count} 个快照"
            }

        except Exception as e:
            logger.error(f"同步失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def share_insight(
        self,
        content: str,
        tags: List[str] = None
    ) -> Dict[str, Any]:
        """
        分享洞察到团队

        Args:
            content: 洞察内容
            tags: 标签

        Returns:
            分享结果
        """
        logger.info("分享洞察到团队")

        try:
            insight_id = await self.hybrid_storage.share_insight(content, tags)

            return {
                'success': True,
                'insight_id': insight_id,
                'message': "洞察已分享到团队"
            }

        except Exception as e:
            logger.error(f"分享失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def get_team_insights(
        self,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        获取团队洞察

        Args:
            limit: 返回数量限制

        Returns:
            洞察列表
        """
        try:
            insights = await self.hybrid_storage.get_team_insights(limit)
            return insights

        except Exception as e:
            logger.error(f"获取团队洞察失败: {e}")
            return []

    async def analyze_patterns(self) -> Dict[str, Any]:
        """
        分析模式 - 结合本地和全局

        Returns:
            模式分析结果
        """
        logger.info("分析项目模式...")

        try:
            # 使用混合存储的模式分析
            patterns = await self.hybrid_storage.analyze_patterns()

            return {
                'success': True,
                'patterns': patterns,
                'recommendations': patterns.get('recommendations', [])
            }

        except Exception as e:
            logger.error(f"模式分析失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def get_snapshot(
        self,
        snapshot_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取特定快照

        Args:
            snapshot_id: 快照ID

        Returns:
            快照数据
        """
        try:
            # 从混合存储加载
            data = await self.hybrid_storage.load(snapshot_id)

            if data:
                # 增加缓存命中统计
                self.stats['cache_hits'] += 1

            return data

        except Exception as e:
            logger.error(f"加载快照失败: {e}")
            return None

    async def get_file_history(
        self,
        file_path: str
    ) -> Dict[str, Any]:
        """
        获取文件的历史记录

        Args:
            file_path: 文件路径

        Returns:
            文件历史
        """
        logger.info(f"获取文件历史: {file_path}")

        try:
            result = await self.recover_memory(
                query_type='file_history',
                parameters={'file_path': file_path}
            )

            return {
                'success': result.success,
                'snapshots': len(result.snapshots),
                'insights': result.insights,
                'suggestions': result.suggestions
            }

        except Exception as e:
            logger.error(f"获取文件历史失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取综合统计信息

        Returns:
            统计数据
        """
        # 获取混合存储统计
        storage_stats = self.hybrid_storage.get_stats()

        # 合并统计信息
        return {
            'integrated_manager': {
                'total_snapshots': self.stats['total_snapshots'],
                'total_searches': self.stats['total_searches'],
                'cache_hits': self.stats['cache_hits'],
                'sync_count': self.stats['sync_count']
            },
            'storage': storage_stats,
            'project_path': self.project_path
        }

    async def cleanup(
        self,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        清理旧数据

        Args:
            days: 保留天数

        Returns:
            清理结果
        """
        logger.info(f"清理 {days} 天前的数据...")

        try:
            deleted_count = await self.hybrid_storage.cleanup_old_snapshots(days)

            return {
                'success': True,
                'deleted_count': deleted_count,
                'message': f"清理了 {deleted_count} 个旧快照"
            }

        except Exception as e:
            logger.error(f"清理失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    # ============================================
    # 私有辅助方法
    # ============================================

    def _convert_memory_to_storage(
        self,
        memory_snapshot: MemorySnapshot
    ) -> Dict[str, Any]:
        """
        将MemorySnapshot转换为混合存储格式

        Args:
            memory_snapshot: 记忆快照

        Returns:
            存储格式数据
        """
        return {
            'nodes': [
                {
                    'id': node.id,
                    'path': node.path,
                    'type': node.type,
                    'name': node.name,
                    'size': node.size,
                    'complexity': node.complexity
                }
                for node in memory_snapshot.graph_data.nodes
            ],
            'edges': [
                {
                    'source': edge.source,
                    'target': edge.target,
                    'type': edge.type,
                    'weight': edge.weight
                }
                for edge in memory_snapshot.graph_data.edges
            ],
            'metadata': memory_snapshot.metadata,
            'context': memory_snapshot.context,
            'insights': memory_snapshot.insights,
            'node_count': len(memory_snapshot.graph_data.nodes),
            'edge_count': len(memory_snapshot.graph_data.edges),
            'timestamp': memory_snapshot.timestamp.isoformat()
        }

    def _enhance_search_result(
        self,
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        增强搜索结果

        Args:
            result: 原始搜索结果

        Returns:
            增强后的结果
        """
        # 添加额外的上下文信息
        enhanced = result.copy()

        # 计算相关性评分
        if 'data' in enhanced and 'nodes' in enhanced['data']:
            enhanced['complexity_avg'] = sum(
                n.get('complexity', 0) for n in enhanced['data']['nodes']
            ) / max(len(enhanced['data']['nodes']), 1)

        # 添加快照年龄
        if 'timestamp' in enhanced:
            try:
                snapshot_time = datetime.fromisoformat(enhanced['timestamp'])
                age_days = (datetime.now() - snapshot_time).days
                enhanced['age_days'] = age_days
                enhanced['age_category'] = self._categorize_age(age_days)
            except:
                pass

        return enhanced

    def _categorize_age(self, days: int) -> str:
        """分类快照年龄"""
        if days < 1:
            return 'today'
        elif days < 7:
            return 'this_week'
        elif days < 30:
            return 'this_month'
        elif days < 90:
            return 'recent'
        else:
            return 'old'


# ============================================
# 工厂函数
# ============================================

def create_integrated_manager(
    project_path: str,
    storage_mode: str = 'auto'
) -> IntegratedMemoryManager:
    """
    创建集成记忆管理器实例

    Args:
        project_path: 项目路径
        storage_mode: 存储模式

    Returns:
        IntegratedMemoryManager实例
    """
    return IntegratedMemoryManager(project_path, storage_mode)


# ============================================
# 使用示例
# ============================================

async def demo():
    """演示集成记忆管理器"""
    print("=" * 60)
    print("混合存储 + 项目记忆 集成演示")
    print("=" * 60)

    # 创建管理器
    manager = create_integrated_manager(
        project_path="/Users/mac/Downloads/MCP",
        storage_mode='hybrid'
    )

    print("\n1. 创建快照...")
    result = await manager.create_snapshot(
        trigger='demo',
        context={'reason': '演示集成系统'},
        sync_options={
            'importance': 'high',
            'team_mode': True
        }
    )
    print(f"   快照ID: {result['snapshot_id']}")
    print(f"   节点数: {result['node_count']}")
    print(f"   洞察: {result['insights']}")

    print("\n2. 搜索记忆...")
    search_results = await manager.search_memories(
        query='analyzer',
        search_options={
            'local': True,
            'central': True,
            'limit': 5
        }
    )
    print(f"   找到 {len(search_results)} 个结果")

    print("\n3. 获取统计...")
    stats = manager.get_statistics()
    print(f"   总快照数: {stats['integrated_manager']['total_snapshots']}")
    print(f"   存储模式: {stats['storage']['storage_mode']}")
    print(f"   本地快照: {stats['storage']['local']['total_count']}")
    print(f"   中央快照: {stats['storage']['central']['total_count']}")

    print("\n4. 分析模式...")
    patterns = await manager.analyze_patterns()
    if patterns['success']:
        print("   推荐:")
        for rec in patterns.get('recommendations', []):
            print(f"   - {rec}")

    print("\n5. 同步到团队...")
    sync_result = await manager.sync_to_team()
    print(f"   {sync_result['message']}")

    print("\n" + "=" * 60)
    print("集成优势:")
    print("1. 本地高性能 (SQLite) + 团队共享 (MySQL)")
    print("2. 智能图谱分析 + 灵活存储策略")
    print("3. 多源并行搜索 + 智能缓存")
    print("4. 自动同步 + 离线支持")
    print("5. 模式识别 + 团队协作")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(demo())

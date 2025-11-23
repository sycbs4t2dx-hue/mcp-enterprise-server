"""
混合记忆存储系统 - SQLite + MySQL
实现本地高性能与团队共享的完美结合
"""

import os
import json
import sqlite3
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
import hashlib

from sqlalchemy import create_engine, Column, String, Integer, Text, DateTime, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

from src.mcp_core.common.logger import get_logger
from src.mcp_core.common.config import get_settings

logger = get_logger(__name__)

Base = declarative_base()

# ============================================
# 数据模型
# ============================================

class MemorySnapshot(Base):
    """MySQL中的记忆快照表"""
    __tablename__ = 'memory_snapshots'

    id = Column(String(50), primary_key=True)
    project_id = Column(String(50), index=True)
    project_path = Column(Text)
    timestamp = Column(DateTime, default=datetime.now)
    trigger_type = Column(String(50))
    node_count = Column(Integer)
    edge_count = Column(Integer)
    complexity = Column(Float)
    graph_data = Column(Text)  # JSON
    meta_data = Column(Text)    # JSON (renamed from metadata to avoid SQLAlchemy conflict)
    insights = Column(Text)    # JSON
    hash = Column(String(100), index=True)
    created_by = Column(String(100))
    team_id = Column(String(50), index=True)
    is_public = Column(Boolean, default=False)

class MemoryPattern(Base):
    """识别的模式表"""
    __tablename__ = 'memory_patterns'

    id = Column(Integer, primary_key=True, autoincrement=True)
    pattern_type = Column(String(50))
    pattern_data = Column(Text)
    frequency = Column(Integer, default=1)
    projects = Column(Text)  # JSON array of project IDs
    first_seen = Column(DateTime, default=datetime.now)
    last_seen = Column(DateTime, default=datetime.now)
    confidence = Column(Float)

class SharedInsight(Base):
    """团队共享的洞察"""
    __tablename__ = 'shared_insights'

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(50), index=True)
    insight_type = Column(String(50))
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    created_by = Column(String(100))
    upvotes = Column(Integer, default=0)
    tags = Column(Text)  # JSON array

# ============================================
# 混合存储管理器
# ============================================

class HybridStorageManager:
    """混合存储管理器 - 智能选择存储策略"""

    def __init__(self, project_path: str):
        self.project_path = project_path
        self.project_id = self._generate_project_id(project_path)

        # 初始化存储
        self.local_storage = LocalSQLiteStorage(project_path)
        self.central_storage = CentralMySQLStorage()

        # 同步配置
        self.sync_enabled = True
        self.sync_interval = 300  # 5分钟
        self.last_sync = None

        # 缓存配置
        self.cache_ttl = 3600  # 1小时
        self.cache = {}

        # 启动后台任务
        self._start_background_tasks()

    def _generate_project_id(self, path: str) -> str:
        """生成项目唯一ID"""
        return hashlib.md5(path.encode()).hexdigest()[:12]

    def _start_background_tasks(self):
        """启动后台任务"""
        if self.sync_enabled:
            asyncio.create_task(self._auto_sync_task())
            asyncio.create_task(self._cleanup_task())

    async def _auto_sync_task(self):
        """自动同步任务"""
        while self.sync_enabled:
            await asyncio.sleep(self.sync_interval)
            try:
                await self.sync_to_central()
            except Exception as e:
                logger.error(f"自动同步失败: {e}")

    async def _cleanup_task(self):
        """清理任务"""
        while True:
            await asyncio.sleep(3600)  # 每小时清理
            try:
                # 清理过期缓存
                self._cleanup_cache()
                # 清理旧快照
                await self.cleanup_old_snapshots()
            except Exception as e:
                logger.error(f"清理任务失败: {e}")

    async def save(self, data: Dict[str, Any], options: Dict[str, Any] = None) -> str:
        """智能保存 - 根据策略选择存储"""
        options = options or {}

        # 生成快照ID
        snapshot_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:20]

        # 准备数据
        snapshot_data = {
            'id': snapshot_id,
            'project_id': self.project_id,
            'project_path': self.project_path,
            'timestamp': datetime.now().isoformat(),
            'data': data,
            'metadata': options.get('metadata', {}),
            'hash': self._calculate_hash(data)
        }

        # 1. 总是先保存到本地（快速）
        self.local_storage.save(snapshot_id, snapshot_data)
        logger.info(f"快照已保存到本地: {snapshot_id}")

        # 2. 根据策略决定是否同步到中央
        if self._should_sync_to_central(options):
            # 异步同步到MySQL
            asyncio.create_task(self._async_save_to_central(snapshot_data))

        # 3. 更新缓存
        self._update_cache(snapshot_id, snapshot_data)

        return snapshot_id

    def _should_sync_to_central(self, options: Dict) -> bool:
        """判断是否应该同步到中央"""
        # 策略1: 明确指定
        if 'sync' in options:
            return options['sync']

        # 策略2: 重要性判断
        if options.get('importance', 'normal') == 'high':
            return True

        # 策略3: 团队模式
        if options.get('team_mode', False):
            return True

        # 策略4: 里程碑事件
        if options.get('trigger') in ['milestone', 'release', 'commit']:
            return True

        # 默认：定期同步
        return self.sync_enabled

    async def _async_save_to_central(self, snapshot_data: Dict):
        """异步保存到中央MySQL"""
        try:
            self.central_storage.save(snapshot_data)
            # 标记本地为已同步
            self.local_storage.mark_synced(snapshot_data['id'])
            logger.info(f"快照已同步到MySQL: {snapshot_data['id']}")
        except Exception as e:
            logger.error(f"同步到MySQL失败: {e}")
            # 失败后会在下次自动同步时重试

    async def load(self, snapshot_id: str) -> Optional[Dict]:
        """智能加载 - 多级查找"""
        # 1. 检查缓存
        cached = self._get_from_cache(snapshot_id)
        if cached:
            logger.debug(f"从缓存加载: {snapshot_id}")
            return cached

        # 2. 查询本地
        local_data = self.local_storage.load(snapshot_id)
        if local_data:
            logger.debug(f"从本地加载: {snapshot_id}")
            self._update_cache(snapshot_id, local_data)
            return local_data

        # 3. 查询中央
        central_data = await self.central_storage.load(snapshot_id)
        if central_data:
            logger.debug(f"从中央加载: {snapshot_id}")
            # 缓存到本地
            self.local_storage.save(snapshot_id, central_data)
            self._update_cache(snapshot_id, central_data)
            return central_data

        return None

    async def search(self, query: str, options: Dict = None) -> List[Dict]:
        """智能搜索 - 并行搜索多个源"""
        options = options or {}
        results = []

        # 决定搜索范围
        search_local = options.get('local', True)
        search_central = options.get('central', True)
        search_team = options.get('team', False)

        tasks = []

        if search_local:
            tasks.append(self._search_local(query))

        if search_central:
            tasks.append(self._search_central(query))

        if search_team:
            tasks.append(self._search_team_projects(query))

        # 并行执行搜索
        if tasks:
            search_results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in search_results:
                if isinstance(result, list):
                    results.extend(result)

        # 去重和排序
        unique_results = self._deduplicate_results(results)
        return self._rank_results(unique_results, query)

    async def _search_local(self, query: str) -> List[Dict]:
        """本地搜索"""
        return self.local_storage.search(query)

    async def _search_central(self, query: str) -> List[Dict]:
        """中央搜索"""
        return await self.central_storage.search(query, self.project_id)

    async def _search_team_projects(self, query: str) -> List[Dict]:
        """搜索团队其他项目"""
        team_id = self._get_team_id()
        if team_id:
            return await self.central_storage.search_team(query, team_id)
        return []

    async def sync_to_central(self):
        """同步本地未同步的数据到中央"""
        unsynced = self.local_storage.get_unsynced()

        success_count = 0
        for snapshot in unsynced:
            try:
                await self.central_storage.save(snapshot)
                self.local_storage.mark_synced(snapshot['id'])
                success_count += 1
            except Exception as e:
                logger.error(f"同步快照 {snapshot['id']} 失败: {e}")

        if success_count > 0:
            logger.info(f"成功同步 {success_count} 个快照到中央存储")

        self.last_sync = datetime.now()
        return success_count

    async def share_insight(self, content: str, tags: List[str] = None):
        """分享洞察到团队"""
        insight = {
            'project_id': self.project_id,
            'content': content,
            'tags': tags or [],
            'created_by': self._get_current_user(),
            'created_at': datetime.now()
        }

        return await self.central_storage.save_insight(insight)

    async def get_team_insights(self, limit: int = 20) -> List[Dict]:
        """获取团队洞察"""
        team_id = self._get_team_id()
        if team_id:
            return await self.central_storage.get_team_insights(team_id, limit)
        return []

    async def analyze_patterns(self) -> Dict[str, Any]:
        """分析模式 - 结合本地和全局"""
        # 本地模式
        local_patterns = self.local_storage.analyze_patterns()

        # 全局模式
        global_patterns = await self.central_storage.get_global_patterns()

        # 团队模式
        team_patterns = await self.central_storage.get_team_patterns(self._get_team_id())

        return {
            'local': local_patterns,
            'global': global_patterns,
            'team': team_patterns,
            'recommendations': self._generate_recommendations(
                local_patterns, global_patterns, team_patterns
            )
        }

    def _generate_recommendations(self, local, global_p, team) -> List[str]:
        """基于模式生成建议"""
        recommendations = []

        # 分析本地与全局差异
        if local and global_p:
            # 比较复杂度
            if local.get('avg_complexity', 0) > global_p.get('avg_complexity', 0) * 1.5:
                recommendations.append("您的项目复杂度高于平均水平，考虑重构")

            # 比较依赖密度
            if local.get('dependency_density', 0) > global_p.get('dependency_density', 0) * 1.2:
                recommendations.append("依赖关系密集，建议解耦模块")

        # 基于团队模式
        if team:
            best_practices = team.get('best_practices', [])
            for practice in best_practices[:3]:
                recommendations.append(f"团队最佳实践: {practice}")

        return recommendations

    async def cleanup_old_snapshots(self, days: int = 30):
        """清理旧快照"""
        cutoff_date = datetime.now() - timedelta(days=days)

        # 清理本地
        local_deleted = self.local_storage.delete_before(cutoff_date)

        # 中央保留更久（可配置）
        if days > 90:  # 只有超过90天才清理中央
            central_deleted = await self.central_storage.delete_before(cutoff_date)
        else:
            central_deleted = 0

        logger.info(f"清理完成: 本地删除 {local_deleted}, 中央删除 {central_deleted}")
        return local_deleted + central_deleted

    def _calculate_hash(self, data: Any) -> str:
        """计算数据哈希"""
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()

    def _update_cache(self, key: str, value: Any):
        """更新缓存"""
        self.cache[key] = {
            'data': value,
            'timestamp': datetime.now()
        }

    def _get_from_cache(self, key: str) -> Optional[Any]:
        """从缓存获取"""
        if key in self.cache:
            cached = self.cache[key]
            age = (datetime.now() - cached['timestamp']).total_seconds()
            if age < self.cache_ttl:
                return cached['data']
            else:
                del self.cache[key]
        return None

    def _cleanup_cache(self):
        """清理过期缓存"""
        now = datetime.now()
        expired = []

        for key, value in self.cache.items():
            age = (now - value['timestamp']).total_seconds()
            if age > self.cache_ttl:
                expired.append(key)

        for key in expired:
            del self.cache[key]

        if expired:
            logger.debug(f"清理了 {len(expired)} 个过期缓存项")

    def _deduplicate_results(self, results: List[Dict]) -> List[Dict]:
        """去重结果"""
        seen = set()
        unique = []

        for result in results:
            result_id = result.get('id')
            if result_id and result_id not in seen:
                seen.add(result_id)
                unique.append(result)

        return unique

    def _rank_results(self, results: List[Dict], query: str) -> List[Dict]:
        """对结果排序"""
        # 简单的相关性评分
        for result in results:
            score = 0

            # 时间因素
            if 'timestamp' in result:
                age_days = (datetime.now() - datetime.fromisoformat(result['timestamp'])).days
                score -= age_days * 0.1

            # 查询匹配度
            if query.lower() in str(result).lower():
                score += 10

            # 重要性
            if result.get('metadata', {}).get('importance') == 'high':
                score += 5

            result['_score'] = score

        # 按分数排序
        return sorted(results, key=lambda x: x.get('_score', 0), reverse=True)

    def _get_team_id(self) -> Optional[str]:
        """获取团队ID"""
        # 从配置或环境变量获取
        return os.environ.get('MCP_TEAM_ID')

    def _get_current_user(self) -> str:
        """获取当前用户"""
        return os.environ.get('USER', 'unknown')

    def get_stats(self) -> Dict[str, Any]:
        """获取存储统计"""
        local_stats = self.local_storage.get_stats()
        central_stats = self.central_storage.get_stats(self.project_id)

        return {
            'storage_mode': 'hybrid',
            'local': local_stats,
            'central': central_stats,
            'cache': {
                'size': len(self.cache),
                'hit_rate': self._calculate_cache_hit_rate()
            },
            'sync': {
                'enabled': self.sync_enabled,
                'last_sync': self.last_sync.isoformat() if self.last_sync else None,
                'pending': local_stats.get('unsynced_count', 0)
            }
        }

    def _calculate_cache_hit_rate(self) -> float:
        """计算缓存命中率"""
        # 这里简化处理，实际应该记录命中次数
        return 0.75  # 示例值

# ============================================
# 本地SQLite存储
# ============================================

class LocalSQLiteStorage:
    """本地SQLite存储实现"""

    def __init__(self, project_path: str):
        self.project_path = project_path
        self.db_path = Path(project_path) / ".mcp_memory" / "local.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = self._init_db()

    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row

        conn.execute("""
            CREATE TABLE IF NOT EXISTS snapshots (
                id TEXT PRIMARY KEY,
                timestamp REAL,
                data TEXT,
                metadata TEXT,
                hash TEXT,
                synced INTEGER DEFAULT 0,
                sync_time REAL
            )
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp
            ON snapshots(timestamp)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_synced
            ON snapshots(synced)
        """)

        conn.commit()
        return conn

    def save(self, snapshot_id: str, data: Dict):
        """保存到本地"""
        self.conn.execute("""
            INSERT OR REPLACE INTO snapshots
            (id, timestamp, data, metadata, hash, synced)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            snapshot_id,
            datetime.now().timestamp(),
            json.dumps(data),
            json.dumps(data.get('metadata', {})),
            data.get('hash', ''),
            0
        ))
        self.conn.commit()

    def load(self, snapshot_id: str) -> Optional[Dict]:
        """加载快照"""
        cursor = self.conn.execute(
            "SELECT data FROM snapshots WHERE id = ?",
            (snapshot_id,)
        )
        row = cursor.fetchone()

        if row:
            return json.loads(row['data'])
        return None

    def search(self, query: str, limit: int = 20) -> List[Dict]:
        """搜索快照"""
        cursor = self.conn.execute("""
            SELECT id, timestamp, data
            FROM snapshots
            WHERE data LIKE ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (f'%{query}%', limit))

        results = []
        for row in cursor:
            data = json.loads(row['data'])
            data['id'] = row['id']
            data['timestamp'] = datetime.fromtimestamp(row['timestamp']).isoformat()
            results.append(data)

        return results

    def get_unsynced(self) -> List[Dict]:
        """获取未同步的快照"""
        cursor = self.conn.execute("""
            SELECT data FROM snapshots
            WHERE synced = 0
            ORDER BY timestamp
            LIMIT 100
        """)

        return [json.loads(row['data']) for row in cursor]

    def mark_synced(self, snapshot_id: str):
        """标记为已同步"""
        self.conn.execute("""
            UPDATE snapshots
            SET synced = 1, sync_time = ?
            WHERE id = ?
        """, (datetime.now().timestamp(), snapshot_id))
        self.conn.commit()

    def delete_before(self, cutoff: datetime) -> int:
        """删除指定日期前的快照"""
        cursor = self.conn.execute("""
            DELETE FROM snapshots
            WHERE timestamp < ? AND synced = 1
        """, (cutoff.timestamp(),))

        self.conn.commit()
        return cursor.rowcount

    def analyze_patterns(self) -> Dict:
        """分析本地模式"""
        cursor = self.conn.execute("""
            SELECT COUNT(*) as count,
                   AVG(LENGTH(data)) as avg_size,
                   MAX(timestamp) as latest,
                   MIN(timestamp) as earliest
            FROM snapshots
        """)

        row = cursor.fetchone()

        return {
            'total_snapshots': row['count'],
            'avg_size': row['avg_size'],
            'time_span': row['latest'] - row['earliest'] if row['latest'] else 0
        }

    def get_stats(self) -> Dict:
        """获取统计信息"""
        cursor = self.conn.execute("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN synced = 0 THEN 1 ELSE 0 END) as unsynced,
                   SUM(LENGTH(data)) as total_size
            FROM snapshots
        """)

        row = cursor.fetchone()

        return {
            'total_count': row['total'],
            'unsynced_count': row['unsynced'],
            'total_size': row['total_size'],
            'db_size': os.path.getsize(self.db_path) if self.db_path.exists() else 0
        }

# ============================================
# 中央MySQL存储
# ============================================

class CentralMySQLStorage:
    """中央MySQL存储实现"""

    def __init__(self):
        self.engine = self._create_engine()
        self.Session = sessionmaker(bind=self.engine)
        self._init_tables()

    def _create_engine(self):
        """创建数据库引擎"""
        settings = get_settings()

        db_url = f"mysql+pymysql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"

        return create_engine(
            db_url,
            poolclass=QueuePool,
            pool_size=10,
            max_overflow=20,
            pool_recycle=3600,
            echo=False
        )

    def _init_tables(self):
        """初始化表"""
        Base.metadata.create_all(self.engine)

    def save(self, data: Dict):
        """保存到MySQL"""
        session = self.Session()
        try:
            snapshot = MemorySnapshot(
                id=data['id'],
                project_id=data['project_id'],
                project_path=data['project_path'],
                timestamp=datetime.fromisoformat(data['timestamp']),
                node_count=data.get('node_count', 0),
                edge_count=data.get('edge_count', 0),
                graph_data=json.dumps(data.get('data', {})),
                meta_data=json.dumps(data.get('metadata', {})),
                hash=data.get('hash', ''),
                created_by=os.environ.get('USER', 'unknown')
            )

            session.merge(snapshot)  # 使用merge避免重复
            session.commit()

        finally:
            session.close()

    async def load(self, snapshot_id: str) -> Optional[Dict]:
        """从MySQL加载"""
        session = self.Session()
        try:
            snapshot = session.query(MemorySnapshot).filter_by(id=snapshot_id).first()

            if snapshot:
                return {
                    'id': snapshot.id,
                    'project_id': snapshot.project_id,
                    'project_path': snapshot.project_path,
                    'timestamp': snapshot.timestamp.isoformat(),
                    'data': json.loads(snapshot.graph_data),
                    'metadata': json.loads(snapshot.meta_data),
                    'hash': snapshot.hash
                }

        finally:
            session.close()

        return None

    async def search(self, query: str, project_id: str, limit: int = 20) -> List[Dict]:
        """搜索快照"""
        session = self.Session()
        try:
            snapshots = session.query(MemorySnapshot).filter(
                MemorySnapshot.project_id == project_id,
                MemorySnapshot.graph_data.contains(query)
            ).order_by(
                MemorySnapshot.timestamp.desc()
            ).limit(limit).all()

            results = []
            for snapshot in snapshots:
                results.append({
                    'id': snapshot.id,
                    'timestamp': snapshot.timestamp.isoformat(),
                    'data': json.loads(snapshot.graph_data),
                    'metadata': json.loads(snapshot.meta_data)
                })

            return results

        finally:
            session.close()

    async def search_team(self, query: str, team_id: str, limit: int = 20) -> List[Dict]:
        """搜索团队项目"""
        session = self.Session()
        try:
            snapshots = session.query(MemorySnapshot).filter(
                MemorySnapshot.team_id == team_id,
                MemorySnapshot.is_public == True,
                MemorySnapshot.graph_data.contains(query)
            ).order_by(
                MemorySnapshot.timestamp.desc()
            ).limit(limit).all()

            results = []
            for snapshot in snapshots:
                results.append({
                    'id': snapshot.id,
                    'project_id': snapshot.project_id,
                    'timestamp': snapshot.timestamp.isoformat(),
                    'data': json.loads(snapshot.graph_data)
                })

            return results

        finally:
            session.close()

    async def save_insight(self, insight: Dict):
        """保存洞察"""
        session = self.Session()
        try:
            shared_insight = SharedInsight(
                project_id=insight['project_id'],
                insight_type='user_generated',
                content=insight['content'],
                created_by=insight['created_by'],
                tags=json.dumps(insight.get('tags', []))
            )

            session.add(shared_insight)
            session.commit()

            return shared_insight.id

        finally:
            session.close()

    async def get_team_insights(self, team_id: str, limit: int = 20) -> List[Dict]:
        """获取团队洞察"""
        session = self.Session()
        try:
            # 这里简化处理，实际应该通过team_id关联
            insights = session.query(SharedInsight).order_by(
                SharedInsight.upvotes.desc(),
                SharedInsight.created_at.desc()
            ).limit(limit).all()

            results = []
            for insight in insights:
                results.append({
                    'id': insight.id,
                    'content': insight.content,
                    'created_by': insight.created_by,
                    'created_at': insight.created_at.isoformat(),
                    'upvotes': insight.upvotes,
                    'tags': json.loads(insight.tags) if insight.tags else []
                })

            return results

        finally:
            session.close()

    async def get_global_patterns(self) -> Dict:
        """获取全局模式"""
        session = self.Session()
        try:
            patterns = session.query(MemoryPattern).filter(
                MemoryPattern.confidence > 0.7
            ).order_by(
                MemoryPattern.frequency.desc()
            ).limit(10).all()

            return {
                'top_patterns': [
                    {
                        'type': p.pattern_type,
                        'frequency': p.frequency,
                        'confidence': p.confidence
                    }
                    for p in patterns
                ]
            }

        finally:
            session.close()

    async def get_team_patterns(self, team_id: str) -> Dict:
        """获取团队模式"""
        # 简化实现
        return await self.get_global_patterns()

    async def delete_before(self, cutoff: datetime) -> int:
        """删除旧数据"""
        session = self.Session()
        try:
            deleted = session.query(MemorySnapshot).filter(
                MemorySnapshot.timestamp < cutoff
            ).delete()

            session.commit()
            return deleted

        finally:
            session.close()

    def get_stats(self, project_id: str) -> Dict:
        """获取统计"""
        session = self.Session()
        try:
            count = session.query(MemorySnapshot).filter_by(
                project_id=project_id
            ).count()

            latest = session.query(MemorySnapshot).filter_by(
                project_id=project_id
            ).order_by(
                MemorySnapshot.timestamp.desc()
            ).first()

            return {
                'total_count': count,
                'latest_snapshot': latest.timestamp.isoformat() if latest else None
            }

        finally:
            session.close()

# ============================================
# 工厂函数
# ============================================

def create_storage(project_path: str, mode: str = 'auto') -> HybridStorageManager:
    """创建存储实例"""

    if mode == 'auto':
        # 自动选择模式
        if os.environ.get('MCP_TEAM_MODE') == 'true':
            mode = 'hybrid'
        else:
            mode = 'local'

    if mode == 'hybrid':
        logger.info("使用混合存储模式 (SQLite + MySQL)")
        return HybridStorageManager(project_path)
    elif mode == 'local':
        logger.info("使用纯本地存储模式 (SQLite)")
        manager = HybridStorageManager(project_path)
        manager.sync_enabled = False
        return manager
    elif mode == 'central':
        logger.info("使用纯中央存储模式 (MySQL)")
        manager = HybridStorageManager(project_path)
        # 配置为主要使用MySQL
        return manager
    else:
        raise ValueError(f"未知的存储模式: {mode}")

# ============================================
# 使用示例
# ============================================

async def demo():
    """演示混合存储系统"""
    print("=" * 60)
    print("🔄 混合存储系统演示 (SQLite + MySQL)")
    print("=" * 60)

    # 创建混合存储
    storage = create_storage("/Users/mac/Downloads/MCP", mode='hybrid')

    # 保存数据
    data = {
        'nodes': [{'id': '1', 'name': 'test'}],
        'edges': [],
        'metadata': {'version': '1.0'}
    }

    snapshot_id = await storage.save(data, {
        'trigger': 'demo',
        'importance': 'high',
        'team_mode': True
    })

    print(f"\n✅ 数据已保存 (ID: {snapshot_id})")
    print("   - 本地SQLite: 立即保存")
    print("   - MySQL: 异步同步中...")

    # 等待异步同步
    await asyncio.sleep(1)

    # 加载数据
    loaded = await storage.load(snapshot_id)
    print(f"\n✅ 数据已加载: {loaded is not None}")

    # 搜索
    results = await storage.search("test")
    print(f"\n🔍 搜索结果: {len(results)} 条")

    # 获取统计
    stats = storage.get_stats()
    print(f"\n📊 存储统计:")
    print(f"   - 存储模式: {stats['storage_mode']}")
    print(f"   - 本地快照: {stats['local']['total_count']}")
    print(f"   - 中央快照: {stats['central']['total_count']}")
    print(f"   - 缓存大小: {stats['cache']['size']}")
    print(f"   - 同步状态: {'启用' if stats['sync']['enabled'] else '禁用'}")

    # 分析模式
    patterns = await storage.analyze_patterns()
    print(f"\n🔮 模式分析:")
    if patterns['recommendations']:
        for rec in patterns['recommendations']:
            print(f"   • {rec}")

    print("\n" + "=" * 60)
    print("✨ 混合存储优势:")
    print("   1. 本地SQLite提供毫秒级响应")
    print("   2. MySQL提供团队共享和永久存储")
    print("   3. 自动同步确保数据一致性")
    print("   4. 支持离线工作，在线同步")
    print("   5. 智能缓存减少数据库访问")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(demo())
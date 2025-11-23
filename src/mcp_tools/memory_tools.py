"""
MCP记忆工具 - 自动保存和恢复项目记忆
整合图谱生成与记忆系统，实现项目的智能记忆管理
"""

import os
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from pathlib import Path

from src.mcp_core.services.project_memory_system import (
    ProjectMemorySystem,
    MemoryQuery,
    MemoryRecoveryAssistant
)
from src.mcp_core.common.logger import get_logger

logger = get_logger(__name__)

# ============================================
# MCP记忆工具
# ============================================

class MemoryTool:
    """MCP记忆工具基类"""
    name: str = ""
    description: str = ""
    parameters: Dict[str, Any] = {}

    async def execute(self, **kwargs) -> Dict[str, Any]:
        raise NotImplementedError

class SaveMemoryTool(MemoryTool):
    """保存项目记忆工具"""

    name = "save_project_memory"
    description = "创建项目的记忆快照，保存当前状态"

    parameters = {
        "type": "object",
        "properties": {
            "project_path": {
                "type": "string",
                "description": "项目路径，默认为当前目录"
            },
            "trigger": {
                "type": "string",
                "enum": ["manual", "auto", "commit", "error", "milestone"],
                "description": "触发类型"
            },
            "message": {
                "type": "string",
                "description": "快照说明信息"
            }
        },
        "required": []
    }

    def __init__(self):
        self.memory_system = ProjectMemorySystem()

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """执行记忆保存"""
        try:
            project_path = kwargs.get('project_path', os.getcwd())
            trigger = kwargs.get('trigger', 'manual')
            message = kwargs.get('message', '')

            # 创建快照
            snapshot = await self.memory_system.create_snapshot(
                project_path=project_path,
                trigger=trigger,
                context={"message": message} if message else None
            )

            return {
                "success": True,
                "snapshot_id": snapshot.id,
                "timestamp": snapshot.timestamp.isoformat(),
                "stats": {
                    "nodes": len(snapshot.graph_data.nodes),
                    "edges": len(snapshot.graph_data.edges),
                    "hash": snapshot.hash
                },
                "insights": snapshot.insights,
                "message": f"记忆快照已保存: {snapshot.id}"
            }

        except Exception as e:
            logger.error(f"保存记忆失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

class RecoverMemoryTool(MemoryTool):
    """恢复项目记忆工具"""

    name = "recover_project_memory"
    description = "从历史快照中恢复项目记忆"

    parameters = {
        "type": "object",
        "properties": {
            "project_path": {
                "type": "string",
                "description": "项目路径"
            },
            "query_type": {
                "type": "string",
                "enum": ["similarity", "time_range", "file_history", "pattern"],
                "description": "查询类型"
            },
            "file_path": {
                "type": "string",
                "description": "文件路径 (用于file_history查询)"
            },
            "days_ago": {
                "type": "integer",
                "description": "多少天前的记忆"
            }
        },
        "required": ["query_type"]
    }

    def __init__(self):
        self.memory_system = ProjectMemorySystem()

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """执行记忆恢复"""
        try:
            project_path = kwargs.get('project_path', os.getcwd())
            query_type = kwargs['query_type']

            # 构建查询
            query_params = {}

            if query_type == "file_history":
                file_path = kwargs.get('file_path')
                if not file_path:
                    return {
                        "success": False,
                        "error": "file_history查询需要提供file_path"
                    }
                query_params['file_path'] = file_path

            elif query_type == "time_range":
                days_ago = kwargs.get('days_ago', 7)
                end_time = datetime.now()
                start_time = end_time - timedelta(days=days_ago)
                query_params['time_range'] = (start_time, end_time)

            query = MemoryQuery(
                query_type=query_type,
                parameters=query_params
            )

            # 恢复记忆
            result = await self.memory_system.recover_memory(query, project_path)

            return {
                "success": result.success,
                "snapshots_found": len(result.snapshots),
                "confidence": result.confidence,
                "insights": result.insights,
                "suggestions": result.suggestions,
                "snapshots": [
                    {
                        "id": s.id,
                        "timestamp": s.timestamp.isoformat(),
                        "nodes": len(s.graph_data.nodes),
                        "edges": len(s.graph_data.edges)
                    }
                    for s in result.snapshots[:5]  # 最多返回5个
                ]
            }

        except Exception as e:
            logger.error(f"恢复记忆失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

class AnalyzeMemoryTool(MemoryTool):
    """分析项目记忆工具"""

    name = "analyze_project_memory"
    description = "分析项目的演化历史和趋势"

    parameters = {
        "type": "object",
        "properties": {
            "project_path": {
                "type": "string",
                "description": "项目路径"
            },
            "analysis_type": {
                "type": "string",
                "enum": ["growth", "complexity", "dependencies", "patterns"],
                "description": "分析类型"
            },
            "time_range_days": {
                "type": "integer",
                "description": "分析时间范围(天)"
            }
        },
        "required": ["analysis_type"]
    }

    def __init__(self):
        self.memory_system = ProjectMemorySystem()
        self.assistant = MemoryRecoveryAssistant(self.memory_system)

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """执行记忆分析"""
        try:
            project_path = kwargs.get('project_path', os.getcwd())
            analysis_type = kwargs['analysis_type']
            time_range_days = kwargs.get('time_range_days', 30)

            if analysis_type == "growth":
                # 分析增长
                time_range = (
                    datetime.now() - timedelta(days=time_range_days),
                    datetime.now()
                )
                growth = await self.assistant.explain_growth(
                    project_path,
                    time_range
                )
                return {
                    "success": True,
                    "analysis_type": "growth",
                    "result": growth
                }

            elif analysis_type == "complexity":
                # 分析复杂度变化
                snapshots = await self.memory_system.get_recent_snapshots(
                    project_path,
                    limit=10
                )
                complexities = []
                for snapshot in snapshots:
                    avg_complexity = sum(
                        n.complexity for n in snapshot.graph_data.nodes
                    ) / len(snapshot.graph_data.nodes)
                    complexities.append({
                        "timestamp": snapshot.timestamp.isoformat(),
                        "complexity": avg_complexity,
                        "node_count": len(snapshot.graph_data.nodes)
                    })

                return {
                    "success": True,
                    "analysis_type": "complexity",
                    "result": complexities
                }

            elif analysis_type == "dependencies":
                # 分析依赖变化
                snapshots = await self.memory_system.get_recent_snapshots(
                    project_path,
                    limit=10
                )
                dependencies = []
                for snapshot in snapshots:
                    density = len(snapshot.graph_data.edges) / max(
                        len(snapshot.graph_data.nodes) * (len(snapshot.graph_data.nodes) - 1),
                        1
                    )
                    dependencies.append({
                        "timestamp": snapshot.timestamp.isoformat(),
                        "edge_count": len(snapshot.graph_data.edges),
                        "density": density
                    })

                return {
                    "success": True,
                    "analysis_type": "dependencies",
                    "result": dependencies
                }

            elif analysis_type == "patterns":
                # 分析模式
                snapshots = await self.memory_system.get_recent_snapshots(
                    project_path,
                    limit=20
                )

                # 简单的模式识别
                patterns = {
                    "growth_trend": "increasing" if len(snapshots) > 1 and
                                   len(snapshots[0].graph_data.nodes) >
                                   len(snapshots[-1].graph_data.nodes) else "stable",
                    "snapshot_frequency": len(snapshots),
                    "common_triggers": self._analyze_triggers(snapshots)
                }

                return {
                    "success": True,
                    "analysis_type": "patterns",
                    "result": patterns
                }

            else:
                return {
                    "success": False,
                    "error": f"未知的分析类型: {analysis_type}"
                }

        except Exception as e:
            logger.error(f"分析记忆失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _analyze_triggers(self, snapshots: List) -> Dict[str, int]:
        """分析触发器分布"""
        triggers = {}
        for snapshot in snapshots:
            trigger = snapshot.metadata.get('trigger', 'unknown')
            triggers[trigger] = triggers.get(trigger, 0) + 1
        return triggers

class AutoMemoryMonitor:
    """自动记忆监控器"""

    def __init__(self, project_path: str):
        self.project_path = project_path
        self.memory_system = ProjectMemorySystem()
        self.monitoring = False
        self.last_snapshot_time = None
        self.file_watcher = None

    async def start_monitoring(
        self,
        interval_minutes: int = 60,
        watch_files: bool = True
    ):
        """开始监控"""
        self.monitoring = True
        logger.info(f"开始监控项目: {self.project_path}")

        # 创建初始快照
        await self.memory_system.create_snapshot(
            self.project_path,
            trigger="monitor_start"
        )
        self.last_snapshot_time = datetime.now()

        # 启动定时快照
        asyncio.create_task(self._periodic_snapshot(interval_minutes))

        # 启动文件监控
        if watch_files:
            asyncio.create_task(self._watch_files())

    async def stop_monitoring(self):
        """停止监控"""
        self.monitoring = False
        logger.info("停止监控")

        # 创建最终快照
        await self.memory_system.create_snapshot(
            self.project_path,
            trigger="monitor_stop"
        )

    async def _periodic_snapshot(self, interval_minutes: int):
        """定期快照"""
        while self.monitoring:
            await asyncio.sleep(interval_minutes * 60)
            if self.monitoring:
                await self.memory_system.create_snapshot(
                    self.project_path,
                    trigger="periodic"
                )
                self.last_snapshot_time = datetime.now()
                logger.info("创建定期快照")

    async def _watch_files(self):
        """监控文件变化"""
        # 简化版文件监控
        last_check = {}

        while self.monitoring:
            await asyncio.sleep(30)  # 每30秒检查一次

            changed_files = []
            for root, dirs, files in os.walk(self.project_path):
                # 跳过特定目录
                if any(skip in root for skip in ['.git', '__pycache__', 'node_modules']):
                    continue

                for file in files:
                    if file.endswith(('.py', '.js', '.ts', '.java')):
                        file_path = os.path.join(root, file)
                        try:
                            mtime = os.path.getmtime(file_path)
                            if file_path in last_check:
                                if mtime > last_check[file_path]:
                                    changed_files.append(file_path)
                            last_check[file_path] = mtime
                        except Exception:
                            pass

            # 如果有大量文件变化，创建快照
            if len(changed_files) > 10:
                logger.info(f"检测到 {len(changed_files)} 个文件变化，创建快照")
                await self.memory_system.create_snapshot(
                    self.project_path,
                    trigger="file_changes",
                    context={"changed_files": changed_files[:20]}  # 最多记录20个
                )
                self.last_snapshot_time = datetime.now()

# ============================================
# Git集成
# ============================================

class GitMemoryIntegration:
    """Git钩子集成 - 自动在提交时保存记忆"""

    @staticmethod
    def create_git_hooks(project_path: str):
        """创建Git钩子"""
        hooks_dir = Path(project_path) / ".git" / "hooks"
        if not hooks_dir.exists():
            logger.error("不是Git仓库")
            return False

        # 创建post-commit钩子
        post_commit_hook = hooks_dir / "post-commit"
        hook_content = """#!/bin/bash
# MCP记忆系统 - 自动保存提交快照

python3 -c "
import asyncio
from src.mcp_tools.memory_tools import SaveMemoryTool

async def save():
    tool = SaveMemoryTool()
    result = await tool.execute(
        trigger='commit',
        message='Git commit snapshot'
    )
    print(f'记忆快照已保存: {result.get(\"snapshot_id\")}')

asyncio.run(save())
" 2>/dev/null || true
"""

        with open(post_commit_hook, 'w') as f:
            f.write(hook_content)

        # 设置执行权限
        os.chmod(post_commit_hook, 0o755)

        logger.info("Git钩子已创建")
        return True

# ============================================
# 注册工具到MCP
# ============================================

def register_memory_tools():
    """注册记忆工具到MCP"""
    return [
        SaveMemoryTool(),
        RecoverMemoryTool(),
        AnalyzeMemoryTool()
    ]

# ============================================
# 测试和演示
# ============================================

async def demo():
    """演示记忆工具的使用"""
    print("=" * 60)
    print("🧠 MCP记忆工具演示")
    print("=" * 60)

    # 1. 保存记忆
    print("\n1. 保存项目记忆...")
    save_tool = SaveMemoryTool()
    result = await save_tool.execute(
        project_path="/Users/mac/Downloads/MCP",
        trigger="demo",
        message="演示记忆保存"
    )
    print(f"   结果: {result}")

    # 2. 恢复记忆
    print("\n2. 恢复项目记忆...")
    recover_tool = RecoverMemoryTool()
    result = await recover_tool.execute(
        project_path="/Users/mac/Downloads/MCP",
        query_type="similarity"
    )
    print(f"   找到快照: {result.get('snapshots_found')}")
    print(f"   置信度: {result.get('confidence')}")

    # 3. 分析记忆
    print("\n3. 分析项目记忆...")
    analyze_tool = AnalyzeMemoryTool()
    result = await analyze_tool.execute(
        project_path="/Users/mac/Downloads/MCP",
        analysis_type="complexity"
    )
    print(f"   分析结果: {result.get('result')}")

    # 4. 自动监控
    print("\n4. 启动自动监控...")
    monitor = AutoMemoryMonitor("/Users/mac/Downloads/MCP")
    await monitor.start_monitoring(interval_minutes=60, watch_files=False)
    print("   ✅ 监控已启动")

    # 等待几秒后停止
    await asyncio.sleep(3)
    await monitor.stop_monitoring()
    print("   ✅ 监控已停止")

    print("\n" + "=" * 60)
    print("💡 MCP记忆工具功能:")
    print("   1. save_project_memory - 保存记忆快照")
    print("   2. recover_project_memory - 恢复历史记忆")
    print("   3. analyze_project_memory - 分析演化趋势")
    print("   4. 自动监控和Git集成")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(demo())
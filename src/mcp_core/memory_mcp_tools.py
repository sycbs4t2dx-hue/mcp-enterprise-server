#!/usr/bin/env python3
"""
混合记忆存储 - MCP工具定义

提供MCP工具供AI使用，管理项目记忆、快照、搜索和团队协作
基于HybridStorageManager实现本地+中央存储
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime

from .services.memory_hybrid_integration import (
    IntegratedMemoryManager,
    create_integrated_manager
)
from .common.logger import get_logger

logger = get_logger(__name__)


# ==================== MCP工具定义 ====================

MCP_TOOLS = [
    {
        "name": "create_memory_snapshot",
        "description": "创建项目记忆快照。分析项目结构，保存到本地SQLite，可选同步到团队MySQL。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_path": {
                    "type": "string",
                    "description": "项目路径"
                },
                "trigger": {
                    "type": "string",
                    "enum": ["manual", "auto", "milestone", "commit", "release"],
                    "description": "触发类型",
                    "default": "manual"
                },
                "importance": {
                    "type": "string",
                    "enum": ["low", "normal", "high"],
                    "description": "重要性级别",
                    "default": "normal"
                },
                "team_mode": {
                    "type": "boolean",
                    "description": "是否同步到团队存储",
                    "default": False
                },
                "context": {
                    "type": "object",
                    "description": "额外上下文信息（可选）",
                    "additionalProperties": True
                }
            },
            "required": ["project_path"]
        }
    },
    {
        "name": "search_memories",
        "description": "搜索项目记忆。支持本地、中央和团队多源并行搜索。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_path": {
                    "type": "string",
                    "description": "项目路径"
                },
                "query": {
                    "type": "string",
                    "description": "搜索关键词"
                },
                "search_local": {
                    "type": "boolean",
                    "description": "是否搜索本地存储",
                    "default": True
                },
                "search_central": {
                    "type": "boolean",
                    "description": "是否搜索中央存储",
                    "default": True
                },
                "search_team": {
                    "type": "boolean",
                    "description": "是否搜索团队项目",
                    "default": False
                },
                "limit": {
                    "type": "integer",
                    "description": "返回结果数量限制",
                    "default": 10
                }
            },
            "required": ["project_path", "query"]
        }
    },
    {
        "name": "recover_memory_by_similarity",
        "description": "基于相似度恢复记忆。找到与当前项目状态最相似的历史快照。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_path": {
                    "type": "string",
                    "description": "项目路径"
                },
                "top_k": {
                    "type": "integer",
                    "description": "返回最相似的K个快照",
                    "default": 5
                }
            },
            "required": ["project_path"]
        }
    },
    {
        "name": "get_file_memory_history",
        "description": "获取特定文件的记忆历史。追踪文件在不同快照中的演变。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_path": {
                    "type": "string",
                    "description": "项目路径"
                },
                "file_path": {
                    "type": "string",
                    "description": "文件相对路径"
                }
            },
            "required": ["project_path", "file_path"]
        }
    },
    {
        "name": "sync_memories_to_team",
        "description": "同步本地记忆到团队中央存储。将未同步的快照上传到MySQL。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_path": {
                    "type": "string",
                    "description": "项目路径"
                }
            },
            "required": ["project_path"]
        }
    },
    {
        "name": "share_insight",
        "description": "分享洞察到团队。将有价值的发现分享给团队成员。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_path": {
                    "type": "string",
                    "description": "项目路径"
                },
                "content": {
                    "type": "string",
                    "description": "洞察内容"
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "标签列表（可选）"
                }
            },
            "required": ["project_path", "content"]
        }
    },
    {
        "name": "get_team_insights",
        "description": "获取团队洞察。查看其他团队成员分享的洞察。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_path": {
                    "type": "string",
                    "description": "项目路径"
                },
                "limit": {
                    "type": "integer",
                    "description": "返回数量限制",
                    "default": 20
                }
            },
            "required": ["project_path"]
        }
    },
    {
        "name": "analyze_memory_patterns",
        "description": "分析记忆模式。识别本地、全局和团队的代码模式，生成改进建议。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_path": {
                    "type": "string",
                    "description": "项目路径"
                }
            },
            "required": ["project_path"]
        }
    },
    {
        "name": "get_memory_statistics",
        "description": "获取记忆系统统计信息。包括快照数、搜索统计、同步状态等。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_path": {
                    "type": "string",
                    "description": "项目路径"
                }
            },
            "required": ["project_path"]
        }
    },
    {
        "name": "cleanup_old_memories",
        "description": "清理旧的记忆快照。删除指定天数前的快照以释放空间。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_path": {
                    "type": "string",
                    "description": "项目路径"
                },
                "days": {
                    "type": "integer",
                    "description": "保留天数（删除此之前的快照）",
                    "default": 30
                }
            },
            "required": ["project_path"]
        }
    }
]


# ==================== 工具实现 ====================

class MemoryMCPTools:
    """混合记忆存储MCP工具实现"""

    def __init__(self):
        """初始化MCP工具"""
        # 管理器缓存 (按项目路径缓存)
        self._managers: Dict[str, IntegratedMemoryManager] = {}

    def _get_manager(self, project_path: str) -> IntegratedMemoryManager:
        """获取或创建项目的记忆管理器"""
        if project_path not in self._managers:
            self._managers[project_path] = create_integrated_manager(
                project_path=project_path,
                storage_mode='hybrid'
            )
        return self._managers[project_path]

    async def create_memory_snapshot(
        self,
        project_path: str,
        trigger: str = "manual",
        importance: str = "normal",
        team_mode: bool = False,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """创建记忆快照"""
        try:
            manager = self._get_manager(project_path)

            sync_options = {
                'importance': importance,
                'team_mode': team_mode
            }

            result = await manager.create_snapshot(
                trigger=trigger,
                context=context,
                sync_options=sync_options
            )

            if result['success']:
                return {
                    "success": True,
                    "snapshot_id": result['snapshot_id'],
                    "node_count": result['node_count'],
                    "edge_count": result['edge_count'],
                    "insights": result['insights'],
                    "synced": result['storage']['synced'],
                    "message": f"快照创建成功: {result['snapshot_id']}"
                }
            else:
                return {
                    "success": False,
                    "error": result.get('error', '未知错误')
                }

        except Exception as e:
            logger.error(f"创建快照失败: {e}")
            return {"success": False, "error": str(e)}

    async def search_memories(
        self,
        project_path: str,
        query: str,
        search_local: bool = True,
        search_central: bool = True,
        search_team: bool = False,
        limit: int = 10
    ) -> Dict[str, Any]:
        """搜索记忆"""
        try:
            manager = self._get_manager(project_path)

            search_options = {
                'local': search_local,
                'central': search_central,
                'team': search_team,
                'limit': limit
            }

            results = await manager.search_memories(query, search_options)

            return {
                "success": True,
                "query": query,
                "total": len(results),
                "results": [
                    {
                        "id": r.get('id'),
                        "timestamp": r.get('timestamp'),
                        "score": r.get('_score', 0),
                        "age_category": r.get('age_category', 'unknown'),
                        "metadata": r.get('metadata', {})
                    }
                    for r in results[:limit]
                ]
            }

        except Exception as e:
            logger.error(f"搜索记忆失败: {e}")
            return {"success": False, "error": str(e)}

    async def recover_memory_by_similarity(
        self,
        project_path: str,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """基于相似度恢复记忆"""
        try:
            manager = self._get_manager(project_path)

            result = await manager.recover_memory(
                query_type='similarity',
                parameters={'top_k': top_k}
            )

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
                        "node_count": len(s.graph_data.nodes),
                        "edge_count": len(s.graph_data.edges)
                    }
                    for s in result.snapshots[:top_k]
                ]
            }

        except Exception as e:
            logger.error(f"相似度恢复失败: {e}")
            return {"success": False, "error": str(e)}

    async def get_file_memory_history(
        self,
        project_path: str,
        file_path: str
    ) -> Dict[str, Any]:
        """获取文件记忆历史"""
        try:
            manager = self._get_manager(project_path)

            result = await manager.get_file_history(file_path)

            return {
                "success": result['success'],
                "file_path": file_path,
                "snapshots_count": result.get('snapshots', 0),
                "insights": result.get('insights', []),
                "suggestions": result.get('suggestions', [])
            }

        except Exception as e:
            logger.error(f"获取文件历史失败: {e}")
            return {"success": False, "error": str(e)}

    async def sync_memories_to_team(
        self,
        project_path: str
    ) -> Dict[str, Any]:
        """同步记忆到团队"""
        try:
            manager = self._get_manager(project_path)
            result = await manager.sync_to_team()

            return {
                "success": result['success'],
                "synced_count": result.get('synced_count', 0),
                "message": result.get('message', '')
            }

        except Exception as e:
            logger.error(f"同步到团队失败: {e}")
            return {"success": False, "error": str(e)}

    async def share_insight(
        self,
        project_path: str,
        content: str,
        tags: List[str] = None
    ) -> Dict[str, Any]:
        """分享洞察"""
        try:
            manager = self._get_manager(project_path)
            result = await manager.share_insight(content, tags)

            return {
                "success": result['success'],
                "insight_id": result.get('insight_id'),
                "message": result.get('message', '')
            }

        except Exception as e:
            logger.error(f"分享洞察失败: {e}")
            return {"success": False, "error": str(e)}

    async def get_team_insights(
        self,
        project_path: str,
        limit: int = 20
    ) -> Dict[str, Any]:
        """获取团队洞察"""
        try:
            manager = self._get_manager(project_path)
            insights = await manager.get_team_insights(limit)

            return {
                "success": True,
                "total": len(insights),
                "insights": insights
            }

        except Exception as e:
            logger.error(f"获取团队洞察失败: {e}")
            return {"success": False, "error": str(e)}

    async def analyze_memory_patterns(
        self,
        project_path: str
    ) -> Dict[str, Any]:
        """分析记忆模式"""
        try:
            manager = self._get_manager(project_path)
            result = await manager.analyze_patterns()

            if result['success']:
                return {
                    "success": True,
                    "local_patterns": result['patterns'].get('local', {}),
                    "global_patterns": result['patterns'].get('global', {}),
                    "team_patterns": result['patterns'].get('team', {}),
                    "recommendations": result['recommendations']
                }
            else:
                return {
                    "success": False,
                    "error": result.get('error', '分析失败')
                }

        except Exception as e:
            logger.error(f"分析模式失败: {e}")
            return {"success": False, "error": str(e)}

    async def get_memory_statistics(
        self,
        project_path: str
    ) -> Dict[str, Any]:
        """获取记忆统计"""
        try:
            manager = self._get_manager(project_path)
            stats = manager.get_statistics()

            return {
                "success": True,
                "project_path": stats['project_path'],
                "storage_mode": stats['storage']['storage_mode'],
                "local_stats": stats['storage']['local'],
                "central_stats": stats['storage']['central'],
                "cache_stats": stats['storage']['cache'],
                "sync_stats": stats['storage']['sync'],
                "manager_stats": stats['integrated_manager']
            }

        except Exception as e:
            logger.error(f"获取统计失败: {e}")
            return {"success": False, "error": str(e)}

    async def cleanup_old_memories(
        self,
        project_path: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """清理旧记忆"""
        try:
            manager = self._get_manager(project_path)
            result = await manager.cleanup(days)

            return {
                "success": result['success'],
                "deleted_count": result.get('deleted_count', 0),
                "message": result.get('message', '')
            }

        except Exception as e:
            logger.error(f"清理失败: {e}")
            return {"success": False, "error": str(e)}


# ==================== 工具调度器 ====================

class MemoryToolDispatcher:
    """MCP工具调度器 - 将工具名称映射到实现"""

    def __init__(self):
        self.tools = MemoryMCPTools()
        self._method_map = {
            'create_memory_snapshot': self.tools.create_memory_snapshot,
            'search_memories': self.tools.search_memories,
            'recover_memory_by_similarity': self.tools.recover_memory_by_similarity,
            'get_file_memory_history': self.tools.get_file_memory_history,
            'sync_memories_to_team': self.tools.sync_memories_to_team,
            'share_insight': self.tools.share_insight,
            'get_team_insights': self.tools.get_team_insights,
            'analyze_memory_patterns': self.tools.analyze_memory_patterns,
            'get_memory_statistics': self.tools.get_memory_statistics,
            'cleanup_old_memories': self.tools.cleanup_old_memories
        }

    async def dispatch(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        调度工具执行

        Args:
            tool_name: 工具名称
            arguments: 工具参数

        Returns:
            执行结果
        """
        if tool_name not in self._method_map:
            return {
                "success": False,
                "error": f"未知工具: {tool_name}"
            }

        method = self._method_map[tool_name]
        return await method(**arguments)


# ==================== 单例实例 ====================

_dispatcher_instance: Optional[MemoryToolDispatcher] = None


def get_memory_tool_dispatcher() -> MemoryToolDispatcher:
    """获取工具调度器单例"""
    global _dispatcher_instance
    if _dispatcher_instance is None:
        _dispatcher_instance = MemoryToolDispatcher()
    return _dispatcher_instance


# ==================== 使用示例 ====================

async def demo():
    """演示MCP工具使用"""
    print("=" * 60)
    print("混合记忆存储 MCP工具演示")
    print("=" * 60)

    dispatcher = get_memory_tool_dispatcher()
    project_path = "/Users/mac/Downloads/MCP"

    # 1. 创建快照
    print("\n1. 创建记忆快照...")
    result = await dispatcher.dispatch('create_memory_snapshot', {
        'project_path': project_path,
        'trigger': 'demo',
        'importance': 'high',
        'team_mode': True,
        'context': {'reason': 'MCP工具演示'}
    })
    print(f"   {result}")

    # 2. 搜索记忆
    print("\n2. 搜索记忆...")
    result = await dispatcher.dispatch('search_memories', {
        'project_path': project_path,
        'query': 'analyzer',
        'search_local': True,
        'search_central': True,
        'limit': 5
    })
    print(f"   找到 {result.get('total', 0)} 个结果")

    # 3. 获取统计
    print("\n3. 获取统计...")
    result = await dispatcher.dispatch('get_memory_statistics', {
        'project_path': project_path
    })
    if result['success']:
        print(f"   存储模式: {result['storage_mode']}")
        print(f"   本地快照: {result['local_stats'].get('total_count', 0)}")

    # 4. 分析模式
    print("\n4. 分析模式...")
    result = await dispatcher.dispatch('analyze_memory_patterns', {
        'project_path': project_path
    })
    if result['success']:
        print("   推荐:")
        for rec in result.get('recommendations', [])[:3]:
            print(f"   - {rec}")

    print("\n" + "=" * 60)
    print("MCP工具提供的功能:")
    for tool in MCP_TOOLS:
        print(f"- {tool['name']}: {tool['description'][:50]}...")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(demo())

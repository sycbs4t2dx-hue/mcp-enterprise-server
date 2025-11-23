#!/usr/bin/env python3
"""
混合记忆存储系统 - 综合集成测试

测试HybridStorageManager + ProjectMemorySystem + MCP Tools的完整集成
"""

import os
import sys
import asyncio
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.mcp_core.services.memory_hybrid_integration import (
    create_integrated_manager,
    IntegratedMemoryManager
)
from src.mcp_core.memory_mcp_tools import (
    get_memory_tool_dispatcher,
    MCP_TOOLS
)
from src.mcp_core.common.logger import get_logger

logger = get_logger(__name__)


class IntegrationTester:
    """集成测试器"""

    def __init__(self, project_path: str):
        self.project_path = project_path
        self.manager: IntegratedMemoryManager = None
        self.dispatcher = None
        self.test_results = []
        self.start_time = None

    async def setup(self):
        """设置测试环境"""
        print("\n" + "=" * 70)
        print("混合记忆存储系统 - 综合集成测试")
        print("=" * 70)

        self.start_time = time.time()

        # 创建集成管理器
        print("\n1. 初始化集成管理器...")
        self.manager = create_integrated_manager(
            project_path=self.project_path,
            storage_mode='hybrid'
        )
        print("   ✓ 集成管理器创建成功")

        # 创建MCP工具调度器
        print("\n2. 初始化MCP工具调度器...")
        self.dispatcher = get_memory_tool_dispatcher()
        print(f"   ✓ 注册了 {len(MCP_TOOLS)} 个MCP工具")

    async def test_snapshot_creation(self):
        """测试快照创建"""
        print("\n" + "-" * 70)
        print("测试 1: 快照创建")
        print("-" * 70)

        try:
            # 测试手动快照
            print("\n  [1.1] 创建手动快照...")
            result = await self.manager.create_snapshot(
                trigger='manual',
                context={'test': 'integration_test'},
                sync_options={
                    'importance': 'high',
                    'team_mode': False
                }
            )

            assert result['success'], "快照创建失败"
            assert 'snapshot_id' in result, "缺少快照ID"
            assert result['node_count'] > 0, "节点数为0"

            print(f"      ✓ 快照ID: {result['snapshot_id']}")
            print(f"      ✓ 节点数: {result['node_count']}")
            print(f"      ✓ 边数: {result['edge_count']}")
            print(f"      ✓ 洞察: {len(result['insights'])} 条")

            self.test_results.append(('快照创建', True, result['snapshot_id']))

            # 测试通过MCP工具创建快照
            print("\n  [1.2] 通过MCP工具创建快照...")
            result = await self.dispatcher.dispatch('create_memory_snapshot', {
                'project_path': self.project_path,
                'trigger': 'auto',
                'importance': 'normal',
                'team_mode': False
            })

            assert result['success'], "MCP工具创建快照失败"
            print(f"      ✓ MCP快照ID: {result['snapshot_id']}")

            self.test_results.append(('MCP工具快照', True, result['snapshot_id']))

        except Exception as e:
            print(f"      ✗ 测试失败: {e}")
            self.test_results.append(('快照创建', False, str(e)))

    async def test_memory_search(self):
        """测试记忆搜索"""
        print("\n" + "-" * 70)
        print("测试 2: 记忆搜索")
        print("-" * 70)

        try:
            # 直接搜索
            print("\n  [2.1] 直接搜索记忆...")
            results = await self.manager.search_memories(
                query='services',
                search_options={
                    'local': True,
                    'central': False,
                    'limit': 5
                }
            )

            print(f"      ✓ 找到 {len(results)} 个结果")
            if results:
                print(f"      ✓ 第一个结果: {results[0].get('id')}")

            self.test_results.append(('直接搜索', True, len(results)))

            # MCP工具搜索
            print("\n  [2.2] 通过MCP工具搜索...")
            result = await self.dispatcher.dispatch('search_memories', {
                'project_path': self.project_path,
                'query': 'mcp',
                'search_local': True,
                'limit': 10
            })

            assert result['success'], "MCP搜索失败"
            print(f"      ✓ MCP搜索到 {result['total']} 个结果")

            self.test_results.append(('MCP搜索', True, result['total']))

        except Exception as e:
            print(f"      ✗ 测试失败: {e}")
            self.test_results.append(('记忆搜索', False, str(e)))

    async def test_memory_recovery(self):
        """测试记忆恢复"""
        print("\n" + "-" * 70)
        print("测试 3: 记忆恢复")
        print("-" * 70)

        try:
            # 相似度恢复
            print("\n  [3.1] 相似度恢复...")
            result = await self.dispatcher.dispatch('recover_memory_by_similarity', {
                'project_path': self.project_path,
                'top_k': 3
            })

            assert result['success'], "相似度恢复失败"
            print(f"      ✓ 找到 {result['snapshots_found']} 个相似快照")
            print(f"      ✓ 置信度: {result['confidence']:.2f}")
            print(f"      ✓ 洞察: {len(result['insights'])} 条")

            self.test_results.append(('相似度恢复', True, result['snapshots_found']))

            # 文件历史
            print("\n  [3.2] 文件历史恢复...")
            result = await self.dispatcher.dispatch('get_file_memory_history', {
                'project_path': self.project_path,
                'file_path': 'src/mcp_core/services/memory_service.py'
            })

            print(f"      ✓ 文件历史: {result.get('snapshots_count', 0)} 个快照")

            self.test_results.append(('文件历史', True, result.get('snapshots_count', 0)))

        except Exception as e:
            print(f"      ✗ 测试失败: {e}")
            self.test_results.append(('记忆恢复', False, str(e)))

    async def test_pattern_analysis(self):
        """测试模式分析"""
        print("\n" + "-" * 70)
        print("测试 4: 模式分析")
        print("-" * 70)

        try:
            print("\n  [4.1] 分析项目模式...")
            result = await self.dispatcher.dispatch('analyze_memory_patterns', {
                'project_path': self.project_path
            })

            assert result['success'], "模式分析失败"
            print(f"      ✓ 本地模式: {result.get('local_patterns', {})}")
            print(f"      ✓ 推荐数: {len(result.get('recommendations', []))}")

            if result.get('recommendations'):
                print("      ✓ 前3条推荐:")
                for i, rec in enumerate(result['recommendations'][:3], 1):
                    print(f"         {i}. {rec}")

            self.test_results.append(('模式分析', True, len(result.get('recommendations', []))))

        except Exception as e:
            print(f"      ✗ 测试失败: {e}")
            self.test_results.append(('模式分析', False, str(e)))

    async def test_statistics(self):
        """测试统计功能"""
        print("\n" + "-" * 70)
        print("测试 5: 统计信息")
        print("-" * 70)

        try:
            print("\n  [5.1] 获取综合统计...")
            stats = self.manager.get_statistics()

            print(f"      ✓ 存储模式: {stats['storage']['storage_mode']}")
            print(f"      ✓ 本地快照: {stats['storage']['local']['total_count']}")
            print(f"      ✓ 中央快照: {stats['storage']['central']['total_count']}")
            print(f"      ✓ 缓存大小: {stats['storage']['cache']['size']}")
            print(f"      ✓ 同步状态: {'启用' if stats['storage']['sync']['enabled'] else '禁用'}")

            self.test_results.append(('综合统计', True, stats['storage']['local']['total_count']))

            # MCP工具统计
            print("\n  [5.2] 通过MCP工具获取统计...")
            result = await self.dispatcher.dispatch('get_memory_statistics', {
                'project_path': self.project_path
            })

            assert result['success'], "MCP统计失败"
            print(f"      ✓ 管理器快照数: {result['manager_stats']['total_snapshots']}")
            print(f"      ✓ 搜索次数: {result['manager_stats']['total_searches']}")

            self.test_results.append(('MCP统计', True, result['manager_stats']['total_snapshots']))

        except Exception as e:
            print(f"      ✗ 测试失败: {e}")
            self.test_results.append(('统计功能', False, str(e)))

    async def test_team_features(self):
        """测试团队协作功能"""
        print("\n" + "-" * 70)
        print("测试 6: 团队协作")
        print("-" * 70)

        try:
            # 分享洞察
            print("\n  [6.1] 分享洞察...")
            result = await self.dispatcher.dispatch('share_insight', {
                'project_path': self.project_path,
                'content': '集成测试发现的洞察：混合存储系统运行良好',
                'tags': ['test', 'integration', 'hybrid-storage']
            })

            if result['success']:
                print(f"      ✓ 洞察已分享: ID {result.get('insight_id')}")
                self.test_results.append(('分享洞察', True, result.get('insight_id')))
            else:
                print(f"      ! 分享可能失败（需要MySQL）: {result.get('error')}")
                self.test_results.append(('分享洞察', False, '需要MySQL'))

            # 获取团队洞察
            print("\n  [6.2] 获取团队洞察...")
            result = await self.dispatcher.dispatch('get_team_insights', {
                'project_path': self.project_path,
                'limit': 10
            })

            if result['success']:
                print(f"      ✓ 团队洞察数: {result['total']}")
                self.test_results.append(('团队洞察', True, result['total']))
            else:
                print(f"      ! 获取可能失败（需要MySQL）: {result.get('error')}")
                self.test_results.append(('团队洞察', False, '需要MySQL'))

        except Exception as e:
            print(f"      ✗ 测试失败: {e}")
            self.test_results.append(('团队协作', False, str(e)))

    async def test_mcp_tools_coverage(self):
        """测试MCP工具覆盖率"""
        print("\n" + "-" * 70)
        print("测试 7: MCP工具覆盖")
        print("-" * 70)

        print(f"\n  已注册的MCP工具 ({len(MCP_TOOLS)} 个):")
        for i, tool in enumerate(MCP_TOOLS, 1):
            print(f"    {i}. {tool['name']}")
            print(f"       - {tool['description'][:60]}...")

        tested_tools = {
            'create_memory_snapshot',
            'search_memories',
            'recover_memory_by_similarity',
            'get_file_memory_history',
            'analyze_memory_patterns',
            'get_memory_statistics',
            'share_insight',
            'get_team_insights'
        }

        all_tools = {tool['name'] for tool in MCP_TOOLS}
        untested = all_tools - tested_tools

        print(f"\n  已测试: {len(tested_tools)} / {len(all_tools)}")
        if untested:
            print(f"  未测试: {', '.join(untested)}")

        coverage = len(tested_tools) / len(all_tools) * 100
        print(f"  覆盖率: {coverage:.1f}%")

        self.test_results.append(('工具覆盖', coverage >= 70, f"{coverage:.1f}%"))

    def print_summary(self):
        """打印测试总结"""
        duration = time.time() - self.start_time

        print("\n" + "=" * 70)
        print("测试总结")
        print("=" * 70)

        passed = sum(1 for _, success, _ in self.test_results if success)
        total = len(self.test_results)

        print(f"\n总测试数: {total}")
        print(f"通过: {passed}")
        print(f"失败: {total - passed}")
        print(f"成功率: {passed/total*100:.1f}%")
        print(f"耗时: {duration:.2f}秒")

        print("\n详细结果:")
        for i, (name, success, detail) in enumerate(self.test_results, 1):
            status = "✓" if success else "✗"
            print(f"  {i}. {status} {name}: {detail}")

        print("\n" + "=" * 70)
        print("集成测试完成")
        print("=" * 70)

        # 返回是否所有测试都通过
        return passed == total


async def main():
    """主测试函数"""
    # 项目路径
    project_path = "/Users/mac/Downloads/MCP"

    # 确保路径存在
    if not os.path.exists(project_path):
        print(f"错误: 项目路径不存在: {project_path}")
        return False

    # 创建测试器
    tester = IntegrationTester(project_path)

    try:
        # 设置
        await tester.setup()

        # 运行所有测试
        await tester.test_snapshot_creation()
        await tester.test_memory_search()
        await tester.test_memory_recovery()
        await tester.test_pattern_analysis()
        await tester.test_statistics()
        await tester.test_team_features()
        await tester.test_mcp_tools_coverage()

        # 打印总结
        all_passed = tester.print_summary()

        return all_passed

    except Exception as e:
        print(f"\n错误: 测试执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # 运行测试
    success = asyncio.run(main())

    # 退出码
    sys.exit(0 if success else 1)

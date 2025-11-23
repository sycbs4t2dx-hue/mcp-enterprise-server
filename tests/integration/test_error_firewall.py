#!/usr/bin/env python3
"""
错误防火墙系统测试脚本
测试核心服务功能和MCP工具
"""

import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.mcp_core.services.error_firewall_service import ErrorFirewallService
from src.mcp_core.api.v1.tools.error_firewall import (
    error_firewall_record,
    error_firewall_check,
    error_firewall_query,
    error_firewall_stats
)


def get_db_session():
    """获取数据库会话"""
    db_password = os.getenv("DB_PASSWORD", "Wxwy.2025@#")
    # URL编码密码中的特殊字符
    encoded_password = db_password.replace("@", "%40").replace("#", "%23")
    db_url = f"mysql+pymysql://root:{encoded_password}@localhost:3306/mcp_db?charset=utf8mb4"

    engine = create_engine(db_url, echo=False)
    Session = sessionmaker(bind=engine)
    return Session()


async def test_record_error(db_session):
    """测试错误记录功能"""
    print("\n" + "=" * 60)
    print("📝 测试1: 记录错误")
    print("=" * 60)

    result = await error_firewall_record(
        error_type="ios_build",
        error_scene="测试错误 - iOS编译时选择不存在的模拟器",
        error_pattern={
            "device_name": "iPhone 15",
            "os_version": "17.0",
            "operation": "build",
            "xcode_version": "15.0"
        },
        error_message="Error: Unable to boot device 'iPhone 15' (17.0) in current state: Shutdown",
        solution="请使用以下可用模拟器: iPhone 15 Pro (17.2), iPhone 14 (16.4). 或运行 'xcrun simctl list devices' 查看所有可用设备",
        solution_confidence=0.95,
        block_level="block",
        auto_fix=False,
        db_session=db_session
    )

    print(f"结果: {result}")

    if result["success"]:
        print(f"✅ 错误记录成功!")
        print(f"   错误ID: {result.get('error_id')}")
        print(f"   是否新记录: {result.get('is_new')}")
    else:
        print(f"❌ 错误记录失败: {result.get('error')}")

    return result


async def test_check_operation(db_session):
    """测试操作检查功能"""
    print("\n" + "=" * 60)
    print("🔍 测试2: 检查操作 (应该被拦截)")
    print("=" * 60)

    # 测试1: 应该被拦截
    result = await error_firewall_check(
        operation_type="ios_build",
        operation_params={
            "device_name": "iPhone 15",
            "os_version": "17.0"
        },
        session_id="test-session-001",
        db_session=db_session
    )

    print(f"结果: {result}")

    if result.get("should_block"):
        print(f"✅ 操作被正确拦截!")
        print(f"   风险等级: {result.get('risk_level')}")
        print(f"   匹配置信度: {result.get('matched_error', {}).get('match_confidence')}")
        print(f"   解决方案: {result.get('solution')}")
    elif result.get("should_warn"):
        print(f"⚠️ 操作收到警告")
    else:
        print(f"ℹ️ 操作通过检查")

    print("\n" + "-" * 60)
    print("🔍 测试3: 检查操作 (不应该被拦截)")
    print("-" * 60)

    # 测试2: 不应该被拦截
    result2 = await error_firewall_check(
        operation_type="ios_build",
        operation_params={
            "device_name": "iPhone 15 Pro",
            "os_version": "17.2"
        },
        session_id="test-session-002",
        db_session=db_session
    )

    print(f"结果: {result2}")

    if not result2.get("should_block"):
        print(f"✅ 正确: 操作未被拦截")
        print(f"   风险等级: {result2.get('risk_level')}")
    else:
        print(f"⚠️ 意外: 操作被拦截")

    return result


async def test_query_errors(db_session):
    """测试错误查询功能"""
    print("\n" + "=" * 60)
    print("📋 测试4: 查询错误记录")
    print("=" * 60)

    result = await error_firewall_query(
        error_type="ios_build",
        limit=10,
        db_session=db_session
    )

    print(f"查询到 {result.get('count', 0)} 条记录")

    for error in result.get("errors", []):
        print(f"\n  📌 {error.get('error_scene')}")
        print(f"     类型: {error.get('error_type')}")
        print(f"     拦截级别: {error.get('block_level')}")
        print(f"     发生次数: {error.get('occurrences')}")
        print(f"     拦截次数: {error.get('blocks')}")

    return result


async def test_get_stats(db_session):
    """测试统计功能"""
    print("\n" + "=" * 60)
    print("📊 测试5: 获取统计信息")
    print("=" * 60)

    result = await error_firewall_stats(db_session=db_session)

    if result.get("success"):
        print(f"✅ 统计信息获取成功!")
        print(f"\n  总错误数: {result.get('total_errors')}")
        print(f"  总发生次数: {result.get('total_occurrences')}")
        print(f"  总拦截次数: {result.get('total_blocks')}")
        print(f"  拦截率: {result.get('block_rate')}%")
        print(f"  平均置信度: {result.get('avg_confidence')}")
        print(f"  可自动修复: {result.get('auto_fixable')}")

        print(f"\n  按类型分布:")
        for type_stat in result.get("by_type", []):
            print(f"    - {type_stat['type']}: {type_stat['count']}个错误, {type_stat['blocks']}次拦截")

        print(f"\n  最近拦截事件:")
        for intercept in result.get("recent_intercepts", [])[:5]:
            print(f"    - {intercept.get('error_scene')} [{intercept.get('action')}] (置信度: {intercept.get('confidence')})")
    else:
        print(f"❌ 获取统计失败: {result.get('error')}")

    return result


async def main():
    """主测试函数"""
    print("""
╔══════════════════════════════════════════════════════════╗
║   错误防火墙系统测试                                       ║
║   Phase 5 - MCP Enterprise Server v2.1.0                 ║
╚══════════════════════════════════════════════════════════╝
    """)

    # 获取数据库会话
    try:
        db_session = get_db_session()
        print("✅ 数据库连接成功")
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return

    try:
        # 运行测试
        await test_record_error(db_session)
        await test_check_operation(db_session)
        await test_query_errors(db_session)
        await test_get_stats(db_session)

        print("\n" + "=" * 60)
        print("🎉 所有测试完成!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 测试过程中出错: {e}")
        import traceback
        traceback.print_exc()

    finally:
        db_session.close()


if __name__ == "__main__":
    asyncio.run(main())

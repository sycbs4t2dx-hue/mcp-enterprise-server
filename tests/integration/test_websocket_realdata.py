#!/usr/bin/env python3
"""
WebSocket真实数据测试脚本
测试MCP Enterprise Server的WebSocket实时推送功能
"""

import asyncio
import websockets
import json
import sys

async def test_websocket_connection():
    """测试WebSocket连接和数据接收"""
    uri = "ws://localhost:8765/ws?client_id=test-client"

    print(f"🔌 连接到WebSocket服务器: {uri}")
    print("=" * 60)

    try:
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket连接成功!\n")

            # 订阅所有频道
            channels = [
                "db_pool_stats",
                "error_firewall",
                "vector_search",
                "system_alerts",
                "ai_analysis",
                "memory_updates"
            ]

            for channel in channels:
                subscribe_msg = {
                    "action": "subscribe",
                    "channel": channel
                }
                await websocket.send(json.dumps(subscribe_msg))
                print(f"📡 已订阅频道: {channel}")

            print("\n" + "=" * 60)
            print("📨 等待接收消息 (按Ctrl+C退出)...")
            print("=" * 60 + "\n")

            # 持续接收消息
            message_count = 0
            while True:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                    message_count += 1

                    data = json.loads(message)

                    print(f"\n[消息 #{message_count}] 收到时间: {data.get('timestamp', 'N/A')}")
                    print(f"类型: {data.get('type', 'unknown')}")
                    print(f"频道: {data.get('channel', 'unknown')}")
                    print(f"数据: {json.dumps(data.get('data', {}), indent=2, ensure_ascii=False)}")
                    print("-" * 60)

                except asyncio.TimeoutError:
                    print("\n⏰ 30秒内未收到消息,发送ping...")
                    await websocket.send(json.dumps({"action": "ping"}))

    except websockets.exceptions.ConnectionClosed:
        print("\n❌ WebSocket连接已关闭")
        return False
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        return False

    return True

async def trigger_pool_adjustment():
    """触发连接池调整(模拟高负载)"""
    print("\n🔧 触发连接池调整测试...")
    print("提示: 需要手动执行数据库查询以触发连接池自动调整")
    print("或等待自然流量触发调整\n")

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════╗
║   MCP Enterprise WebSocket 真实数据测试                   ║
╚══════════════════════════════════════════════════════════╝

测试目标:
1. 验证WebSocket连接正常
2. 验证频道订阅功能
3. 验证实时数据推送
4. 验证连接池调整推送

预期行为:
- 连接成功后显示订阅的6个频道
- 当连接池调整时会收到 db_pool_stats 消息
- 消息包含真实的pool_size、utilization等指标
    """)

    try:
        asyncio.run(test_websocket_connection())
    except KeyboardInterrupt:
        print("\n\n👋 测试结束")
        sys.exit(0)

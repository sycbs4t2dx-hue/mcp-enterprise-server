"""
WebSocket测试客户端
用于测试WebSocket实时通知功能
"""

import asyncio
import aiohttp
import json
from datetime import datetime


async def test_websocket_client():
    """WebSocket客户端测试"""
    
    url = "ws://localhost:8080/ws?client_id=test_client_001"
    
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(url) as ws:
            print(f"✅ 连接成功: {url}")
            print("=" * 60)
            
            # 等待欢迎消息
            msg = await ws.receive()
            if msg.type == aiohttp.WSMsgType.TEXT:
                data = json.loads(msg.data)
                print(f"📩 欢迎消息: {json.dumps(data, indent=2, ensure_ascii=False)}")
                print("=" * 60)
            
            # 订阅频道
            channels = ["error_firewall", "db_pool_stats", "system_alerts"]
            for channel in channels:
                await ws.send_json({
                    "action": "subscribe",
                    "channel": channel
                })
                msg = await ws.receive()
                data = json.loads(msg.data)
                print(f"✅ 订阅频道: {channel} - {data.get('status')}")
            
            print("=" * 60)
            print("📡 等待实时消息 (Ctrl+C退出)...")
            print("=" * 60)
            
            # 接收消息
            try:
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        data = json.loads(msg.data)
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        print(f"[{timestamp}] 📨 收到消息:")
                        print(f"  频道: {data.get('channel')}")
                        print(f"  类型: {data.get('type')}")
                        print(f"  数据: {json.dumps(data.get('data'), indent=4, ensure_ascii=False)}")
                        print("-" * 60)
                    
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        print(f"❌ WebSocket错误: {ws.exception()}")
                        break
            
            except KeyboardInterrupt:
                print("\n👋 用户中断，关闭连接...")
            
            finally:
                await ws.close()
                print("✅ 连接已关闭")


if __name__ == "__main__":
    asyncio.run(test_websocket_client())

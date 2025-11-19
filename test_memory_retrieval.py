#!/usr/bin/env python3
"""
测试改进后的记忆检索功能
"""
import json
import requests

MCP_SERVER = "http://localhost:8765"

def test_retrieve_memory(query: str, project_id: str = "history-timeline"):
    """测试记忆检索"""
    print(f"\n{'='*60}")
    print(f"测试查询: {query}")
    print(f"{'='*60}")

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "retrieve_memory",
            "arguments": {
                "project_id": project_id,
                "query": query,
                "top_k": 5
            }
        }
    }

    response = requests.post(MCP_SERVER, json=payload)
    result = response.json()

    if "result" in result:
        content = json.loads(result["result"]["content"][0]["text"])

        print(f"\n✅ 检索成功:")
        print(f"   返回记忆数: {content.get('count', 0)}")

        if content.get('memories'):
            print(f"\n   匹配的记忆:")
            for i, mem in enumerate(content['memories'][:3], 1):
                print(f"\n   {i}. 记忆ID: {mem.get('memory_id', 'N/A')}")
                print(f"      内容预览: {mem.get('content', 'N/A')[:80]}...")
                print(f"      相关性: {mem.get('relevance_score', 0):.3f}")
                print(f"      来源: {mem.get('source', 'N/A')}")
                if 'matched_keywords' in mem:
                    print(f"      匹配关键词数: {mem['matched_keywords']}")
        else:
            print("\n   ⚠️  没有找到匹配的记忆")
    else:
        print(f"❌ 检索失败: {result.get('error', 'Unknown error')}")

    return result

if __name__ == "__main__":
    # 测试用例
    test_cases = [
        "历史时间轴项目",
        "React和D3.js",
        "AI智能助手",
        "TTS语音朗读",
        "MongoDB数据库",
    ]

    print("="*60)
    print("  记忆检索功能测试")
    print("="*60)

    for query in test_cases:
        try:
            test_retrieve_memory(query)
        except Exception as e:
            print(f"\n❌ 测试失败: {e}")

    print(f"\n{'='*60}")
    print("测试完成!")
    print(f"{'='*60}\n")

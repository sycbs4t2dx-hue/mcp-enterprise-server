#!/usr/bin/env python3
"""
MCP服务端测试脚本
快速验证MCP协议实现是否正常
"""

import json
import subprocess
import sys


def send_request(process, method, params):
    """发送JSON-RPC请求"""
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params
    }

    print(f"\n📤 发送请求: {method}")
    print(f"参数: {json.dumps(params, ensure_ascii=False, indent=2)}")

    process.stdin.write(json.dumps(request) + "\n")
    process.stdin.flush()

    response_line = process.stdout.readline()
    response = json.loads(response_line)

    print(f"\n📥 响应:")
    print(json.dumps(response, ensure_ascii=False, indent=2))

    return response


def main():
    """测试MCP服务端"""
    print("=" * 60)
    print("MCP服务端测试")
    print("=" * 60)

    # 启动MCP服务端
    print("\n1️⃣ 启动MCP服务端...")
    process = subprocess.Popen(
        ["python3", "-m", "src.mcp_core.mcp_server"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )

    try:
        # 测试1: 初始化
        print("\n" + "=" * 60)
        print("测试1: Initialize")
        print("=" * 60)

        response = send_request(process, "initialize", {
            "protocolVersion": "2025-06-18",
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        })

        if "result" in response:
            print("✅ 初始化成功")
            print(f"   服务器: {response['result']['serverInfo']['name']}")
            print(f"   版本: {response['result']['serverInfo']['version']}")
        else:
            print("❌ 初始化失败")
            return

        # 测试2: 列出工具
        print("\n" + "=" * 60)
        print("测试2: Tools List")
        print("=" * 60)

        response = send_request(process, "tools/list", {})

        if "result" in response and "tools" in response["result"]:
            tools = response["result"]["tools"]
            print(f"✅ 获取到 {len(tools)} 个工具:")
            for tool in tools:
                print(f"   - {tool['name']}: {tool['description']}")
        else:
            print("❌ 获取工具列表失败")

        # 测试3: 列出提示模板
        print("\n" + "=" * 60)
        print("测试3: Prompts List")
        print("=" * 60)

        response = send_request(process, "prompts/list", {})

        if "result" in response and "prompts" in response["result"]:
            prompts = response["result"]["prompts"]
            print(f"✅ 获取到 {len(prompts)} 个提示模板:")
            for prompt in prompts:
                print(f"   - {prompt['name']}: {prompt['description']}")
        else:
            print("❌ 获取提示列表失败")

        # 测试4: 调用工具 (需要数据库)
        print("\n" + "=" * 60)
        print("测试4: 调用compress_content工具")
        print("=" * 60)

        response = send_request(process, "tools/call", {
            "name": "compress_content",
            "arguments": {
                "content": "这是一段很长的文本，需要被压缩以节省Token。" * 10,
                "target_ratio": 0.5
            }
        })

        if "result" in response:
            print("✅ 工具调用成功")
            # 解析返回的JSON文本
            result_text = response["result"]["content"][0]["text"]
            result_data = json.loads(result_text)
            if result_data.get("success"):
                print(f"   压缩率: {result_data.get('compression_ratio', 'N/A')}")
        else:
            print("❌ 工具调用失败")

        print("\n" + "=" * 60)
        print("✅ 所有测试完成")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # 关闭进程
        process.terminate()
        process.wait()


if __name__ == "__main__":
    main()

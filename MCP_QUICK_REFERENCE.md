# MCP快速参考

> 一页纸快速开始使用MCP协议

## 🎯 项目现状

**v1.1.0** - 支持双接口:
- ✅ REST API (http://localhost:8000)
- ✅ MCP协议 (stdio)

## 🚀 30秒快速开始

### Claude Desktop使用

1. **添加配置**

编辑 `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "mcp-memory": {
      "command": "/Users/mac/Downloads/MCP/start_mcp_server.sh"
    }
  }
}
```

2. **重启Claude Desktop**

3. **开始对话**

```
你: "帮我记住项目proj_001使用FastAPI框架"
Claude: ✅ 已存储

你: "项目用什么框架？"
Claude: 项目使用FastAPI框架
```

---

## 🛠️ 可用工具

| 工具 | 功能 | 示例提示 |
|------|------|----------|
| **store_memory** | 存储记忆 | "帮我记住..." |
| **retrieve_memory** | 检索记忆 | "查询关于...的信息" |
| **compress_content** | 压缩文本 | "压缩这段文本" |
| **detect_hallucination** | 检测幻觉 | "检查这段话是否准确" |

---

## 📝 Python集成

```python
import json, subprocess

# 启动MCP服务
process = subprocess.Popen(
    ["/Users/mac/Downloads/MCP/start_mcp_server.sh"],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True
)

# 初始化
request = {
    "jsonrpc": "2.0", "id": 1,
    "method": "initialize",
    "params": {"protocolVersion": "2025-06-18"}
}
process.stdin.write(json.dumps(request) + "\n")
process.stdin.flush()

# 存储记忆
request = {
    "jsonrpc": "2.0", "id": 2,
    "method": "tools/call",
    "params": {
        "name": "store_memory",
        "arguments": {
            "project_id": "my_project",
            "content": "重要信息..."
        }
    }
}
process.stdin.write(json.dumps(request) + "\n")
process.stdin.flush()
print(process.stdout.readline())
```

---

## 🔍 故障排查

### 问题1: Claude Desktop未显示工具

**检查**:
- 配置文件路径是否正确
- `start_mcp_server.sh` 是否可执行
- 查看日志 `logs/mcp_server.log`

### 问题2: 数据库连接失败

**解决**:
```bash
# 1. 启动MySQL
# 2. 初始化数据库
python3 scripts/init_database.py

# 3. 测试REST API
./start.sh
curl http://localhost:8000/health
```

### 问题3: 调试MCP通信

**查看日志**:
```bash
tail -f /Users/mac/Downloads/MCP/logs/mcp_server.log
```

**手动测试**:
```bash
python3 test_mcp_server.py
```

---

## 📊 两种接口对比

| 特性 | REST API | MCP协议 |
|------|----------|---------|
| **用途** | Web/移动应用 | AI工具集成 |
| **认证** | JWT Token | 无需 |
| **调用** | HTTP请求 | AI自动 |
| **地址** | http://localhost:8000 | stdio |

---

## 📚 完整文档

- **详细指南**: [MCP_USAGE_GUIDE.md](MCP_USAGE_GUIDE.md)
- **实现报告**: [MCP_IMPLEMENTATION_REPORT.md](MCP_IMPLEMENTATION_REPORT.md)
- **升级总结**: [MCP_UPGRADE_SUMMARY.md](MCP_UPGRADE_SUMMARY.md)
- **项目主页**: [README.md](README.md)

---

## 🎓 典型使用流程

### 1. AI助手模式（Claude Desktop）

```
用户对话 → Claude自动选择工具 → MCP服务器 → 数据库
                                      ↓
                                   返回结果
```

### 2. 应用集成模式

```
Python/Node.js → JSON-RPC请求 → MCP服务器 → 数据库
应用程序                             ↓
                                返回JSON响应
```

### 3. 混合模式

```
Web界面(REST API) ←→ 数据库 ←→ MCP服务器 ←→ Claude Desktop
     管理记忆               共享数据         AI访问记忆
```

---

## 💡 最佳实践

1. **项目ID规范**
   - 使用清晰命名: `proj_myapp`, `proj_docs`
   - 一个项目一个ID

2. **记忆分级**
   - short: 临时会话信息
   - mid: 项目相关知识
   - long: 核心长期知识

3. **标签使用**
   - 为记忆添加标签便于检索
   - 例: `["config", "api", "database"]`

4. **定期检测**
   - 重要输出使用 `detect_hallucination`
   - 确保AI回答准确性

---

**快速开始? 查看** [MCP_USAGE_GUIDE.md](MCP_USAGE_GUIDE.md) **获取详细步骤！**

---

**MCP Memory Server v1.1.0** 🚀

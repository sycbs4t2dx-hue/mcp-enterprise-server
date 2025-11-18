# MCP服务端使用指南

> 如何让Claude Desktop和其他AI工具使用MCP进行记忆持久化

## 🎯 什么是MCP服务端？

本项目现在支持**两种接口**：

1. **REST API** (http://localhost:8000) - 用于Web应用、移动端
2. **MCP协议** (stdio) - 用于Claude Desktop、其他AI工具

## 🚀 快速开始

### 1. 在Claude Desktop中使用

#### 步骤1: 复制配置

将 `claude_desktop_config.json` 的内容添加到Claude Desktop配置文件：

**macOS路径**: `~/Library/Application Support/Claude/claude_desktop_config.json`

**Windows路径**: `%APPDATA%\Claude\claude_desktop_config.json`

**Linux路径**: `~/.config/Claude/claude_desktop_config.json`

配置内容：
```json
{
  "mcpServers": {
    "mcp-memory": {
      "command": "/Users/mac/Downloads/MCP/start_mcp_server.sh",
      "env": {
        "PYTHONPATH": "/Users/mac/Downloads/MCP",
        "MCP_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

**注意**: 请将路径 `/Users/mac/Downloads/MCP` 修改为您的实际项目路径。

#### 步骤2: 重启Claude Desktop

关闭并重新打开Claude Desktop，MCP服务端会自动启动。

#### 步骤3: 验证连接

在Claude Desktop对话框中，您会看到一个工具图标(🔌)，表示MCP服务已连接。

#### 步骤4: 开始使用

直接与Claude对话，例如：

```
你: 帮我记住：这个项目使用FastAPI框架
Claude: [调用store_memory工具存储]

你: 之前我说项目用什么框架来着？
Claude: [调用retrieve_memory工具检索] 您之前提到项目使用FastAPI框架。

你: 帮我压缩这段长文本...
Claude: [调用compress_content工具]
```

Claude会**自动选择**合适的工具来完成任务！

## 🛠️ 可用的MCP工具

### 1. store_memory - 存储记忆

**功能**: 将信息持久化到项目记忆库

**参数**:
- `project_id` (必填): 项目ID
- `content` (必填): 记忆内容
- `memory_level` (可选): short/mid/long，默认mid
- `tags` (可选): 标签数组

**示例**:
```
"帮我记住项目proj_001的配置信息：数据库使用MySQL"
```

### 2. retrieve_memory - 检索记忆

**功能**: 根据查询检索相关历史记忆

**参数**:
- `project_id` (必填): 项目ID
- `query` (必填): 检索查询
- `top_k` (可选): 返回数量，默认5
- `memory_level` (可选): 记忆级别过滤

**示例**:
```
"查询项目proj_001中关于数据库的信息"
```

### 3. compress_content - 压缩内容

**功能**: 压缩长文本以节省Token

**参数**:
- `content` (必填): 待压缩内容
- `target_ratio` (可选): 目标压缩率0-1，默认0.5

**示例**:
```
"帮我把这段API文档压缩到原来的50%"
```

### 4. detect_hallucination - 检测幻觉

**功能**: 检测AI输出是否包含不准确信息

**参数**:
- `project_id` (必填): 项目ID
- `output` (必填): AI生成的输出

**示例**:
```
"检查一下这段描述是否准确：项目使用PostgreSQL数据库"
```

## 📊 MCP vs REST API

| 特性 | MCP协议 | REST API |
|------|---------|----------|
| **使用场景** | AI工具集成 | Web/移动应用 |
| **调用方式** | LLM自动调用 | 手动HTTP请求 |
| **认证** | 无需（本地） | JWT Token |
| **传输** | stdio | HTTP |
| **客户端** | Claude Desktop等 | 任何HTTP客户端 |

## 🔧 高级配置

### 调试MCP连接

查看MCP服务端日志：

```bash
tail -f /Users/mac/Downloads/MCP/logs/mcp_server.log
```

### 手动测试MCP服务端

```bash
cd /Users/mac/Downloads/MCP

# 通过stdin发送请求
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","clientInfo":{"name":"test","version":"1.0.0"}}}' | python3 -m src.mcp_core.mcp_server
```

### 修改项目ID

默认情况下，MCP工具需要传入 `project_id`。建议在Claude Desktop中创建一个默认项目：

```bash
# 使用REST API创建项目
curl -X POST http://localhost:8000/api/v1/project/create \
  -H "Authorization: Bearer <your_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "my_default_project",
    "name": "我的默认项目",
    "description": "Claude Desktop使用的默认项目"
  }'
```

然后在Claude对话中直接使用：
```
"帮我在my_default_project项目中存储这个信息..."
```

## 🌐 在其他AI项目中使用

### Python项目集成

```python
import json
import subprocess

class MCPClient:
    """MCP客户端封装"""

    def __init__(self, server_path: str):
        self.process = subprocess.Popen(
            [server_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # 初始化连接
        self._send_request("initialize", {
            "protocolVersion": "2025-06-18",
            "clientInfo": {"name": "my-ai-app", "version": "1.0.0"}
        })

    def _send_request(self, method: str, params: dict):
        """发送JSON-RPC请求"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params
        }

        self.process.stdin.write(json.dumps(request) + "\n")
        self.process.stdin.flush()

        response = json.loads(self.process.stdout.readline())
        return response.get("result")

    def store_memory(self, project_id: str, content: str):
        """存储记忆"""
        return self._send_request("tools/call", {
            "name": "store_memory",
            "arguments": {
                "project_id": project_id,
                "content": content
            }
        })

    def retrieve_memory(self, project_id: str, query: str):
        """检索记忆"""
        return self._send_request("tools/call", {
            "name": "retrieve_memory",
            "arguments": {
                "project_id": project_id,
                "query": query
            }
        })

# 使用示例
client = MCPClient("/Users/mac/Downloads/MCP/start_mcp_server.sh")
client.store_memory("proj_001", "项目使用FastAPI")
results = client.retrieve_memory("proj_001", "项目框架")
print(results)
```

### Node.js项目集成

```javascript
const { spawn } = require('child_process');
const readline = require('readline');

class MCPClient {
  constructor(serverPath) {
    this.process = spawn(serverPath);
    this.rl = readline.createInterface({
      input: this.process.stdout
    });

    // 初始化
    this.sendRequest('initialize', {
      protocolVersion: '2025-06-18',
      clientInfo: { name: 'my-ai-app', version: '1.0.0' }
    });
  }

  sendRequest(method, params) {
    return new Promise((resolve) => {
      const request = {
        jsonrpc: '2.0',
        id: 1,
        method: method,
        params: params
      };

      this.process.stdin.write(JSON.stringify(request) + '\n');

      this.rl.once('line', (line) => {
        const response = JSON.parse(line);
        resolve(response.result);
      });
    });
  }

  async storeMemory(projectId, content) {
    return await this.sendRequest('tools/call', {
      name: 'store_memory',
      arguments: { project_id: projectId, content: content }
    });
  }

  async retrieveMemory(projectId, query) {
    return await this.sendRequest('tools/call', {
      name: 'retrieve_memory',
      arguments: { project_id: projectId, query: query }
    });
  }
}

// 使用示例
const client = new MCPClient('/Users/mac/Downloads/MCP/start_mcp_server.sh');
await client.storeMemory('proj_001', '项目使用FastAPI');
const results = await client.retrieveMemory('proj_001', '项目框架');
console.log(results);
```

## 🎓 最佳实践

### 1. 项目ID命名规范

建议使用清晰的命名：
- `proj_myapp` - 您的应用项目
- `proj_docs` - 文档相关
- `proj_research` - 研究笔记

### 2. 记忆分级策略

- **short** (短期): 会话内临时信息，自动过期
- **mid** (中期): 项目相关信息，保留1个月
- **long** (长期): 核心知识，永久保存

### 3. 标签使用

为记忆添加标签便于后续检索：

```
store_memory(
  project_id="proj_001",
  content="API密钥: sk-xxx",
  tags=["config", "api", "secret"]
)
```

### 4. 定期检测幻觉

在生成重要内容后检测：

```
detect_hallucination(
  project_id="proj_001",
  output="系统使用Redis作为主数据库"
)
```

## 🐛 故障排查

### 问题1: Claude Desktop未显示工具

**解决**:
1. 检查配置文件路径是否正确
2. 确认 `start_mcp_server.sh` 有执行权限
3. 查看日志 `logs/mcp_server.log`

### 问题2: 数据库连接失败

**解决**:
1. 确保MySQL已启动并初始化
2. 检查 `config.yaml` 中的数据库配置
3. 运行 `python3 scripts/init_database.py`

### 问题3: 工具调用失败

**解决**:
1. 查看 `logs/mcp_server.log` 的错误信息
2. 确认REST API正常运行 (`./start.sh`)
3. 检查项目ID是否存在

## 📚 相关资源

- [MCP官方规范](https://modelcontextprotocol.io/specification/2025-06-18)
- [Claude Desktop文档](https://claude.ai/docs)
- [REST API文档](http://localhost:8000/docs)
- [项目README](README.md)

## 🆘 获取帮助

遇到问题？

1. 查看日志文件 `logs/mcp_server.log`
2. 检查REST API是否正常: `curl http://localhost:8000/health`
3. 运行测试: `pytest tests/unit/ -v`

---

**MCP Memory Server v1.0.0** - 让AI拥有持久记忆 🧠

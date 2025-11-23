# 🚀 MCP v2.0.0 - 快速参考卡

## 📦 三种服务器版本

| 版本 | 文件 | 适用场景 | 特性 |
|------|------|---------|------|
| **Simple** | `mcp_server_http_simple.py` | 小团队，快速开始 | ✅ 简单<br>❌ 无安全 |
| **Standard** | `mcp_server_unified.py` | 本机开发 | ✅ stdio<br>✅ 完整功能 |
| **Enterprise** | `mcp_server_enterprise.py` | 生产环境 | ✅ 认证<br>✅ 监控<br>✅ 限流 |

---

## 🎯 快速启动

### 方案1: 本机开发（推荐个人）

```bash
# Claude Code配置
{
  "mcpServers": {
    "mcp-local": {
      "command": "python3",
      "args": ["/Users/mac/Downloads/MCP/mcp_server_unified.py"],
      "env": {"DB_PASSWORD": "Wxwy.2025@#"}
    }
  }
}
```

### 方案2: 局域网简单（推荐小团队）

```bash
# 启动
./start_sse_server.sh

# Claude Code配置
{
  "mcpServers": {
    "mcp-remote": {
      "url": "http://192.168.3.5:8765"
    }
  }
}
```

### 方案3: 企业生产（推荐企业）

```bash
# 配置
cp .env.example .env
vim .env  # 设置API_KEYS和ALLOWED_IPS

# 启动
./start_enterprise_server.sh

# Claude Code配置
{
  "mcpServers": {
    "mcp-remote": {
      "url": "http://192.168.3.5:8765",
      "headers": {
        "Authorization": "Bearer sk-your-api-key"
      }
    }
  }
}
```

---

## 🔧 常用命令

### 服务管理

```bash
# 启动Docker服务
docker start mcp-mysql mcp-redis mcp-milvus

# 启动MCP服务器（简单版）
./start_sse_server.sh

# 启动MCP服务器（企业版）
./start_enterprise_server.sh

# 查看服务器状态
curl http://192.168.3.5:8765/health

# 查看统计
curl http://192.168.3.5:8765/stats

# 查看Prometheus指标
curl http://192.168.3.5:8765/metrics
```

### 测试命令

```bash
# 测试工具列表
curl -X POST http://192.168.3.5:8765/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'

# 测试工具调用
curl -X POST http://192.168.3.5:8765/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"retrieve_memory","arguments":{"project_id":"test","query":"测试"}}}'

# 带认证的请求
curl -X POST http://192.168.3.5:8765/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-your-key" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

---

## 📋 配置选项

### 环境变量 (.env)

```bash
# 基础配置
HOST=0.0.0.0
PORT=8765
DB_PASSWORD=Wxwy.2025@#

# 安全配置
API_KEYS=sk-key1,sk-key2
ALLOWED_IPS=192.168.1.10,192.168.1.20

# 性能配置
RATE_LIMIT=100
MAX_CONNECTIONS=1000
```

### 命令行参数

```bash
python3 mcp_server_enterprise.py \
  --host 0.0.0.0 \
  --port 8765 \
  --api-key sk-key1 \
  --api-key sk-key2 \
  --allowed-ip 192.168.1.10 \
  --allowed-ip 192.168.1.20 \
  --rate-limit 100 \
  --max-connections 1000
```

---

## 🐛 故障排查

| 问题 | 解决方案 |
|------|---------|
| `fetch failed` | 检查服务器运行状态，查看 /health |
| `401 Unauthorized` | 检查API密钥和Authorization头 |
| `429 Rate limit` | 减少请求频率或调整 --rate-limit |
| `503 Server capacity` | 增加 --max-connections |
| Docker连接失败 | `docker start mcp-mysql mcp-redis mcp-milvus` |

---

## 📊 监控端点

| 端点 | 用途 |
|------|------|
| `/health` | 健康检查 |
| `/stats` | 统计数据 |
| `/connections` | 活动连接 |
| `/metrics` | Prometheus指标 |
| `/info` | 服务器信息页面 |

---

## 🎯 37个可用工具

### 基础记忆 (2)
- `store_memory` - 存储记忆
- `retrieve_memory` - 检索记忆

### 代码分析 (8)
- `analyze_codebase` - 分析代码库
- `query_architecture` - 查询架构
- `find_entity` - 查找实体
- `trace_function_calls` - 追踪调用
- `find_dependencies` - 查找依赖
- `list_modules` - 列出模块
- `explain_module` - 解释模块
- `search_code_pattern` - 搜索模式

### 项目上下文 (12)
- `start_dev_session` - 开始会话
- `end_dev_session` - 结束会话
- `record_design_decision` - 记录决策
- `add_project_note` - 添加笔记
- `create_todo` - 创建TODO
- `update_todo_status` - 更新状态
- `get_project_context` - 获取上下文
- `list_todos` - 列出TODO
- `get_next_todo` - 获取下一个
- `list_design_decisions` - 列出决策
- `list_project_notes` - 列出笔记
- `get_project_statistics` - 获取统计

### AI辅助 (7)
- `ai_understand_function` - AI理解函数
- `ai_understand_module` - AI理解模块
- `ai_explain_architecture` - AI解释架构
- `ai_generate_resumption_briefing` - 生成简报
- `ai_generate_todos_from_goal` - 生成TODO
- `ai_decompose_task` - 分解任务
- `ai_analyze_code_quality` - 分析质量

### 质量守护 (8)
- `detect_code_smells` - 检测异味
- `assess_technical_debt` - 评估债务
- `identify_debt_hotspots` - 识别热点
- `get_quality_trends` - 质量趋势
- `resolve_quality_issue` - 解决问题
- `ignore_quality_issue` - 忽略问题
- `generate_quality_report` - 生成报告
- `list_quality_issues` - 列出问题

---

## ✅ 成功标志

服务器正常运行会看到:
- ✅ Docker服务: `Up XX minutes`
- ✅ 健康检查: `{"status": "healthy"}`
- ✅ 工具列表: 37个工具
- ✅ 客户端: 连接成功，可使用工具

---

**MCP v2.0.0 - 生产就绪！** 🎉

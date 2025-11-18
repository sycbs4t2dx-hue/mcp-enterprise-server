# 远程MCP服务使用指南

> 如何在Claude Code/Desktop中使用远程MCP记忆服务

## 🎯 服务说明

远程MCP服务提供：
- ✅ 云端记忆持久化
- ✅ 跨设备同步
- ✅ 多项目管理
- ✅ Token压缩
- ✅ 幻觉检测

---

## 🚀 快速开始（3步）

### 步骤1: 获取API Key

联系管理员获取您的专属API Key，格式如：
```
mcp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

⚠️ **请妥善保管**，不要分享给他人！

---

### 步骤2: 配置Claude Desktop

#### 2.1 找到配置文件

**macOS**:
```bash
~/Library/Application Support/Claude/claude_desktop_config.json
```

**Windows**:
```
%APPDATA%\Claude\claude_desktop_config.json
```

**Linux**:
```bash
~/.config/Claude/claude_desktop_config.json
```

#### 2.2 添加配置

编辑配置文件，添加以下内容：

```json
{
  "mcpServers": {
    "remote-mcp-memory": {
      "url": "https://mcp.yourdomain.com/mcp",
      "transport": "http",
      "headers": {
        "Authorization": "Bearer mcp_your_api_key_here"
      }
    }
  }
}
```

**重要**:
- 将 `mcp.yourdomain.com` 替换为实际服务器地址
- 将 `mcp_your_api_key_here` 替换为您的API Key

**完整示例**:
```json
{
  "mcpServers": {
    "remote-mcp-memory": {
      "url": "https://mcp.example.com/mcp",
      "transport": "http",
      "headers": {
        "Authorization": "Bearer mcp_abc123xyz789..."
      }
    }
  }
}
```

---

### 步骤3: 重启Claude Desktop

关闭并重新打开Claude Desktop。

**验证连接成功**:
- 看到工具图标 🔌
- 可以使用记忆相关功能

---

## 💡 使用示例

### 1. 存储记忆

**对话**:
```
你: "帮我记住项目proj_001使用的技术栈：
    - 后端：FastAPI + Python
    - 数据库：MySQL + Redis
    - 前端：React + TypeScript"

Claude: [自动调用store_memory工具]
        ✅ 已为您存储这些信息到项目proj_001
```

**幕后发生**:
- Claude自动选择 `store_memory` 工具
- 参数：`project_id="proj_001"`, `content="技术栈..."`
- 服务器保存到数据库

### 2. 检索记忆

**对话**:
```
你: "项目proj_001用的什么数据库？"

Claude: [自动调用retrieve_memory工具]
        根据记忆，项目proj_001使用MySQL作为主数据库，
        Redis用于缓存。
```

### 3. 压缩长文本

**对话**:
```
你: "帮我压缩这段API文档到原来的50%：
    [很长的API文档...]"

Claude: [自动调用compress_content工具]
        已为您压缩完成，压缩率52%，保留了核心信息：
        [压缩后的内容]
```

### 4. 检测AI幻觉

**对话**:
```
你: "检查这段描述是否准确：
    项目使用PostgreSQL数据库"

Claude: [自动调用detect_hallucination工具]
        ⚠️ 检测到可能的不准确信息。
        根据记忆，项目实际使用的是MySQL，不是PostgreSQL。
```

---

## 🎓 最佳实践

### 项目ID命名

建议使用清晰的命名：
- `proj_myapp` - 您的应用项目
- `proj_work` - 工作相关
- `proj_study` - 学习笔记
- `proj_personal` - 个人项目

### 记忆分级

选择合适的记忆级别：
- **short** - 临时信息，会话结束后自动清理
- **mid** - 项目相关信息，保留1个月（默认）
- **long** - 核心知识，永久保存

**示例**:
```
"帮我长期记住Python最佳实践..."  → long
"记住这个临时密码..."  → short
"项目的数据库配置..."  → mid
```

### 使用标签

为记忆添加标签便于管理：

```
"帮我记住API密钥，标签：config, api, secret"
```

### 定期清理

定期清理不再需要的记忆：

```
"删除proj_old中的所有临时记忆"
```

---

## 🔐 安全提示

### 1. API Key安全

- ✅ 不要分享给他人
- ✅ 不要提交到Git仓库
- ✅ 定期更换（联系管理员）
- ✅ 发现泄露立即撤销

### 2. 敏感信息

**不要存储**:
- ❌ 密码
- ❌ 密钥
- ❌ 信用卡信息
- ❌ 身份证号

**可以存储**:
- ✅ 项目配置（非敏感）
- ✅ 代码片段
- ✅ 学习笔记
- ✅ 工作流程

### 3. 数据隔离

每个用户的数据是隔离的：
- 您的记忆只有您能访问
- API Key绑定特定用户

---

## 🐛 故障排查

### 问题1: 工具图标不显示

**原因**: 配置错误或服务器连接失败

**解决**:
1. 检查配置文件格式是否正确
2. 检查API Key是否有效
3. 测试服务器连接：
   ```bash
   curl https://mcp.yourdomain.com/health
   ```
4. 查看Claude Desktop日志

### 问题2: API Key无效

**错误信息**: "Invalid API Key"

**解决**:
1. 确认API Key复制完整
2. 确认没有多余空格
3. 联系管理员验证Key是否有效
4. 申请新的API Key

### 问题3: 记忆未保存

**原因**: 网络问题或服务器错误

**检查**:
```
"查询proj_xxx中的所有记忆"
```

**解决**:
1. 检查网络连接
2. 重试操作
3. 联系管理员查看服务器日志

### 问题4: 响应很慢

**原因**: 服务器负载或网络延迟

**优化**:
- 避免存储超大文本（先压缩）
- 减少检索数量（默认5条）
- 选择合适的记忆级别

---

## 📊 配额与限制

### 请求限制

- 每秒请求：10次
- 突发请求：20次
- 超过限制：稍后重试

### 存储限制

- 单条记忆：最大100KB
- 项目数量：无限制
- 记忆数量：无限制（建议定期清理）

### 网络要求

- 需要HTTPS访问
- 需要稳定网络连接
- 建议延迟 <500ms

---

## 💡 高级用法

### 批量操作

```
"帮我批量存储这些配置到proj_001:
1. 数据库：MySQL
2. 缓存：Redis
3. 队列：RabbitMQ"
```

### 跨项目查询

```
"查询我在所有项目中关于FastAPI的记忆"
```

（需要管理员启用全局搜索）

### 导出记忆

```
"导出proj_001的所有记忆为Markdown格式"
```

### 统计分析

```
"统计proj_001中存储了多少条记忆"
```

---

## 📞 获取帮助

### 遇到问题？

1. **查看文档**
   - 本文档
   - [完整部署文档](DEPLOYMENT_GUIDE.md)

2. **联系管理员**
   - 报告问题
   - 申请新API Key
   - 查询使用统计

3. **社区支持**
   - GitHub Issues
   - 用户论坛

---

## 📚 相关资源

- [MCP官方规范](https://modelcontextprotocol.io)
- [Claude Desktop文档](https://claude.ai/docs)
- [服务器部署指南](DEPLOYMENT_GUIDE.md)
- [API参考文档](API_REFERENCE.md)

---

## ✨ 使用技巧

### 技巧1: 结构化存储

```
"帮我结构化存储项目信息：
项目ID: proj_webapp
名称: 电商平台
技术栈: [列表]
团队成员: [列表]
部署地址: xxx"
```

### 技巧2: 上下文记忆

```
第一次对话:
"记住项目proj_001使用微服务架构"

下次对话:
"proj_001用什么架构？"
→ Claude会自动检索之前的记忆
```

### 技巧3: 渐进式学习

```
"记住关于Python装饰器的学习笔记..."
"记住装饰器的实际应用案例..."
"记住装饰器的最佳实践..."

稍后:
"总结我学习的Python装饰器知识"
→ Claude会综合所有相关记忆
```

---

**开始使用远程MCP服务，让AI拥有云端记忆！** 🚀

---

**版本**: 1.1.0
**更新时间**: 2025-01-19

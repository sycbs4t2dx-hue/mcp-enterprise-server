# Hugging Face模型本地化 - 快速指南

## 🎯 问题

默认情况下，Hugging Face模型会下载到系统缓存目录（如 `~/.cache/huggingface/`），导致：
- 占用系统盘空间
- 重装系统需重新下载
- 路径管理混乱

## ✅ 解决方案

本项目已配置模型本地化管理，所有模型统一存储在 `./models/` 目录。

---

## 🚀 快速开始

### 方法1: 一键设置脚本 (推荐)

```bash
# 运行自动设置脚本
./scripts/setup_models.sh
```

交互式引导下载所有模型，支持镜像加速。

### 方法2: 手动下载

```bash
# 列出可用模型
python3 scripts/download_models.py --list

# 下载所有模型 (使用国内镜像)
python3 scripts/download_models.py --download all --mirror

# 验证文件完整性
python3 scripts/download_models.py --validate all
```

---

## 📁 文件结构

```
MCP/
├── models/                          # 模型存储目录 (自动创建)
│   ├── all-MiniLM-L6-v2/           # 嵌入模型 (~90MB)
│   └── codebert-base/              # 代码模型 (~500MB)
│
├── config.yaml                      # 模型配置
├── scripts/
│   ├── setup_models.sh             # 一键设置脚本
│   └── download_models.py          # 模型下载工具
│
└── src/mcp_core/services/
    └── embedding_service.py        # 自动使用本地模型
```

---

## ⚙️ 配置说明

### config.yaml 关键配置

```yaml
models:
  # 本地模型目录
  local_model_dir: "./models"

  # 优先使用本地模型
  prefer_local: true

  # 镜像加速 (国内推荐)
  huggingface:
    use_mirror: false  # 改为true启用
    mirror_url: "https://hf-mirror.com"

  # 嵌入模型
  embedding:
    model_name: "sentence-transformers/all-MiniLM-L6-v2"
    local_path: "./models/all-MiniLM-L6-v2"
```

---

## 🔧 使用方法

### 下载命令

```bash
# 列出模型
python3 scripts/download_models.py --list

# 下载单个模型
python3 scripts/download_models.py --download embedding

# 下载所有模型
python3 scripts/download_models.py --download all

# 使用镜像加速
python3 scripts/download_models.py --download all --mirror

# 强制重新下载
python3 scripts/download_models.py --download all --force
```

### 验证命令

```bash
# 验证单个模型
python3 scripts/download_models.py --validate embedding

# 验证所有模型
python3 scripts/download_models.py --validate all
```

---

## 🌍 镜像加速 (国内推荐)

### 方法1: 命令行参数

```bash
python3 scripts/download_models.py --download all --mirror
```

### 方法2: 修改配置文件

```yaml
# config.yaml
models:
  huggingface:
    use_mirror: true  # 改为true
    mirror_url: "https://hf-mirror.com"
```

### 方法3: 环境变量

```bash
export HF_ENDPOINT="https://hf-mirror.com"
python3 scripts/download_models.py --download all
```

---

## 🔌 离线模式

### 启用完全离线

```yaml
# config.yaml
models:
  prefer_local: true
  huggingface:
    offline_mode: true  # 完全离线
```

或使用环境变量：

```bash
export TRANSFORMERS_OFFLINE=1
export HF_HUB_OFFLINE=1
```

### 验证离线模式

```bash
# 启动服务器,检查日志
export DB_PASSWORD="Wxwy.2025@#"
python3 mcp_server_enterprise.py

# 应显示:
# ✅ 使用本地模型: ./models/all-MiniLM-L6-v2
# (无网络请求)
```

---

## 📦 模型信息

### sentence-transformers/all-MiniLM-L6-v2

| 属性 | 值 |
|------|-----|
| 大小 | ~90MB |
| 用途 | 文本嵌入向量 |
| 维度 | 384 |
| 文件数 | 10个 |

### microsoft/codebert-base

| 属性 | 值 |
|------|-----|
| 大小 | ~500MB |
| 用途 | 代码理解 |
| 维度 | 768 |
| 文件数 | 6个 |

---

## ✅ 验证成功标志

运行服务器时应看到：

```
✅ 使用本地模型
   path: ./models/all-MiniLM-L6-v2
嵌入模型加载成功
   model: ./models/all-MiniLM-L6-v2
   dimension: 384
```

---

## 🚨 常见问题

### Q: 模型还是下载到缓存目录？

**A**: 检查配置
```yaml
models:
  prefer_local: true  # 确保为true
```

### Q: 提示"本地模型路径无效"？

**A**: 验证文件
```bash
python3 scripts/download_models.py --validate embedding
```

### Q: 下载速度慢？

**A**: 使用镜像
```bash
python3 scripts/download_models.py --download all --mirror
```

---

## 📦 部署到新环境

### 打包模型

```bash
# 压缩
tar -czf mcp-models.tar.gz models/

# 传输
scp mcp-models.tar.gz user@server:/path/

# 解压
tar -xzf mcp-models.tar.gz
```

### Docker部署

```dockerfile
# 复制模型
COPY models/ /app/models/
COPY config.yaml /app/

# 离线模式
ENV TRANSFORMERS_OFFLINE=1
ENV HF_HUB_OFFLINE=1
```

---

## 📖 详细文档

完整配置指南请查看: [`docs/HUGGINGFACE_MODEL_SETUP.md`](./HUGGINGFACE_MODEL_SETUP.md)

---

## 🎯 总结

- ✅ **统一管理**: 所有模型在 `./models/`
- ✅ **避免重复**: 不再下载到缓存
- ✅ **可移植**: 打包即可迁移
- ✅ **离线支持**: 完全离线使用
- ✅ **镜像加速**: 国内快速下载
- ✅ **自动识别**: 代码自动使用本地模型

---

**版本**: v1.0
**日期**: 2025-11-20

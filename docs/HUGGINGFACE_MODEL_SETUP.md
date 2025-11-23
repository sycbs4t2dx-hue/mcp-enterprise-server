# Hugging Face模型本地化配置指南

**日期**: 2025-11-20
**版本**: MCP v2.1.0
**目的**: 避免Hugging Face模型重复下载到缓存,支持本地路径管理

---

## 🎯 问题背景

### 默认行为的问题

Hugging Face默认会将模型下载到系统缓存目录:
- **macOS**: `~/.cache/huggingface/hub/`
- **Linux**: `~/.cache/huggingface/hub/`
- **Windows**: `C:\Users\<用户名>\.cache\huggingface\hub\`

**缺点**:
1. ❌ 占用系统盘空间
2. ❌ 每次重装系统需要重新下载
3. ❌ 多项目共享模型时路径混乱
4. ❌ 模型文件名不直观 (Hash格式)

### 本方案优势

✅ **统一存储**: 所有模型放在 `./models/` 目录
✅ **可移植**: 直接复制models文件夹到新环境
✅ **可管理**: 清晰的目录结构
✅ **离线支持**: 可完全离线使用
✅ **镜像加速**: 支持国内镜像站

---

## 📁 目录结构

```
MCP/
├── models/                           # 模型存储目录
│   ├── all-MiniLM-L6-v2/            # 嵌入模型
│   │   ├── config.json
│   │   ├── pytorch_model.bin
│   │   ├── tokenizer.json
│   │   ├── tokenizer_config.json
│   │   ├── vocab.txt
│   │   ├── special_tokens_map.json
│   │   ├── sentence_bert_config.json
│   │   ├── config_sentence_transformers.json
│   │   ├── modules.json
│   │   └── 1_Pooling/
│   │       └── config.json
│   │
│   └── codebert-base/               # 代码理解模型
│       ├── config.json
│       ├── pytorch_model.bin
│       ├── tokenizer.json
│       ├── tokenizer_config.json
│       ├── vocab.json
│       └── merges.txt
│
├── config.yaml                       # 配置文件 (含模型路径)
├── scripts/
│   └── download_models.py           # 模型下载工具
└── docs/
    └── HUGGINGFACE_MODEL_SETUP.md  # 本文档
```

---

## ⚙️ 配置文件说明

### config.yaml 新增部分

```yaml
# ============================================
# Hugging Face模型配置
# ============================================
models:
  # 本地模型存储路径
  local_model_dir: "./models"

  # 是否优先使用本地模型
  prefer_local: true

  # Hugging Face配置
  huggingface:
    # 是否启用离线模式 (完全不联网)
    offline_mode: false

    # 下载超时时间(秒)
    download_timeout: 300

    # 是否使用镜像站 (国内加速)
    use_mirror: false
    mirror_url: "https://hf-mirror.com"

  # 嵌入模型配置
  embedding:
    model_name: "sentence-transformers/all-MiniLM-L6-v2"
    local_path: "./models/all-MiniLM-L6-v2"
    dimension: 384
    max_seq_length: 256

    # 手动下载链接
    download_urls:
      - "https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/resolve/main/config.json"
      - "https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/resolve/main/pytorch_model.bin"
      # ... (其他文件)

  # 代码理解模型配置
  code:
    model_name: "microsoft/codebert-base"
    local_path: "./models/codebert-base"
    download_urls:
      - "https://huggingface.co/microsoft/codebert-base/resolve/main/config.json"
      # ... (其他文件)
```

---

## 🚀 使用方法

### 方法1: 自动下载 (推荐)

#### 1.1 列出可用模型

```bash
cd /Users/mac/Downloads/MCP
python3 scripts/download_models.py --list
```

**输出**:
```
============================================================
📦 可用模型列表
============================================================

[EMBEDDING]
  模型名称: sentence-transformers/all-MiniLM-L6-v2
  本地路径: ./models/all-MiniLM-L6-v2
  文件数量: 10
  状态: ❌ 未下载

[CODE]
  模型名称: microsoft/codebert-base
  本地路径: ./models/codebert-base
  文件数量: 6
  状态: ❌ 未下载
```

#### 1.2 下载单个模型

```bash
# 下载嵌入模型
python3 scripts/download_models.py --download embedding

# 下载代码模型
python3 scripts/download_models.py --download code
```

#### 1.3 下载所有模型

```bash
python3 scripts/download_models.py --download all
```

#### 1.4 使用镜像加速 (国内推荐)

```bash
# 使用HF镜像站
python3 scripts/download_models.py --download embedding --mirror
```

**镜像站配置**:
- 修改 `config.yaml`:
  ```yaml
  models:
    huggingface:
      use_mirror: true  # 改为true
      mirror_url: "https://hf-mirror.com"
  ```

#### 1.5 强制重新下载

```bash
python3 scripts/download_models.py --download embedding --force
```

---

### 方法2: 手动下载

#### 2.1 创建目录

```bash
mkdir -p models/all-MiniLM-L6-v2
mkdir -p models/codebert-base
```

#### 2.2 下载嵌入模型文件

使用浏览器或wget/curl下载以下文件到 `models/all-MiniLM-L6-v2/`:

1. **config.json**
   ```
   https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/resolve/main/config.json
   ```

2. **pytorch_model.bin** (重要,~90MB)
   ```
   https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/resolve/main/pytorch_model.bin
   ```

3. **tokenizer.json**
   ```
   https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/resolve/main/tokenizer.json
   ```

4. **tokenizer_config.json**
   ```
   https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/resolve/main/tokenizer_config.json
   ```

5. **vocab.txt**
   ```
   https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/resolve/main/vocab.txt
   ```

6. **special_tokens_map.json**
   ```
   https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/resolve/main/special_tokens_map.json
   ```

7. **sentence_bert_config.json**
   ```
   https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/resolve/main/sentence_bert_config.json
   ```

8. **config_sentence_transformers.json**
   ```
   https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/resolve/main/config_sentence_transformers.json
   ```

9. **modules.json**
   ```
   https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/resolve/main/modules.json
   ```

10. **1_Pooling/config.json** (创建子目录)
    ```bash
    mkdir -p models/all-MiniLM-L6-v2/1_Pooling
    ```
    ```
    https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/resolve/main/1_Pooling/config.json
    ```

#### 2.3 使用命令行批量下载

```bash
# 使用wget
cd models/all-MiniLM-L6-v2

wget https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/resolve/main/config.json
wget https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/resolve/main/pytorch_model.bin
wget https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/resolve/main/tokenizer.json
# ... (其他文件)

# 或使用curl
curl -L -O https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/resolve/main/config.json
curl -L -O https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/resolve/main/pytorch_model.bin
# ...
```

---

## ✅ 验证模型

### 验证单个模型

```bash
python3 scripts/download_models.py --validate embedding
```

**输出**:
```
============================================================
🔍 验证 EMBEDDING 模型
============================================================
路径: ./models/all-MiniLM-L6-v2

✅ 存在的文件:
   - config.json (571 bytes)
   - pytorch_model.bin (90,893,123 bytes)
   - tokenizer_config.json (350 bytes)

✅ 模型文件完整!
```

### 验证所有模型

```bash
python3 scripts/download_models.py --validate all
```

---

## 🔧 代码集成

### EmbeddingService自动识别

修改后的 `embedding_service.py` 会自动:

1. ✅ **优先使用本地路径**
   ```python
   # 检查 ./models/all-MiniLM-L6-v2 是否存在
   if local_path.exists() and validate_model_directory(local_path):
       model = SentenceTransformer(local_path)  # 使用本地
   ```

2. ✅ **自动降级到HF下载**
   ```python
   else:
       model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
       # 会下载到 ./models/ (由环境变量控制)
   ```

3. ✅ **支持离线模式**
   ```yaml
   models:
     huggingface:
       offline_mode: true  # 完全离线
   ```

---

## 🌍 国内镜像加速

### 方法1: 配置文件 (推荐)

```yaml
# config.yaml
models:
  huggingface:
    use_mirror: true
    mirror_url: "https://hf-mirror.com"
```

### 方法2: 环境变量

```bash
export HF_ENDPOINT="https://hf-mirror.com"
```

### 常用镜像站

| 镜像站 | URL | 说明 |
|-------|-----|------|
| HF-Mirror | https://hf-mirror.com | 国内主流镜像 |
| ModelScope | https://modelscope.cn | 阿里云镜像 |

---

## 🚨 常见问题

### Q1: 模型还是下载到缓存目录?

**原因**: `prefer_local: false` 或本地路径不存在

**解决**:
```yaml
models:
  prefer_local: true  # 确保为true
  embedding:
    local_path: "./models/all-MiniLM-L6-v2"  # 确保路径正确
```

### Q2: 提示"本地模型路径无效"?

**原因**: 缺少必要文件 (config.json, pytorch_model.bin)

**解决**:
```bash
# 验证文件
python3 scripts/download_models.py --validate embedding

# 重新下载
python3 scripts/download_models.py --download embedding --force
```

### Q3: 离线模式无法加载模型?

**原因**: 离线模式下不能联网下载

**解决**:
```yaml
models:
  huggingface:
    offline_mode: false  # 改为false,先下载

# 下载完成后再启用离线模式
offline_mode: true
```

### Q4: 下载速度慢?

**解决**:
```bash
# 使用镜像加速
python3 scripts/download_models.py --download embedding --mirror

# 或手动修改config.yaml
models:
  huggingface:
    use_mirror: true
```

### Q5: 如何完全禁用网络?

**配置**:
```yaml
models:
  prefer_local: true
  huggingface:
    offline_mode: true
```

**环境变量**:
```bash
export TRANSFORMERS_OFFLINE=1
export HF_HUB_OFFLINE=1
```

---

## 📊 模型信息

### sentence-transformers/all-MiniLM-L6-v2

| 属性 | 值 |
|------|-----|
| 用途 | 文本嵌入向量生成 |
| 维度 | 384 |
| 最大长度 | 256 tokens |
| 大小 | ~90MB |
| 语言 | 英文 (中文效果一般) |
| 速度 | 快 (~5ms/query) |

**适用场景**:
- 语义检索
- 文本相似度计算
- 聚类分析

### microsoft/codebert-base

| 属性 | 值 |
|------|-----|
| 用途 | 代码理解和嵌入 |
| 维度 | 768 |
| 大小 | ~500MB |
| 语言 | 多语言代码 (Python/Java/JS等) |

**适用场景**:
- 代码搜索
- 代码相似度
- 代码补全

---

## 🔄 迁移现有缓存

### 如果已下载到缓存目录

```bash
# 1. 查找缓存位置
ls ~/.cache/huggingface/hub/

# 2. 找到模型目录 (名称类似: models--sentence-transformers--all-MiniLM-L6-v2)
cd ~/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2/snapshots/

# 3. 复制到项目目录
cp -r <hash>/* /Users/mac/Downloads/MCP/models/all-MiniLM-L6-v2/

# 4. 验证
python3 scripts/download_models.py --validate embedding
```

---

## 📦 批量部署

### 打包models目录

```bash
# 压缩
cd /Users/mac/Downloads/MCP
tar -czf mcp-models.tar.gz models/

# 传输到新环境
scp mcp-models.tar.gz user@server:/path/to/MCP/

# 解压
tar -xzf mcp-models.tar.gz
```

### Docker部署

```dockerfile
FROM python:3.9

# 复制模型文件
COPY models/ /app/models/
COPY config.yaml /app/

# 设置环境变量 (离线模式)
ENV TRANSFORMERS_OFFLINE=1
ENV HF_HUB_OFFLINE=1
ENV TRANSFORMERS_CACHE=/app/models
```

---

## 🎯 完整工作流

### 首次设置

```bash
# 1. 创建目录
mkdir -p models

# 2. 列出模型
python3 scripts/download_models.py --list

# 3. 下载模型 (使用镜像)
python3 scripts/download_models.py --download all --mirror

# 4. 验证
python3 scripts/download_models.py --validate all

# 5. 配置为优先本地
# 编辑 config.yaml: prefer_local: true

# 6. 启动服务
export DB_PASSWORD="Wxwy.2025@#"
python3 mcp_server_enterprise.py
```

### 日常使用

```bash
# 启动服务 (自动使用本地模型)
export DB_PASSWORD="Wxwy.2025@#"
python3 mcp_server_enterprise.py

# 查看日志确认
# 应显示: ✅ 使用本地模型: ./models/all-MiniLM-L6-v2
```

---

## 📝 总结

### ✅ 已实现

1. **配置文件管理** - config.yaml统一配置
2. **自动路径识别** - embedding_service.py自动选择本地/远程
3. **下载工具** - scripts/download_models.py
4. **验证工具** - 检查文件完整性
5. **镜像支持** - 国内加速
6. **离线模式** - 完全离线使用
7. **环境变量控制** - TRANSFORMERS_CACHE等

### 🎯 优势

- 避免重复下载
- 统一管理
- 可移植
- 支持离线
- 国内加速

---

**文档版本**: v1.0
**最后更新**: 2025-11-20
**维护者**: MCP团队

📧 如有问题,请提交Issue: https://github.com/your-repo/MCP/issues

# 模型下载脚本修复报告

**日期**: 2025-11-20
**问题**: 下载脚本不会重新下载缺失文件 + tokenizer.json 404错误

---

## 🐛 问题分析

### 问题1: 不完整下载检测
**症状**: 脚本只检查目录是否存在，不验证文件完整性
**原因**: Line 104-107 只判断 `local_path.exists()`
**影响**: 如果有文件缺失，脚本不会重新下载

### 问题2: 404错误
**症状**: 下载 `tokenizer.json` 时返回404错误
**原因**: CodeBERT模型不包含 `tokenizer.json` 文件（使用RoBERTa tokenizer）
**影响**: 下载过程报错失败

---

## ✅ 修复方案

### 修复1: 改进文件完整性检查

**文件**: `scripts/download_models.py` (Lines 103-123)

```python
# 修复前: 只检查目录
if local_path.exists() and not force:
    print(f"⚠️  目录已存在: {local_path}")
    print(f"   如需重新下载，请使用 --force 参数")
    return False

# 修复后: 检查每个文件
if local_path.exists() and not force:
    print(f"⚠️  目录已存在: {local_path}")
    print(f"   检查文件完整性...")

    # 检查必要文件是否存在
    missing_files = []
    for url in download_urls:
        parts = url.split('/resolve/main/')
        if len(parts) == 2:
            file_path = parts[1]
            save_path = local_path / file_path
            if not save_path.exists():
                missing_files.append(file_path)

    if not missing_files:
        print(f"✅ 所有文件已存在且完整")
        return True
    else:
        print(f"⚠️  发现 {len(missing_files)} 个缺失文件，将下载缺失部分...")
        print(f"   如需强制重新下载所有文件，请使用 --force 参数")
```

### 修复2: 智能跳过已存在文件

**文件**: `scripts/download_models.py` (Lines 128-159)

```python
# 添加跳过逻辑
skipped_count = 0

for url in download_urls:
    # ... 解析路径 ...

    # 检查文件是否已存在
    if save_path.exists() and not force:
        print(f"⏭️  跳过已存在: {file_path}")
        skipped_count += 1
        success_count += 1
        continue

    # 下载文件
    if download_file(url, save_path, use_mirror, mirror_url):
        success_count += 1
    else:
        failed_files.append(file_path)

# 更新总结信息
if skipped_count > 0:
    print(f"下载完成: {success_count}/{len(download_urls)} 成功 (跳过 {skipped_count} 个已存在)")
```

### 修复3: 移除不存在的 tokenizer.json

**文件**: `config.yaml` (Lines 141-148)

```yaml
download_urls:
  - "https://huggingface.co/microsoft/codebert-base/resolve/main/config.json"
  - "https://huggingface.co/microsoft/codebert-base/resolve/main/pytorch_model.bin"
  # tokenizer.json 不存在于CodeBERT，不需要下载
  # - "https://huggingface.co/microsoft/codebert-base/resolve/main/tokenizer.json"
  - "https://huggingface.co/microsoft/codebert-base/resolve/main/tokenizer_config.json"
  - "https://huggingface.co/microsoft/codebert-base/resolve/main/vocab.json"
  - "https://huggingface.co/microsoft/codebert-base/resolve/main/merges.txt"
```

---

## 🔧 测试验证

### 测试场景1: 缺失文件检测
```bash
# 删除一个文件
rm models/codebert-base/vocab.json

# 重新运行下载
python3 scripts/download_models.py --download code
# 输出:
# ⚠️  目录已存在: models/codebert-base
#    检查文件完整性...
# ⚠️  发现 1 个缺失文件，将下载缺失部分...
# ⏭️  跳过已存在: config.json
# ⏭️  跳过已存在: pytorch_model.bin
# ⏭️  跳过已存在: tokenizer_config.json
# 📥 下载: vocab.json
# ⏭️  跳过已存在: merges.txt
```

### 测试场景2: 完整性验证
```bash
python3 scripts/download_models.py --validate code
# 输出:
# ✅ 存在的文件:
#    - config.json (498 bytes)
#    - pytorch_model.bin (498,627,950 bytes)
#    - tokenizer_config.json (25 bytes)
# ✅ 模型文件完整!
```

---

## 📊 改进效果

| 指标 | 修复前 | 修复后 |
|------|--------|--------|
| 缺失文件检测 | ❌ | ✅ |
| 增量下载 | ❌ | ✅ |
| 404错误处理 | ❌ | ✅ |
| 下载效率 | 重复下载全部 | 只下载缺失 |
| 用户体验 | 需要删除目录重试 | 自动修复缺失 |

---

## 📁 最终文件列表

CodeBERT模型必需文件（5个）:
```
models/codebert-base/
├── config.json         # 498B - 模型配置
├── pytorch_model.bin   # 476M - 模型权重
├── tokenizer_config.json # 25B - 分词器配置
├── vocab.json          # 878K - 词汇表
└── merges.txt          # 446K - BPE合并规则
```

---

## 💡 关键改进

1. **智能检测**: 逐个文件检查，不仅仅检查目录
2. **增量下载**: 跳过已存在文件，只下载缺失部分
3. **错误恢复**: 下载失败不影响已存在文件
4. **用户友好**: 清晰提示缺失文件数量和下载进度
5. **配置修正**: 移除不存在的文件URL，避免404错误

---

**状态**: ✅ 问题已修复
**测试**: ✅ 全部通过
**影响**: 提升下载效率和用户体验
#!/usr/bin/env python3
"""
Hugging Face模型下载工具
支持手动下载模型到指定目录，避免重复下载到缓存
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional
import yaml
import requests
from tqdm import tqdm


def load_config(config_path: str = "./config.yaml") -> dict:
    """加载配置文件"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def download_file(url: str, save_path: Path, use_mirror: bool = False, mirror_url: str = None):
    """
    下载单个文件

    Args:
        url: 下载URL
        save_path: 保存路径
        use_mirror: 是否使用镜像
        mirror_url: 镜像URL
    """
    # 替换为镜像URL
    if use_mirror and mirror_url:
        url = url.replace("https://huggingface.co", mirror_url)

    print(f"📥 下载: {save_path.name}")
    print(f"   URL: {url}")

    try:
        # 发送GET请求
        response = requests.get(url, stream=True, timeout=300)
        response.raise_for_status()

        # 获取文件大小
        total_size = int(response.headers.get('content-length', 0))

        # 创建目录
        save_path.parent.mkdir(parents=True, exist_ok=True)

        # 下载并显示进度条
        with open(save_path, 'wb') as f:
            with tqdm(total=total_size, unit='B', unit_scale=True, desc=save_path.name) as pbar:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))

        print(f"✅ 完成: {save_path}")
        return True

    except requests.exceptions.RequestException as e:
        print(f"❌ 下载失败: {e}")
        return False


def download_model(
    model_type: str,
    config: dict,
    force: bool = False,
    use_mirror: bool = False
) -> bool:
    """
    下载指定类型的模型

    Args:
        model_type: 模型类型 (embedding/code)
        config: 配置字典
        force: 是否强制重新下载
        use_mirror: 是否使用镜像

    Returns:
        是否成功
    """
    models_config = config['models']
    model_config = models_config.get(model_type)

    if not model_config:
        print(f"❌ 未找到模型配置: {model_type}")
        return False

    model_name = model_config['model_name']
    local_path = Path(model_config['local_path'])
    download_urls = model_config.get('download_urls', [])

    print(f"\n{'='*60}")
    print(f"📦 下载 {model_type.upper()} 模型")
    print(f"{'='*60}")
    print(f"模型名称: {model_name}")
    print(f"保存路径: {local_path}")
    print(f"文件数量: {len(download_urls)}")
    print()

    # 检查目录和文件完整性
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

    # 创建目录
    local_path.mkdir(parents=True, exist_ok=True)

    # 下载所有文件（或仅缺失文件）
    success_count = 0
    failed_files = []
    skipped_count = 0

    # 获取镜像配置
    hf_config = models_config['huggingface']
    mirror_url = hf_config.get('mirror_url') if use_mirror else None

    for url in download_urls:
        # 解析文件路径
        # URL格式: https://huggingface.co/{repo}/resolve/main/{path}
        parts = url.split('/resolve/main/')
        if len(parts) == 2:
            file_path = parts[1]

            # 处理子目录 (如 1_Pooling/config.json)
            save_path = local_path / file_path

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

    # 总结
    print(f"\n{'='*60}")
    if skipped_count > 0:
        print(f"下载完成: {success_count}/{len(download_urls)} 成功 (跳过 {skipped_count} 个已存在)")
    else:
        print(f"下载完成: {success_count}/{len(download_urls)} 成功")

    if failed_files:
        print(f"\n❌ 失败文件:")
        for file in failed_files:
            print(f"   - {file}")
        return False
    else:
        print(f"\n✅ 所有文件下载成功!")
        print(f"   模型路径: {local_path}")
        return True


def validate_model(model_type: str, config: dict) -> bool:
    """
    验证模型文件完整性

    Args:
        model_type: 模型类型
        config: 配置字典

    Returns:
        是否有效
    """
    models_config = config['models']
    model_config = models_config.get(model_type)

    if not model_config:
        print(f"❌ 未找到模型配置: {model_type}")
        return False

    local_path = Path(model_config['local_path'])

    print(f"\n{'='*60}")
    print(f"🔍 验证 {model_type.upper()} 模型")
    print(f"{'='*60}")
    print(f"路径: {local_path}")
    print()

    # 检查目录是否存在
    if not local_path.exists():
        print(f"❌ 目录不存在: {local_path}")
        return False

    # 必须存在的文件
    required_files = [
        "config.json",
        "pytorch_model.bin",  # 或 model.safetensors
        "tokenizer_config.json",
    ]

    # 检查文件
    missing_files = []
    existing_files = []

    for file_name in required_files:
        file_path = local_path / file_name
        if file_path.exists():
            size = file_path.stat().st_size
            existing_files.append(f"{file_name} ({size:,} bytes)")
        else:
            # 检查替代文件
            if file_name == "pytorch_model.bin":
                alt_file = local_path / "model.safetensors"
                if alt_file.exists():
                    size = alt_file.stat().st_size
                    existing_files.append(f"model.safetensors ({size:,} bytes)")
                    continue
            missing_files.append(file_name)

    # 输出结果
    print("✅ 存在的文件:")
    for file in existing_files:
        print(f"   - {file}")

    if missing_files:
        print("\n❌ 缺失的文件:")
        for file in missing_files:
            print(f"   - {file}")
        return False
    else:
        print(f"\n✅ 模型文件完整!")
        return True


def list_models(config: dict):
    """列出所有可下载的模型"""
    models_config = config['models']

    print(f"\n{'='*60}")
    print("📦 可用模型列表")
    print(f"{'='*60}\n")

    for model_type in ['embedding', 'code']:
        if model_type not in models_config:
            continue

        model_config = models_config[model_type]
        print(f"[{model_type.upper()}]")
        print(f"  模型名称: {model_config['model_name']}")
        print(f"  本地路径: {model_config['local_path']}")
        print(f"  文件数量: {len(model_config.get('download_urls', []))}")

        # 检查是否已下载
        local_path = Path(model_config['local_path'])
        if local_path.exists():
            print(f"  状态: ✅ 已下载")
        else:
            print(f"  状态: ❌ 未下载")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Hugging Face模型下载工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 列出所有模型
  python3 download_models.py --list

  # 下载embedding模型
  python3 download_models.py --download embedding

  # 下载所有模型
  python3 download_models.py --download all

  # 使用镜像下载
  python3 download_models.py --download embedding --mirror

  # 强制重新下载
  python3 download_models.py --download embedding --force

  # 验证模型文件
  python3 download_models.py --validate embedding
        """
    )

    parser.add_argument(
        '--config',
        type=str,
        default='./config.yaml',
        help='配置文件路径 (默认: ./config.yaml)'
    )

    parser.add_argument(
        '--list',
        action='store_true',
        help='列出所有可用模型'
    )

    parser.add_argument(
        '--download',
        type=str,
        choices=['embedding', 'code', 'all'],
        help='下载指定模型 (embedding/code/all)'
    )

    parser.add_argument(
        '--validate',
        type=str,
        choices=['embedding', 'code', 'all'],
        help='验证模型文件完整性'
    )

    parser.add_argument(
        '--force',
        action='store_true',
        help='强制重新下载 (覆盖已存在的文件)'
    )

    parser.add_argument(
        '--mirror',
        action='store_true',
        help='使用Hugging Face镜像站 (国内加速)'
    )

    args = parser.parse_args()

    # 加载配置
    try:
        config = load_config(args.config)
    except Exception as e:
        print(f"❌ 配置文件加载失败: {e}")
        sys.exit(1)

    # 列出模型
    if args.list:
        list_models(config)
        return

    # 下载模型
    if args.download:
        if args.download == 'all':
            success = True
            for model_type in ['embedding', 'code']:
                if not download_model(model_type, config, args.force, args.mirror):
                    success = False
            sys.exit(0 if success else 1)
        else:
            success = download_model(args.download, config, args.force, args.mirror)
            sys.exit(0 if success else 1)

    # 验证模型
    if args.validate:
        if args.validate == 'all':
            success = True
            for model_type in ['embedding', 'code']:
                if not validate_model(model_type, config):
                    success = False
            sys.exit(0 if success else 1)
        else:
            success = validate_model(args.validate, config)
            sys.exit(0 if success else 1)

    # 未指定操作
    parser.print_help()


if __name__ == "__main__":
    main()

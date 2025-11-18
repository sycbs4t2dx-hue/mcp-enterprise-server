"""
通用工具函数
"""

import hashlib
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def generate_id(prefix: str = "") -> str:
    """
    生成唯一ID

    Args:
        prefix: ID前缀

    Returns:
        格式化的唯一ID

    Example:
        >>> generate_id("mem")
        'mem_20250118_a1b2c3d4'
    """
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    unique_suffix = uuid.uuid4().hex[:8]

    if prefix:
        return f"{prefix}_{timestamp}_{unique_suffix}"
    return f"{timestamp}_{unique_suffix}"


def hash_content(content: str, algorithm: str = "sha256") -> str:
    """
    计算内容哈希值

    Args:
        content: 内容字符串
        algorithm: 哈希算法(md5/sha1/sha256)

    Returns:
        十六进制哈希值
    """
    hash_func = getattr(hashlib, algorithm)()
    hash_func.update(content.encode("utf-8"))
    return hash_func.hexdigest()


def truncate_string(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    截断字符串

    Args:
        text: 原始文本
        max_length: 最大长度
        suffix: 后缀

    Returns:
        截断后的文本
    """
    if len(text) <= max_length:
        return text

    return text[: max_length - len(suffix)] + suffix


def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
    """
    提取关键词(简化版,实际应使用NLP算法)

    Args:
        text: 文本内容
        max_keywords: 最大关键词数

    Returns:
        关键词列表
    """
    # 移除标点,分词
    words = re.findall(r"\b\w{3,}\b", text.lower())

    # 停用词列表(简化)
    stop_words = {
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "by",
        "from",
        "是",
        "的",
        "了",
        "在",
        "和",
        "有",
        "这",
        "个",
        "我",
        "你",
    }

    # 过滤停用词
    keywords = [word for word in words if word not in stop_words]

    # 去重并保持顺序
    seen = set()
    unique_keywords = []
    for kw in keywords:
        if kw not in seen:
            seen.add(kw)
            unique_keywords.append(kw)

    return unique_keywords[:max_keywords]


def calculate_text_similarity(text1: str, text2: str) -> float:
    """
    计算文本相似度(简化版,使用Jaccard相似度)

    Args:
        text1: 文本1
        text2: 文本2

    Returns:
        相似度分数(0-1)
    """
    words1 = set(re.findall(r"\b\w+\b", text1.lower()))
    words2 = set(re.findall(r"\b\w+\b", text2.lower()))

    if not words1 or not words2:
        return 0.0

    intersection = len(words1 & words2)
    union = len(words1 | words2)

    return intersection / union if union > 0 else 0.0


def utc_now() -> datetime:
    """获取当前UTC时间(带时区)"""
    return datetime.now(timezone.utc)


def format_timestamp(dt: datetime, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    格式化时间戳

    Args:
        dt: datetime对象
        fmt: 格式字符串

    Returns:
        格式化后的时间字符串
    """
    return dt.strftime(fmt)


def parse_timestamp(ts_str: str, fmt: str = "%Y-%m-%d %H:%M:%S") -> datetime:
    """
    解析时间字符串

    Args:
        ts_str: 时间字符串
        fmt: 格式字符串

    Returns:
        datetime对象
    """
    return datetime.strptime(ts_str, fmt)


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    安全除法(避免除零错误)

    Args:
        numerator: 分子
        denominator: 分母
        default: 默认值(当分母为0时)

    Returns:
        除法结果
    """
    if denominator == 0:
        return default
    return numerator / denominator


def merge_dicts(*dicts: Dict[str, Any], deep: bool = False) -> Dict[str, Any]:
    """
    合并多个字典

    Args:
        *dicts: 要合并的字典
        deep: 是否深度合并

    Returns:
        合并后的字典
    """
    result: Dict[str, Any] = {}

    for d in dicts:
        if not deep:
            result.update(d)
        else:
            for key, value in d.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = merge_dicts(result[key], value, deep=True)
                else:
                    result[key] = value

    return result


def validate_project_id(project_id: str) -> bool:
    """
    验证项目ID格式

    Args:
        project_id: 项目ID

    Returns:
        是否合法
    """
    # 项目ID规则:字母数字下划线中划线,长度1-64
    pattern = r"^[a-zA-Z0-9_-]{1,64}$"
    return bool(re.match(pattern, project_id))


def sanitize_input(text: str, max_length: int = 10000) -> str:
    """
    清理用户输入(防注入)

    Args:
        text: 原始文本
        max_length: 最大长度

    Returns:
        清理后的文本
    """
    # 移除潜在的SQL/NoSQL注入字符
    dangerous_patterns = [
        r"';",
        r"--",
        r"/\*",
        r"\*/",
        r"xp_",
        r"sp_",
        r"\$where",
        r"\$ne",
    ]

    cleaned = text
    for pattern in dangerous_patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

    # 限制长度
    return cleaned[:max_length]


class Timer:
    """
    简单的计时器上下文管理器

    Example:
        with Timer() as timer:
            # 执行操作
            pass
        print(f"耗时: {timer.elapsed}秒")
    """

    def __init__(self) -> None:
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

    def __enter__(self) -> "Timer":
        self.start_time = datetime.now()
        return self

    def __exit__(self, *args: Any) -> None:
        self.end_time = datetime.now()

    @property
    def elapsed(self) -> float:
        """获取耗时(秒)"""
        if self.start_time is None:
            return 0.0
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()

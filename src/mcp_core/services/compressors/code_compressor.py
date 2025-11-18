"""
代码压缩器
使用AST解析+模式匹配提取核心代码逻辑
"""

import ast
import re
from typing import List, Optional

from ...common.logger import get_logger

logger = get_logger(__name__)


class CodeCompressor:
    """代码压缩器"""

    def __init__(self):
        """初始化代码压缩器"""
        self.preserve_structure = True

    def compress(self, code: str, compression_ratio: float = 0.2) -> str:
        """
        压缩代码

        策略:
        1. 保留函数/类定义(签名)
        2. 提取关键逻辑块
        3. 移除注释和空行
        4. 简化长函数体

        Args:
            code: 原始代码
            compression_ratio: 目标压缩比例(保留比例)

        Returns:
            压缩后的代码
        """
        try:
            # 检测编程语言
            language = self._detect_language(code)

            if language == "python":
                return self._compress_python(code, compression_ratio)
            elif language in ["javascript", "typescript"]:
                return self._compress_javascript(code, compression_ratio)
            else:
                # 通用压缩(移除注释和空行)
                return self._compress_generic(code, compression_ratio)

        except Exception as e:
            logger.warning(f"代码压缩失败,使用降级策略: {e}")
            return self._compress_generic(code, compression_ratio)

    # ==================== Python压缩 ====================

    def _compress_python(self, code: str, ratio: float) -> str:
        """压缩Python代码"""
        try:
            # 解析AST
            tree = ast.parse(code)

            # 提取核心元素
            core_elements = []

            # 1. 提取import语句
            imports = [
                ast.get_source_segment(code, node)
                for node in ast.walk(tree)
                if isinstance(node, (ast.Import, ast.ImportFrom))
            ]
            if imports:
                core_elements.append("# Imports")
                core_elements.extend(imports[:5])  # 最多5个import

            # 2. 提取类定义
            classes = []
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_code = self._extract_class_summary(code, node)
                    if class_code:
                        classes.append(class_code)

            if classes:
                core_elements.append("\n# Classes")
                core_elements.extend(classes)

            # 3. 提取函数定义
            functions = []
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and not self._is_method(node, tree):
                    func_code = self._extract_function_summary(code, node)
                    if func_code:
                        functions.append(func_code)

            if functions:
                core_elements.append("\n# Functions")
                core_elements.extend(functions[:10])  # 最多10个函数

            # 合并结果
            compressed = "\n".join(core_elements)

            # 如果压缩后仍太长,进一步截断
            target_length = int(len(code) * ratio)
            if len(compressed) > target_length:
                compressed = compressed[:target_length] + "\n# ..."

            return compressed.strip()

        except SyntaxError as e:
            logger.debug(f"Python AST解析失败: {e}")
            return self._compress_generic(code, ratio)

    def _extract_class_summary(self, code: str, node: ast.ClassDef) -> Optional[str]:
        """提取类摘要"""
        try:
            # 类签名
            bases = ", ".join(
                ast.get_source_segment(code, base) for base in node.bases
            ) if node.bases else ""
            class_sig = f"class {node.name}({bases}):" if bases else f"class {node.name}:"

            # 文档字符串
            docstring = ast.get_docstring(node)
            if docstring:
                # 只保留第一行
                docstring = docstring.split("\n")[0]
                class_sig += f'\n    """{docstring}"""'

            # 提取方法签名(最多3个)
            methods = []
            for item in node.body[:3]:
                if isinstance(item, ast.FunctionDef):
                    args = ", ".join(arg.arg for arg in item.args.args)
                    methods.append(f"    def {item.name}({args}): ...")

            if methods:
                class_sig += "\n" + "\n".join(methods)

            return class_sig

        except Exception:
            return None

    def _extract_function_summary(self, code: str, node: ast.FunctionDef) -> Optional[str]:
        """提取函数摘要"""
        try:
            # 函数签名
            args = ", ".join(arg.arg for arg in node.args.args)
            func_sig = f"def {node.name}({args}):"

            # 文档字符串
            docstring = ast.get_docstring(node)
            if docstring:
                # 只保留第一行
                docstring = docstring.split("\n")[0]
                func_sig += f'\n    """{docstring}"""'
            else:
                func_sig += "\n    ..."

            return func_sig

        except Exception:
            return None

    def _is_method(self, node: ast.FunctionDef, tree: ast.AST) -> bool:
        """判断函数是否为类方法"""
        for parent in ast.walk(tree):
            if isinstance(parent, ast.ClassDef):
                if node in parent.body:
                    return True
        return False

    # ==================== JavaScript/TypeScript压缩 ====================

    def _compress_javascript(self, code: str, ratio: float) -> str:
        """压缩JavaScript/TypeScript代码"""
        # 简化实现:提取函数和类定义

        # 提取函数定义
        function_pattern = r"(function\s+\w+\s*\([^)]*\)|const\s+\w+\s*=\s*\([^)]*\)\s*=>|class\s+\w+)"
        matches = re.finditer(function_pattern, code)

        core_elements = []
        for match in list(matches)[:15]:  # 最多15个定义
            start = match.start()
            # 提取签名(不包含函数体)
            signature = code[start:start + 200].split("{")[0]
            core_elements.append(signature.strip() + " { ... }")

        compressed = "\n\n".join(core_elements)

        # 长度控制
        target_length = int(len(code) * ratio)
        if len(compressed) > target_length:
            compressed = compressed[:target_length] + "\n// ..."

        return compressed

    # ==================== 通用压缩 ====================

    def _compress_generic(self, code: str, ratio: float) -> str:
        """
        通用代码压缩

        策略:
        1. 移除注释
        2. 移除空行
        3. 保留前N%的代码
        """
        lines = code.split("\n")

        # 移除注释和空行
        cleaned_lines = []
        for line in lines:
            stripped = line.strip()

            # 跳过空行
            if not stripped:
                continue

            # 跳过单行注释
            if stripped.startswith("#") or stripped.startswith("//"):
                continue

            cleaned_lines.append(line)

        # 计算保留行数
        target_lines = max(int(len(cleaned_lines) * ratio), 5)

        # 保留前N行+添加省略号
        compressed_lines = cleaned_lines[:target_lines]
        if len(cleaned_lines) > target_lines:
            compressed_lines.append("# ... (truncated)")

        return "\n".join(compressed_lines)

    # ==================== 辅助方法 ====================

    def _detect_language(self, code: str) -> str:
        """
        检测编程语言

        Returns:
            语言类型(python/javascript/typescript/go/java/unknown)
        """
        # Python特征
        if any(keyword in code for keyword in ["def ", "import ", "class ", "self.", "__init__"]):
            if ":" in code and "def " in code:
                return "python"

        # JavaScript/TypeScript特征
        if any(keyword in code for keyword in ["function ", "const ", "let ", "var ", "=>"]):
            if "interface " in code or ": " in code and "=>" in code:
                return "typescript"
            return "javascript"

        # Go特征
        if "func " in code and "package " in code:
            return "go"

        # Java特征
        if "public class" in code or "private class" in code:
            return "java"

        return "unknown"

    def get_compression_info(self) -> dict:
        """获取压缩器信息"""
        return {
            "compressor": "CodeCompressor",
            "supported_languages": ["python", "javascript", "typescript", "generic"],
            "strategies": [
                "AST parsing (Python)",
                "Pattern matching (JS/TS)",
                "Comment removal (Generic)",
            ],
        }

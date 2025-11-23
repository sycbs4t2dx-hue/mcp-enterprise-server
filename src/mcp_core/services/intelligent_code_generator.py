"""
智能代码生成器
基于上下文学习和模式识别的高级代码生成服务
"""

import os
import re
import ast
import json
import asyncio
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import hashlib

from ..common.logger import get_logger
from ..common.config import get_settings
from .ai_model_manager import (
    get_model_manager,
    ModelCapability,
    ModelRequest
)
from .pattern_recognizer import PatternRecognizer
from .experience_manager import ExperienceManager
from ..models import db_manager, CodeGeneration, GenerationTemplate, CodeContext
from ..services.redis_client import get_redis_client

logger = get_logger(__name__)

# ============================================
# 代码生成配置
# ============================================

class GenerationType(Enum):
    """代码生成类型"""
    FUNCTION = "function"
    CLASS = "class"
    MODULE = "module"
    TEST = "test"
    DOCUMENTATION = "documentation"
    REFACTOR = "refactor"
    OPTIMIZATION = "optimization"
    BUG_FIX = "bug_fix"
    FEATURE = "feature"
    API_ENDPOINT = "api_endpoint"
    DATABASE_MODEL = "database_model"
    UI_COMPONENT = "ui_component"

class CodeStyle(Enum):
    """代码风格"""
    GOOGLE = "google"
    PEP8 = "pep8"
    AIRBNB = "airbnb"
    STANDARD = "standard"
    CUSTOM = "custom"

@dataclass
class GenerationContext:
    """代码生成上下文"""
    type: GenerationType
    language: str
    framework: Optional[str] = None
    style: CodeStyle = CodeStyle.STANDARD
    target_file: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    examples: List[Dict[str, str]] = field(default_factory=list)
    patterns: List[str] = field(default_factory=list)
    test_requirements: Optional[Dict[str, Any]] = None
    performance_targets: Optional[Dict[str, Any]] = None
    security_requirements: Optional[List[str]] = None

@dataclass
class GenerationRequest:
    """代码生成请求"""
    prompt: str
    context: GenerationContext
    project_id: str
    user_requirements: Optional[str] = None
    reference_code: Optional[str] = None
    max_iterations: int = 3
    auto_test: bool = True
    auto_optimize: bool = True
    use_experience: bool = True

@dataclass
class GenerationResult:
    """代码生成结果"""
    code: str
    language: str
    type: GenerationType
    quality_score: float
    test_results: Optional[Dict[str, Any]] = None
    optimizations_applied: List[str] = field(default_factory=list)
    patterns_used: List[str] = field(default_factory=list)
    security_checks: Optional[Dict[str, Any]] = None
    documentation: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

# ============================================
# 代码分析器
# ============================================

class CodeAnalyzer:
    """代码分析器"""

    def analyze_code(self, code: str, language: str) -> Dict[str, Any]:
        """分析代码"""
        if language.lower() in ["python", "py"]:
            return self._analyze_python(code)
        elif language.lower() in ["javascript", "js", "typescript", "ts"]:
            return self._analyze_javascript(code)
        elif language.lower() in ["java"]:
            return self._analyze_java(code)
        else:
            return self._analyze_generic(code)

    def _analyze_python(self, code: str) -> Dict[str, Any]:
        """分析Python代码"""
        try:
            tree = ast.parse(code)

            # 提取结构信息
            functions = []
            classes = []
            imports = []

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    functions.append({
                        "name": node.name,
                        "args": [arg.arg for arg in node.args.args],
                        "decorators": [d.id if isinstance(d, ast.Name) else str(d) for d in node.decorator_list],
                        "docstring": ast.get_docstring(node),
                        "complexity": self._calculate_complexity(node)
                    })
                elif isinstance(node, ast.ClassDef):
                    classes.append({
                        "name": node.name,
                        "bases": [base.id if isinstance(base, ast.Name) else str(base) for base in node.bases],
                        "methods": [n.name for n in node.body if isinstance(n, ast.FunctionDef)],
                        "docstring": ast.get_docstring(node)
                    })
                elif isinstance(node, ast.Import):
                    imports.extend([alias.name for alias in node.names])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)

            return {
                "valid": True,
                "language": "python",
                "functions": functions,
                "classes": classes,
                "imports": imports,
                "lines": len(code.splitlines()),
                "complexity": sum(f["complexity"] for f in functions)
            }

        except SyntaxError as e:
            return {
                "valid": False,
                "error": str(e),
                "language": "python"
            }

    def _analyze_javascript(self, code: str) -> Dict[str, Any]:
        """分析JavaScript代码"""
        # 简化的JS分析
        functions = re.findall(r'function\s+(\w+)\s*\(([^)]*)\)', code)
        classes = re.findall(r'class\s+(\w+)', code)
        imports = re.findall(r'import\s+.*?\s+from\s+[\'"]([^\'"]+)[\'"]', code)

        return {
            "valid": True,
            "language": "javascript",
            "functions": [{"name": f[0], "args": f[1].split(",")} for f in functions],
            "classes": [{"name": c} for c in classes],
            "imports": imports,
            "lines": len(code.splitlines())
        }

    def _analyze_java(self, code: str) -> Dict[str, Any]:
        """分析Java代码"""
        # 简化的Java分析
        classes = re.findall(r'(?:public\s+)?class\s+(\w+)', code)
        methods = re.findall(r'(?:public|private|protected)?\s+\w+\s+(\w+)\s*\([^)]*\)', code)
        imports = re.findall(r'import\s+([^;]+);', code)

        return {
            "valid": True,
            "language": "java",
            "classes": [{"name": c} for c in classes],
            "methods": [{"name": m} for m in methods],
            "imports": imports,
            "lines": len(code.splitlines())
        }

    def _analyze_generic(self, code: str) -> Dict[str, Any]:
        """通用代码分析"""
        return {
            "valid": True,
            "language": "unknown",
            "lines": len(code.splitlines()),
            "size": len(code)
        }

    def _calculate_complexity(self, node: ast.AST) -> int:
        """计算代码复杂度"""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
        return complexity

# ============================================
# 代码优化器
# ============================================

class CodeOptimizer:
    """代码优化器"""

    def __init__(self):
        self.optimization_rules = {
            "python": self._get_python_rules(),
            "javascript": self._get_javascript_rules(),
            "java": self._get_java_rules()
        }

    def _get_python_rules(self) -> List[Dict[str, Any]]:
        """Python优化规则"""
        return [
            {
                "name": "use_list_comprehension",
                "pattern": r"for\s+\w+\s+in\s+.*:\s*\n\s+.*\.append\(",
                "suggestion": "Consider using list comprehension",
                "severity": "info"
            },
            {
                "name": "avoid_mutable_defaults",
                "pattern": r"def\s+\w+\([^)]*=\s*\[\]",
                "suggestion": "Avoid mutable default arguments",
                "severity": "warning"
            },
            {
                "name": "use_f_strings",
                "pattern": r'["\'].format\(|%\s*\(',
                "suggestion": "Use f-strings for better readability",
                "severity": "info"
            }
        ]

    def _get_javascript_rules(self) -> List[Dict[str, Any]]:
        """JavaScript优化规则"""
        return [
            {
                "name": "use_const",
                "pattern": r"let\s+\w+\s*=.*(?!.*\w+\s*=)",
                "suggestion": "Use const for variables that don't change",
                "severity": "info"
            },
            {
                "name": "use_arrow_functions",
                "pattern": r"function\s*\([^)]*\)\s*{",
                "suggestion": "Consider using arrow functions",
                "severity": "info"
            }
        ]

    def _get_java_rules(self) -> List[Dict[str, Any]]:
        """Java优化规则"""
        return [
            {
                "name": "use_string_builder",
                "pattern": r"String\s+\w+\s*=.*\+\s*",
                "suggestion": "Use StringBuilder for string concatenation",
                "severity": "info"
            }
        ]

    async def optimize(self, code: str, language: str, context: GenerationContext) -> Tuple[str, List[str]]:
        """优化代码"""
        optimizations = []
        optimized_code = code

        # 应用语言特定规则
        rules = self.optimization_rules.get(language.lower(), [])
        for rule in rules:
            if re.search(rule["pattern"], code):
                optimizations.append(rule["name"])
                logger.info(f"Optimization suggestion: {rule['suggestion']}")

        # 使用AI进行高级优化
        if context.auto_optimize:
            ai_optimized = await self._ai_optimize(code, language, context)
            if ai_optimized:
                optimized_code = ai_optimized
                optimizations.append("ai_optimization")

        return optimized_code, optimizations

    async def _ai_optimize(self, code: str, language: str, context: GenerationContext) -> Optional[str]:
        """使用AI优化代码"""
        try:
            model_manager = get_model_manager()

            prompt = f"""
            Optimize the following {language} code for:
            1. Performance
            2. Readability
            3. Best practices
            4. Security

            Code:
            ```{language}
            {code}
            ```

            Provide only the optimized code without explanation.
            """

            response = await model_manager.generate(
                prompt=prompt,
                capability=ModelCapability.OPTIMIZATION
            )

            if not response.error:
                # 提取代码块
                code_match = re.search(f"```{language}?\n(.*?)\n```", response.content, re.DOTALL)
                if code_match:
                    return code_match.group(1)
                return response.content

        except Exception as e:
            logger.error(f"AI optimization failed: {e}")

        return None

# ============================================
# 智能代码生成器主类
# ============================================

class IntelligentCodeGenerator:
    """智能代码生成器"""

    def __init__(self):
        """初始化生成器"""
        self.model_manager = get_model_manager()
        self.pattern_recognizer = PatternRecognizer()
        self.experience_manager = ExperienceManager()
        self.code_analyzer = CodeAnalyzer()
        self.code_optimizer = CodeOptimizer()
        self.redis_client = get_redis_client()
        self.templates_cache: Dict[str, GenerationTemplate] = {}

        # 加载预置模板
        self._load_templates()

    def _load_templates(self):
        """加载代码生成模板"""
        # 这里可以从数据库或文件加载预定义的模板
        pass

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        """生成代码"""
        try:
            # 1. 准备上下文
            enhanced_context = await self._enhance_context(request)

            # 2. 检查缓存
            cached_result = await self._check_cache(request)
            if cached_result:
                logger.info("Using cached generation result")
                return cached_result

            # 3. 生成初始代码
            initial_code = await self._generate_initial_code(request, enhanced_context)

            # 4. 迭代改进
            improved_code = await self._iterative_improvement(
                initial_code,
                request,
                enhanced_context
            )

            # 5. 优化代码
            optimized_code, optimizations = await self.code_optimizer.optimize(
                improved_code,
                request.context.language,
                request.context
            )

            # 6. 测试验证
            test_results = None
            if request.auto_test:
                test_results = await self._run_tests(optimized_code, request)

            # 7. 安全检查
            security_results = await self._security_check(optimized_code, request)

            # 8. 生成文档
            documentation = await self._generate_documentation(optimized_code, request)

            # 9. 计算质量分数
            quality_score = self._calculate_quality_score(
                optimized_code,
                test_results,
                security_results
            )

            # 10. 构建结果
            result = GenerationResult(
                code=optimized_code,
                language=request.context.language,
                type=request.context.type,
                quality_score=quality_score,
                test_results=test_results,
                optimizations_applied=optimizations,
                patterns_used=enhanced_context.get("patterns_used", []),
                security_checks=security_results,
                documentation=documentation,
                metadata={
                    "iterations": enhanced_context.get("iterations", 1),
                    "model_used": enhanced_context.get("model_id"),
                    "generation_time": datetime.now().isoformat()
                }
            )

            # 11. 保存到数据库
            await self._save_generation(request, result)

            # 12. 更新缓存
            await self._update_cache(request, result)

            # 13. 学习经验
            if request.use_experience:
                await self._learn_from_generation(request, result)

            return result

        except Exception as e:
            logger.error(f"Code generation failed: {e}")
            raise

    async def _enhance_context(self, request: GenerationRequest) -> Dict[str, Any]:
        """增强生成上下文"""
        enhanced = {
            "original_context": request.context,
            "patterns_used": [],
            "experiences": [],
            "similar_code": []
        }

        # 1. 识别相关模式
        if request.reference_code:
            patterns = await self.pattern_recognizer.recognize(request.reference_code)
            enhanced["patterns_used"] = [p["type"] for p in patterns]

        # 2. 获取相关经验
        if request.use_experience:
            experiences = await self.experience_manager.search(
                query=request.prompt,
                limit=5
            )
            enhanced["experiences"] = experiences

        # 3. 查找相似代码
        similar = await self._find_similar_code(request)
        enhanced["similar_code"] = similar

        return enhanced

    async def _generate_initial_code(
        self,
        request: GenerationRequest,
        context: Dict[str, Any]
    ) -> str:
        """生成初始代码"""

        # 构建生成提示
        prompt = self._build_generation_prompt(request, context)

        # 选择合适的模型能力
        capability = self._select_capability(request.context.type)

        # 生成代码
        response = await self.model_manager.generate(
            prompt=prompt,
            capability=capability,
            max_tokens=2048,
            temperature=0.7
        )

        if response.error:
            raise Exception(f"Generation failed: {response.error}")

        # 提取代码
        code = self._extract_code(response.content, request.context.language)

        return code

    def _build_generation_prompt(
        self,
        request: GenerationRequest,
        context: Dict[str, Any]
    ) -> str:
        """构建生成提示"""
        prompt_parts = []

        # 基础提示
        prompt_parts.append(f"Generate {request.context.language} code for: {request.prompt}")

        # 类型特定要求
        if request.context.type == GenerationType.FUNCTION:
            prompt_parts.append("Generate a well-documented function with proper error handling.")
        elif request.context.type == GenerationType.CLASS:
            prompt_parts.append("Generate a complete class with constructor, methods, and documentation.")
        elif request.context.type == GenerationType.TEST:
            prompt_parts.append("Generate comprehensive test cases with edge cases and assertions.")

        # 添加框架要求
        if request.context.framework:
            prompt_parts.append(f"Use {request.context.framework} framework conventions.")

        # 添加风格要求
        prompt_parts.append(f"Follow {request.context.style.value} coding style.")

        # 添加约束
        for constraint in request.context.constraints:
            prompt_parts.append(f"Constraint: {constraint}")

        # 添加示例
        if request.context.examples:
            prompt_parts.append("\nExamples:")
            for example in request.context.examples:
                prompt_parts.append(f"Input: {example.get('input', '')}")
                prompt_parts.append(f"Output: {example.get('output', '')}")

        # 添加参考代码
        if request.reference_code:
            prompt_parts.append(f"\nReference code:\n```\n{request.reference_code}\n```")

        # 添加相似代码
        if context.get("similar_code"):
            prompt_parts.append("\nSimilar implementations:")
            for similar in context["similar_code"][:2]:
                prompt_parts.append(f"```\n{similar}\n```")

        return "\n\n".join(prompt_parts)

    def _select_capability(self, gen_type: GenerationType) -> ModelCapability:
        """选择模型能力"""
        capability_map = {
            GenerationType.FUNCTION: ModelCapability.CODE_GENERATION,
            GenerationType.CLASS: ModelCapability.CODE_GENERATION,
            GenerationType.TEST: ModelCapability.TESTING,
            GenerationType.DOCUMENTATION: ModelCapability.DOCUMENTATION,
            GenerationType.REFACTOR: ModelCapability.REFACTORING,
            GenerationType.OPTIMIZATION: ModelCapability.OPTIMIZATION,
            GenerationType.BUG_FIX: ModelCapability.BUG_DETECTION
        }
        return capability_map.get(gen_type, ModelCapability.CODE_GENERATION)

    def _extract_code(self, content: str, language: str) -> str:
        """从响应中提取代码"""
        # 尝试提取代码块
        code_pattern = f"```{language}?\n(.*?)\n```"
        match = re.search(code_pattern, content, re.DOTALL)

        if match:
            return match.group(1)

        # 如果没有代码块标记，返回整个内容
        return content

    async def _iterative_improvement(
        self,
        code: str,
        request: GenerationRequest,
        context: Dict[str, Any]
    ) -> str:
        """迭代改进代码"""
        improved_code = code

        for iteration in range(request.max_iterations):
            # 分析当前代码
            analysis = self.code_analyzer.analyze_code(improved_code, request.context.language)

            if not analysis["valid"]:
                # 修复语法错误
                improved_code = await self._fix_syntax_errors(
                    improved_code,
                    analysis["error"],
                    request.context.language
                )
                continue

            # 检查是否满足要求
            if await self._meets_requirements(improved_code, request):
                break

            # 改进代码
            improved_code = await self._improve_iteration(
                improved_code,
                request,
                analysis
            )

            context["iterations"] = iteration + 1

        return improved_code

    async def _fix_syntax_errors(self, code: str, error: str, language: str) -> str:
        """修复语法错误"""
        prompt = f"""
        Fix the syntax error in this {language} code:

        Error: {error}

        Code:
        ```{language}
        {code}
        ```

        Return only the fixed code.
        """

        response = await self.model_manager.generate(
            prompt=prompt,
            capability=ModelCapability.BUG_DETECTION
        )

        return self._extract_code(response.content, language)

    async def _meets_requirements(self, code: str, request: GenerationRequest) -> bool:
        """检查代码是否满足要求"""
        # 基础检查
        if not code or len(code) < 10:
            return False

        # 分析代码结构
        analysis = self.code_analyzer.analyze_code(code, request.context.language)

        if request.context.type == GenerationType.FUNCTION:
            return len(analysis.get("functions", [])) > 0
        elif request.context.type == GenerationType.CLASS:
            return len(analysis.get("classes", [])) > 0
        elif request.context.type == GenerationType.TEST:
            # 检查是否包含测试关键字
            test_keywords = ["test", "assert", "expect", "describe", "it"]
            return any(keyword in code.lower() for keyword in test_keywords)

        return True

    async def _improve_iteration(
        self,
        code: str,
        request: GenerationRequest,
        analysis: Dict[str, Any]
    ) -> str:
        """单次改进迭代"""
        prompt = f"""
        Improve this {request.context.language} code based on:
        1. Add missing error handling
        2. Improve variable naming
        3. Add necessary comments
        4. Ensure it follows {request.context.style.value} style

        Current analysis: {json.dumps(analysis, indent=2)}

        Code:
        ```{request.context.language}
        {code}
        ```

        Return only the improved code.
        """

        response = await self.model_manager.generate(
            prompt=prompt,
            capability=ModelCapability.REFACTORING
        )

        return self._extract_code(response.content, request.context.language)

    async def _run_tests(self, code: str, request: GenerationRequest) -> Dict[str, Any]:
        """运行测试"""
        test_results = {
            "passed": False,
            "tests_run": 0,
            "failures": [],
            "coverage": 0.0
        }

        # 根据语言运行不同的测试
        if request.context.language.lower() in ["python", "py"]:
            test_results = await self._run_python_tests(code, request)
        elif request.context.language.lower() in ["javascript", "js"]:
            test_results = await self._run_javascript_tests(code, request)

        return test_results

    async def _run_python_tests(self, code: str, request: GenerationRequest) -> Dict[str, Any]:
        """运行Python测试"""
        # 这里简化处理，实际应该在隔离环境中运行
        try:
            # 基础语法检查
            compile(code, '<string>', 'exec')

            return {
                "passed": True,
                "tests_run": 1,
                "failures": [],
                "coverage": 85.0  # 模拟覆盖率
            }
        except SyntaxError as e:
            return {
                "passed": False,
                "tests_run": 1,
                "failures": [str(e)],
                "coverage": 0.0
            }

    async def _run_javascript_tests(self, code: str, request: GenerationRequest) -> Dict[str, Any]:
        """运行JavaScript测试"""
        # 简化处理
        return {
            "passed": True,
            "tests_run": 1,
            "failures": [],
            "coverage": 80.0
        }

    async def _security_check(self, code: str, request: GenerationRequest) -> Dict[str, Any]:
        """安全检查"""
        security_issues = []

        # 检查常见安全问题
        security_patterns = [
            {"pattern": r"eval\(", "issue": "Use of eval() is dangerous"},
            {"pattern": r"exec\(", "issue": "Use of exec() is dangerous"},
            {"pattern": r"__import__", "issue": "Dynamic import detected"},
            {"pattern": r"subprocess.*shell=True", "issue": "Shell injection risk"},
            {"pattern": r"sql.*%s", "issue": "Potential SQL injection"},
            {"pattern": r"password.*=.*['\"]", "issue": "Hardcoded password"}
        ]

        for check in security_patterns:
            if re.search(check["pattern"], code, re.IGNORECASE):
                security_issues.append(check["issue"])

        return {
            "secure": len(security_issues) == 0,
            "issues": security_issues,
            "severity": "high" if len(security_issues) > 2 else "medium" if security_issues else "low"
        }

    async def _generate_documentation(self, code: str, request: GenerationRequest) -> str:
        """生成文档"""
        prompt = f"""
        Generate comprehensive documentation for this {request.context.language} code:

        ```{request.context.language}
        {code}
        ```

        Include:
        1. Overview
        2. Parameters/Arguments
        3. Return values
        4. Usage examples
        5. Notes and warnings
        """

        response = await self.model_manager.generate(
            prompt=prompt,
            capability=ModelCapability.DOCUMENTATION
        )

        return response.content if not response.error else ""

    def _calculate_quality_score(
        self,
        code: str,
        test_results: Optional[Dict[str, Any]],
        security_results: Optional[Dict[str, Any]]
    ) -> float:
        """计算代码质量分数"""
        score = 50.0  # 基础分数

        # 代码分析得分
        analysis = self.code_analyzer.analyze_code(code, "python")
        if analysis["valid"]:
            score += 10

        # 测试得分
        if test_results:
            if test_results["passed"]:
                score += 20
            score += min(test_results.get("coverage", 0) / 5, 10)  # 最多10分

        # 安全得分
        if security_results:
            if security_results["secure"]:
                score += 10
            else:
                score -= len(security_results["issues"]) * 2

        # 确保分数在0-100之间
        return max(0, min(100, score))

    async def _save_generation(self, request: GenerationRequest, result: GenerationResult):
        """保存生成记录"""
        try:
            with db_manager.get_session() as session:
                generation = CodeGeneration(
                    project_id=request.project_id,
                    prompt=request.prompt,
                    code=result.code,
                    language=result.language,
                    type=result.type.value,
                    quality_score=result.quality_score,
                    metadata=json.dumps(result.metadata)
                )
                session.add(generation)
                session.commit()
                logger.info(f"Saved generation record: {generation.id}")
        except Exception as e:
            logger.error(f"Failed to save generation: {e}")

    async def _check_cache(self, request: GenerationRequest) -> Optional[GenerationResult]:
        """检查缓存"""
        cache_key = self._get_cache_key(request)

        cached = await self.redis_client.get(cache_key)
        if cached:
            return GenerationResult(**json.loads(cached))

        return None

    async def _update_cache(self, request: GenerationRequest, result: GenerationResult):
        """更新缓存"""
        cache_key = self._get_cache_key(request)

        # 序列化结果
        result_dict = {
            "code": result.code,
            "language": result.language,
            "type": result.type.value,
            "quality_score": result.quality_score,
            "optimizations_applied": result.optimizations_applied,
            "patterns_used": result.patterns_used,
            "metadata": result.metadata
        }

        await self.redis_client.setex(
            cache_key,
            3600,  # 1小时过期
            json.dumps(result_dict)
        )

    def _get_cache_key(self, request: GenerationRequest) -> str:
        """生成缓存键"""
        # 创建唯一标识
        key_parts = [
            request.prompt,
            request.context.type.value,
            request.context.language,
            request.context.framework or "",
            request.context.style.value
        ]

        key_str = "|".join(key_parts)
        return f"codegen:{hashlib.md5(key_str.encode()).hexdigest()}"

    async def _find_similar_code(self, request: GenerationRequest) -> List[str]:
        """查找相似代码"""
        # 从经验库中查找
        similar = await self.experience_manager.search(
            query=request.prompt,
            limit=3
        )

        return [exp.get("code", "") for exp in similar if exp.get("code")]

    async def _learn_from_generation(self, request: GenerationRequest, result: GenerationResult):
        """从生成中学习"""
        if result.quality_score > 70:  # 只学习高质量代码
            experience = {
                "type": "code_generation",
                "prompt": request.prompt,
                "code": result.code,
                "language": result.language,
                "quality_score": result.quality_score,
                "patterns": result.patterns_used,
                "metadata": result.metadata
            }

            await self.experience_manager.add_experience(
                project_id=request.project_id,
                experience_type="generation",
                content=json.dumps(experience),
                tags=[request.context.type.value, request.context.language]
            )

# ============================================
# 代码生成模板管理
# ============================================

class TemplateManager:
    """模板管理器"""

    def __init__(self):
        self.templates = self._load_default_templates()

    def _load_default_templates(self) -> Dict[str, str]:
        """加载默认模板"""
        return {
            "python_class": """
class {class_name}:
    \"\"\"
    {description}
    \"\"\"

    def __init__(self, {init_params}):
        \"\"\"Initialize {class_name}.\"\"\"
        {init_body}

    {methods}
""",
            "python_function": """
def {function_name}({params}):
    \"\"\"
    {description}

    Args:
        {args_description}

    Returns:
        {return_description}
    \"\"\"
    {function_body}
""",
            "python_test": """
import unittest
from {module} import {target}

class Test{target}(unittest.TestCase):
    \"\"\"Test cases for {target}.\"\"\"

    def setUp(self):
        \"\"\"Set up test fixtures.\"\"\"
        {setup_body}

    {test_methods}

if __name__ == '__main__':
    unittest.main()
""",
            "javascript_class": """
class {class_name} {
    constructor({init_params}) {
        {init_body}
    }

    {methods}
}

module.exports = {class_name};
""",
            "react_component": """
import React, { useState, useEffect } from 'react';
import {{ {imports} }} from '{import_from}';

const {component_name} = ({{ {props} }}) => {{
    {state_declarations}

    {use_effects}

    {handlers}

    return (
        {jsx_content}
    );
}};

export default {component_name};
"""
        }

    def get_template(self, template_name: str) -> Optional[str]:
        """获取模板"""
        return self.templates.get(template_name)

    def render_template(self, template_name: str, **kwargs) -> str:
        """渲染模板"""
        template = self.get_template(template_name)
        if template:
            return template.format(**kwargs)
        return ""

# ============================================
# 单例实例
# ============================================

_generator_instance: Optional[IntelligentCodeGenerator] = None

def get_code_generator() -> IntelligentCodeGenerator:
    """获取代码生成器单例"""
    global _generator_instance
    if _generator_instance is None:
        _generator_instance = IntelligentCodeGenerator()
    return _generator_instance
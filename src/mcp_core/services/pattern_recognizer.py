"""
高级模式识别器 - 智能代码模式学习与识别
支持深度学习、模式演化、自动分类
"""

import re
import ast
import json
import hashlib
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict, Counter
import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.feature_extraction.text import TfidfVectorizer

from ..common.logger import get_logger
from ..services.embedding_service import get_embedding_service

logger = get_logger(__name__)

# ============================================
# 数据模型
# ============================================

@dataclass
class PatternFeature:
    """模式特征"""
    feature_type: str  # structural, semantic, behavioral
    feature_name: str
    feature_value: Any
    weight: float = 1.0
    confidence: float = 1.0

@dataclass
class CodePattern:
    """增强版代码模式"""
    pattern_id: str
    pattern_type: str  # design, anti-pattern, idiom, refactoring
    pattern_name: str
    pattern_category: str
    pattern_description: str

    # 模式内容
    pattern_template: str
    pattern_signature: str
    pattern_ast: Optional[dict] = None

    # 模式特征
    features: List[PatternFeature] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    context_requirements: Dict[str, Any] = field(default_factory=dict)

    # 使用统计
    occurrences: List[Dict[str, Any]] = field(default_factory=list)
    success_rate: float = 0.0
    effectiveness: float = 0.0
    evolution_stage: int = 1  # 演化阶段

    # 关系
    parent_pattern: Optional[str] = None
    child_patterns: List[str] = field(default_factory=list)
    similar_patterns: List[str] = field(default_factory=list)

    # 元数据
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)

@dataclass
class PatternCluster:
    """模式聚类"""
    cluster_id: str
    cluster_type: str
    patterns: List[str]  # pattern_ids
    centroid: np.ndarray
    radius: float
    density: float
    representative_pattern: str

# ============================================
# 高级模式识别器
# ============================================

class AdvancedPatternRecognizer:
    """高级模式识别器"""

    def __init__(self):
        """初始化识别器"""
        self.embedding_service = get_embedding_service()

        # 模式库
        self.patterns: Dict[str, CodePattern] = {}
        self.pattern_index: Dict[str, Set[str]] = defaultdict(set)  # type -> pattern_ids

        # 特征提取器
        self.feature_extractors = {
            "structural": self.extract_structural_features,
            "semantic": self.extract_semantic_features,
            "behavioral": self.extract_behavioral_features,
            "quality": self.extract_quality_features
        }

        # 模式分类器
        self.pattern_classifiers = {
            "design_pattern": self.classify_design_pattern,
            "anti_pattern": self.classify_anti_pattern,
            "code_smell": self.classify_code_smell,
            "optimization": self.classify_optimization_pattern
        }

        # TF-IDF向量化器
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=100,
            ngram_range=(1, 3),
            min_df=0.01
        )

        # 聚类器
        self.clusterer = DBSCAN(eps=0.3, min_samples=2, metric='cosine')

        # 演化追踪
        self.evolution_history: Dict[str, List[Dict]] = defaultdict(list)

        logger.info("高级模式识别器初始化完成")

    # ============================================
    # 核心识别功能
    # ============================================

    def recognize_patterns(
        self,
        code: str,
        context: Dict[str, Any],
        deep_analysis: bool = True
    ) -> List[CodePattern]:
        """
        识别代码模式

        Args:
            code: 代码文本
            context: 上下文信息
            deep_analysis: 是否进行深度分析

        Returns:
            识别到的模式列表
        """
        patterns = []

        try:
            # 1. 预处理
            preprocessed = self.preprocess_code(code)

            # 2. 提取特征
            features = self.extract_all_features(preprocessed, context)

            # 3. 快速模式匹配
            quick_matches = self.quick_pattern_match(features)
            patterns.extend(quick_matches)

            if deep_analysis:
                # 4. 深度分析
                deep_patterns = self.deep_pattern_analysis(preprocessed, features, context)
                patterns.extend(deep_patterns)

                # 5. 模式组合识别
                composite_patterns = self.recognize_composite_patterns(patterns)
                patterns.extend(composite_patterns)

                # 6. 反模式检测
                anti_patterns = self.detect_anti_patterns(preprocessed, features)
                patterns.extend(anti_patterns)

            # 7. 去重和排序
            patterns = self.deduplicate_and_rank(patterns)

            # 8. 更新模式库
            self.update_pattern_library(patterns, context)

            logger.info(f"识别到 {len(patterns)} 个模式")

        except Exception as e:
            logger.error(f"模式识别失败: {e}")

        return patterns

    def preprocess_code(self, code: str) -> Dict[str, Any]:
        """预处理代码"""
        preprocessed = {
            "raw": code,
            "normalized": self.normalize_code(code),
            "tokens": self.tokenize_code(code),
            "ast": None,
            "metrics": {}
        }

        # 尝试解析AST
        try:
            preprocessed["ast"] = ast.parse(code)
        except:
            pass

        # 计算基础指标
        preprocessed["metrics"] = {
            "lines": len(code.split('\n')),
            "chars": len(code),
            "complexity": self.calculate_complexity(code)
        }

        return preprocessed

    def extract_all_features(
        self,
        preprocessed: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, List[PatternFeature]]:
        """提取所有特征"""
        all_features = {}

        for feature_type, extractor in self.feature_extractors.items():
            features = extractor(preprocessed, context)
            all_features[feature_type] = features

        return all_features

    # ============================================
    # 特征提取
    # ============================================

    def extract_structural_features(
        self,
        preprocessed: Dict[str, Any],
        context: Dict[str, Any]
    ) -> List[PatternFeature]:
        """提取结构特征"""
        features = []

        if preprocessed["ast"]:
            # AST特征
            for node in ast.walk(preprocessed["ast"]):
                if isinstance(node, ast.ClassDef):
                    features.append(PatternFeature(
                        "structural", "class_definition",
                        {"name": node.name, "bases": len(node.bases)},
                        weight=2.0
                    ))
                elif isinstance(node, ast.FunctionDef):
                    features.append(PatternFeature(
                        "structural", "function_definition",
                        {"name": node.name, "args": len(node.args.args)},
                        weight=1.5
                    ))
                elif isinstance(node, ast.For):
                    features.append(PatternFeature(
                        "structural", "loop_structure", "for_loop", weight=1.0
                    ))
                elif isinstance(node, ast.If):
                    features.append(PatternFeature(
                        "structural", "conditional", "if_statement", weight=1.0
                    ))
                elif isinstance(node, ast.Try):
                    features.append(PatternFeature(
                        "structural", "exception_handling", "try_except", weight=1.2
                    ))

        # 代码结构模式
        code = preprocessed["raw"]

        # 装饰器模式
        if "@" in code:
            decorators = re.findall(r'@\w+', code)
            for decorator in decorators:
                features.append(PatternFeature(
                    "structural", "decorator", decorator, weight=1.5
                ))

        # 上下文管理器
        if "with " in code:
            features.append(PatternFeature(
                "structural", "context_manager", "with_statement", weight=1.3
            ))

        # 生成器模式
        if "yield" in code:
            features.append(PatternFeature(
                "structural", "generator", "yield_statement", weight=1.4
            ))

        # Lambda表达式
        if "lambda" in code:
            features.append(PatternFeature(
                "structural", "lambda", "lambda_expression", weight=1.1
            ))

        return features

    def extract_semantic_features(
        self,
        preprocessed: Dict[str, Any],
        context: Dict[str, Any]
    ) -> List[PatternFeature]:
        """提取语义特征"""
        features = []
        code = preprocessed["raw"]

        # 命名模式
        # 驼峰命名
        camel_case = re.findall(r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)*\b', code)
        if camel_case:
            features.append(PatternFeature(
                "semantic", "naming_convention", "camel_case",
                weight=0.8, confidence=len(camel_case) / 10
            ))

        # 下划线命名
        snake_case = re.findall(r'\b[a-z]+(?:_[a-z]+)+\b', code)
        if snake_case:
            features.append(PatternFeature(
                "semantic", "naming_convention", "snake_case",
                weight=0.8, confidence=len(snake_case) / 10
            ))

        # 设计意图
        # 单例模式特征
        if "instance" in code.lower() and "get" in code.lower():
            features.append(PatternFeature(
                "semantic", "design_intent", "singleton_like", weight=1.5
            ))

        # 工厂模式特征
        if "create" in code.lower() or "factory" in code.lower():
            features.append(PatternFeature(
                "semantic", "design_intent", "factory_like", weight=1.5
            ))

        # 观察者模式特征
        if "observer" in code.lower() or "listener" in code.lower():
            features.append(PatternFeature(
                "semantic", "design_intent", "observer_like", weight=1.5
            ))

        # 策略模式特征
        if "strategy" in code.lower() or "algorithm" in code.lower():
            features.append(PatternFeature(
                "semantic", "design_intent", "strategy_like", weight=1.5
            ))

        # 文档字符串
        docstrings = re.findall(r'""".*?"""', code, re.DOTALL)
        if docstrings:
            features.append(PatternFeature(
                "semantic", "documentation", "docstring",
                weight=1.0, confidence=len(docstrings) / 5
            ))

        return features

    def extract_behavioral_features(
        self,
        preprocessed: Dict[str, Any],
        context: Dict[str, Any]
    ) -> List[PatternFeature]:
        """提取行为特征"""
        features = []
        code = preprocessed["raw"]

        # 递归模式
        if preprocessed["ast"]:
            for node in ast.walk(preprocessed["ast"]):
                if isinstance(node, ast.FunctionDef):
                    # 检查函数是否调用自己
                    for inner_node in ast.walk(node):
                        if isinstance(inner_node, ast.Call):
                            if hasattr(inner_node.func, 'id') and inner_node.func.id == node.name:
                                features.append(PatternFeature(
                                    "behavioral", "recursion", node.name, weight=1.6
                                ))

        # 迭代模式
        if "for " in code or "while " in code:
            features.append(PatternFeature(
                "behavioral", "iteration", "loop", weight=1.0
            ))

        # 缓存模式
        if "cache" in code.lower() or "memoize" in code.lower():
            features.append(PatternFeature(
                "behavioral", "caching", "cache_pattern", weight=1.4
            ))

        # 延迟加载
        if "lazy" in code.lower() or "@property" in code:
            features.append(PatternFeature(
                "behavioral", "lazy_loading", "lazy_pattern", weight=1.3
            ))

        # 回调模式
        if "callback" in code.lower() or "on_" in code:
            features.append(PatternFeature(
                "behavioral", "callback", "callback_pattern", weight=1.2
            ))

        # 链式调用
        chain_calls = re.findall(r'\.\w+\([^)]*\)\.\w+', code)
        if chain_calls:
            features.append(PatternFeature(
                "behavioral", "chaining", "method_chaining", weight=1.3
            ))

        return features

    def extract_quality_features(
        self,
        preprocessed: Dict[str, Any],
        context: Dict[str, Any]
    ) -> List[PatternFeature]:
        """提取质量特征"""
        features = []
        code = preprocessed["raw"]
        lines = code.split('\n')

        # 代码复杂度
        complexity = preprocessed["metrics"]["complexity"]
        if complexity > 10:
            features.append(PatternFeature(
                "quality", "high_complexity", complexity,
                weight=0.5, confidence=min(complexity / 20, 1.0)
            ))

        # 代码重复
        duplicate_lines = self.detect_duplicates(lines)
        if duplicate_lines > 5:
            features.append(PatternFeature(
                "quality", "code_duplication", duplicate_lines,
                weight=0.6, confidence=min(duplicate_lines / 10, 1.0)
            ))

        # 长方法
        if preprocessed["ast"]:
            for node in ast.walk(preprocessed["ast"]):
                if isinstance(node, ast.FunctionDef):
                    func_lines = node.end_lineno - node.lineno if hasattr(node, 'end_lineno') else 0
                    if func_lines > 30:
                        features.append(PatternFeature(
                            "quality", "long_method", node.name,
                            weight=0.7, confidence=min(func_lines / 50, 1.0)
                        ))

        # 嵌套深度
        max_indent = max((len(line) - len(line.lstrip()) for line in lines if line.strip()), default=0)
        if max_indent > 12:  # 3级嵌套以上
            features.append(PatternFeature(
                "quality", "deep_nesting", max_indent // 4,
                weight=0.8, confidence=min(max_indent / 20, 1.0)
            ))

        # 魔法数字
        magic_numbers = re.findall(r'\b\d+\b', code)
        magic_count = len([n for n in magic_numbers if n not in ['0', '1', '2']])
        if magic_count > 3:
            features.append(PatternFeature(
                "quality", "magic_numbers", magic_count,
                weight=0.5, confidence=min(magic_count / 10, 1.0)
            ))

        return features

    # ============================================
    # 模式匹配与分析
    # ============================================

    def quick_pattern_match(
        self,
        features: Dict[str, List[PatternFeature]]
    ) -> List[CodePattern]:
        """快速模式匹配"""
        matched_patterns = []

        # 将特征转换为特征向量
        feature_vector = self.features_to_vector(features)

        # 与已知模式匹配
        for pattern_id, pattern in self.patterns.items():
            similarity = self.calculate_pattern_similarity(feature_vector, pattern)
            if similarity > 0.7:
                matched_patterns.append(pattern)

        return matched_patterns

    def deep_pattern_analysis(
        self,
        preprocessed: Dict[str, Any],
        features: Dict[str, List[PatternFeature]],
        context: Dict[str, Any]
    ) -> List[CodePattern]:
        """深度模式分析"""
        patterns = []

        # 1. 使用机器学习分类
        for classifier_type, classifier in self.pattern_classifiers.items():
            classified = classifier(preprocessed, features, context)
            if classified:
                patterns.extend(classified)

        # 2. 模式演化检测
        evolved_patterns = self.detect_pattern_evolution(features, context)
        patterns.extend(evolved_patterns)

        # 3. 新模式发现
        new_patterns = self.discover_new_patterns(preprocessed, features)
        patterns.extend(new_patterns)

        return patterns

    def recognize_composite_patterns(
        self,
        base_patterns: List[CodePattern]
    ) -> List[CodePattern]:
        """识别组合模式"""
        composite_patterns = []

        # 检查常见的模式组合
        pattern_names = {p.pattern_name for p in base_patterns}

        # MVC模式
        if {"model", "view", "controller"}.issubset(pattern_names):
            composite_patterns.append(self.create_pattern(
                "composite", "MVC",
                "Model-View-Controller架构模式",
                child_patterns=[p.pattern_id for p in base_patterns if p.pattern_name in ["model", "view", "controller"]]
            ))

        # 装饰器链
        decorator_patterns = [p for p in base_patterns if "decorator" in p.pattern_type]
        if len(decorator_patterns) > 2:
            composite_patterns.append(self.create_pattern(
                "composite", "decorator_chain",
                "装饰器链模式",
                child_patterns=[p.pattern_id for p in decorator_patterns]
            ))

        # 策略+工厂
        if "strategy" in pattern_names and "factory" in pattern_names:
            composite_patterns.append(self.create_pattern(
                "composite", "strategy_factory",
                "策略工厂组合模式"
            ))

        return composite_patterns

    def detect_anti_patterns(
        self,
        preprocessed: Dict[str, Any],
        features: Dict[str, List[PatternFeature]]
    ) -> List[CodePattern]:
        """检测反模式"""
        anti_patterns = []

        # 检查质量特征
        quality_features = features.get("quality", [])

        for feature in quality_features:
            if feature.feature_name == "high_complexity" and feature.confidence > 0.7:
                anti_patterns.append(self.create_pattern(
                    "anti_pattern", "spaghetti_code",
                    "意大利面条式代码 - 过度复杂"
                ))

            elif feature.feature_name == "code_duplication" and feature.confidence > 0.6:
                anti_patterns.append(self.create_pattern(
                    "anti_pattern", "copy_paste",
                    "复制粘贴编程 - 代码重复"
                ))

            elif feature.feature_name == "deep_nesting" and feature.confidence > 0.8:
                anti_patterns.append(self.create_pattern(
                    "anti_pattern", "arrow_anti_pattern",
                    "箭头反模式 - 过度嵌套"
                ))

            elif feature.feature_name == "long_method" and feature.confidence > 0.7:
                anti_patterns.append(self.create_pattern(
                    "anti_pattern", "god_method",
                    "上帝方法 - 方法过长"
                ))

        # 检查结构特征
        structural_features = features.get("structural", [])

        # 检查是否有过多的全局变量
        global_vars = [f for f in structural_features if f.feature_name == "global_variable"]
        if len(global_vars) > 5:
            anti_patterns.append(self.create_pattern(
                "anti_pattern", "global_pollution",
                "全局污染 - 过多全局变量"
            ))

        return anti_patterns

    # ============================================
    # 分类器
    # ============================================

    def classify_design_pattern(
        self,
        preprocessed: Dict[str, Any],
        features: Dict[str, List[PatternFeature]],
        context: Dict[str, Any]
    ) -> List[CodePattern]:
        """分类设计模式"""
        patterns = []

        semantic_features = features.get("semantic", [])
        structural_features = features.get("structural", [])

        # 单例模式检测
        singleton_indicators = 0
        for f in semantic_features:
            if f.feature_value == "singleton_like":
                singleton_indicators += 1
        for f in structural_features:
            if f.feature_name == "class_definition":
                class_info = f.feature_value
                # 检查是否有getInstance或类似方法
                if "instance" in str(class_info).lower():
                    singleton_indicators += 1

        if singleton_indicators >= 2:
            patterns.append(self.create_pattern(
                "design_pattern", "singleton",
                "单例模式 - 确保类只有一个实例"
            ))

        # 工厂模式检测
        factory_indicators = 0
        for f in semantic_features:
            if f.feature_value == "factory_like":
                factory_indicators += 1

        if factory_indicators > 0:
            patterns.append(self.create_pattern(
                "design_pattern", "factory",
                "工厂模式 - 创建对象的接口"
            ))

        # 观察者模式检测
        observer_indicators = 0
        for f in semantic_features:
            if f.feature_value == "observer_like":
                observer_indicators += 1
        for f in behavioral_features:
            if f.feature_value == "callback_pattern":
                observer_indicators += 1

        if observer_indicators >= 2:
            patterns.append(self.create_pattern(
                "design_pattern", "observer",
                "观察者模式 - 定义对象间的一对多依赖"
            ))

        return patterns

    def classify_anti_pattern(
        self,
        preprocessed: Dict[str, Any],
        features: Dict[str, List[PatternFeature]],
        context: Dict[str, Any]
    ) -> List[CodePattern]:
        """分类反模式"""
        # 已在detect_anti_patterns中实现
        return []

    def classify_code_smell(
        self,
        preprocessed: Dict[str, Any],
        features: Dict[str, List[PatternFeature]],
        context: Dict[str, Any]
    ) -> List[CodePattern]:
        """分类代码异味"""
        patterns = []

        quality_features = features.get("quality", [])

        # 长参数列表
        if preprocessed["ast"]:
            for node in ast.walk(preprocessed["ast"]):
                if isinstance(node, ast.FunctionDef):
                    if len(node.args.args) > 5:
                        patterns.append(self.create_pattern(
                            "code_smell", "long_parameter_list",
                            f"长参数列表 - {node.name}有{len(node.args.args)}个参数"
                        ))

        # 注释过多
        code = preprocessed["raw"]
        comment_lines = len([l for l in code.split('\n') if l.strip().startswith('#')])
        total_lines = len(code.split('\n'))
        if total_lines > 0 and comment_lines / total_lines > 0.5:
            patterns.append(self.create_pattern(
                "code_smell", "excessive_comments",
                "过多注释 - 可能代码不够清晰"
            ))

        # 死代码
        if "return" in code:
            # 检查return后是否还有代码
            lines = code.split('\n')
            for i, line in enumerate(lines):
                if 'return' in line and i < len(lines) - 1:
                    # 检查同一缩进级别是否还有代码
                    indent = len(line) - len(line.lstrip())
                    for j in range(i + 1, len(lines)):
                        next_line = lines[j]
                        if next_line.strip() and len(next_line) - len(next_line.lstrip()) == indent:
                            patterns.append(self.create_pattern(
                                "code_smell", "dead_code",
                                "死代码 - return后存在不可达代码"
                            ))
                            break

        return patterns

    def classify_optimization_pattern(
        self,
        preprocessed: Dict[str, Any],
        features: Dict[str, List[PatternFeature]],
        context: Dict[str, Any]
    ) -> List[CodePattern]:
        """分类优化模式"""
        patterns = []

        behavioral_features = features.get("behavioral", [])

        # 缓存优化
        for f in behavioral_features:
            if f.feature_value == "cache_pattern":
                patterns.append(self.create_pattern(
                    "optimization", "caching",
                    "缓存优化 - 避免重复计算"
                ))

        # 延迟加载优化
        for f in behavioral_features:
            if f.feature_value == "lazy_pattern":
                patterns.append(self.create_pattern(
                    "optimization", "lazy_loading",
                    "延迟加载 - 按需初始化"
                ))

        # 批处理优化
        code = preprocessed["raw"]
        if "batch" in code.lower() or "bulk" in code.lower():
            patterns.append(self.create_pattern(
                "optimization", "batch_processing",
                "批处理优化 - 减少操作次数"
            ))

        # 对象池优化
        if "pool" in code.lower():
            patterns.append(self.create_pattern(
                "optimization", "object_pooling",
                "对象池 - 重用对象减少创建开销"
            ))

        return patterns

    # ============================================
    # 模式演化与学习
    # ============================================

    def detect_pattern_evolution(
        self,
        features: Dict[str, List[PatternFeature]],
        context: Dict[str, Any]
    ) -> List[CodePattern]:
        """检测模式演化"""
        evolved_patterns = []

        # 检查是否有模式的改进版本
        for pattern_id, pattern in self.patterns.items():
            if pattern.evolution_stage > 1:
                # 检查是否匹配演化后的模式
                if self.matches_evolved_pattern(pattern, features):
                    evolved_patterns.append(pattern)

        return evolved_patterns

    def discover_new_patterns(
        self,
        preprocessed: Dict[str, Any],
        features: Dict[str, List[PatternFeature]]
    ) -> List[CodePattern]:
        """发现新模式"""
        new_patterns = []

        # 使用聚类发现新模式
        feature_vectors = []
        for feature_list in features.values():
            for feature in feature_list:
                vec = self.feature_to_vector(feature)
                feature_vectors.append(vec)

        if len(feature_vectors) > 5:
            # 聚类
            X = np.array(feature_vectors)
            clusters = self.clusterer.fit_predict(X)

            # 分析每个聚类
            unique_clusters = set(clusters) - {-1}  # 排除噪声点
            for cluster_id in unique_clusters:
                cluster_features = [
                    f for i, f in enumerate(feature_vectors)
                    if clusters[i] == cluster_id
                ]

                # 如果聚类足够大且不匹配已知模式
                if len(cluster_features) > 3:
                    if not self.matches_known_pattern(cluster_features):
                        # 创建新模式
                        new_pattern = self.create_pattern(
                            "discovered", f"pattern_{cluster_id}",
                            f"新发现的模式 - 聚类{cluster_id}"
                        )
                        new_patterns.append(new_pattern)

        return new_patterns

    def evolve_pattern(
        self,
        pattern: CodePattern,
        new_occurrence: Dict[str, Any]
    ) -> None:
        """演化模式"""
        # 记录新的出现
        pattern.occurrences.append(new_occurrence)

        # 更新成功率
        successful = new_occurrence.get("success", True)
        total = len(pattern.occurrences)
        success_count = sum(1 for o in pattern.occurrences if o.get("success", True))
        pattern.success_rate = success_count / total

        # 检查是否需要演化
        if total > 10 and pattern.success_rate > 0.8:
            # 提升演化阶段
            pattern.evolution_stage += 1

            # 记录演化历史
            self.evolution_history[pattern.pattern_id].append({
                "timestamp": datetime.now(),
                "stage": pattern.evolution_stage,
                "success_rate": pattern.success_rate,
                "changes": self.analyze_pattern_changes(pattern)
            })

    # ============================================
    # 辅助方法
    # ============================================

    def create_pattern(
        self,
        pattern_type: str,
        pattern_name: str,
        description: str,
        **kwargs
    ) -> CodePattern:
        """创建模式"""
        pattern_id = self.generate_pattern_id(pattern_name)

        pattern = CodePattern(
            pattern_id=pattern_id,
            pattern_type=pattern_type,
            pattern_name=pattern_name,
            pattern_category=pattern_type,
            pattern_description=description,
            pattern_template="",
            pattern_signature="",
            **kwargs
        )

        return pattern

    def generate_pattern_id(self, name: str) -> str:
        """生成模式ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        hash_suffix = hashlib.md5(name.encode()).hexdigest()[:8]
        return f"pat_{timestamp}_{hash_suffix}"

    def normalize_code(self, code: str) -> str:
        """规范化代码"""
        # 移除多余空白
        code = re.sub(r'\s+', ' ', code)
        # 统一引号
        code = code.replace('"', "'")
        return code.strip()

    def tokenize_code(self, code: str) -> List[str]:
        """代码分词"""
        # 简单的分词实现
        tokens = re.findall(r'\b\w+\b', code)
        return tokens

    def calculate_complexity(self, code: str) -> int:
        """计算复杂度"""
        complexity = 1

        # 条件语句
        complexity += code.count('if ')
        complexity += code.count('elif ')
        complexity += code.count('else:')

        # 循环
        complexity += code.count('for ')
        complexity += code.count('while ')

        # 异常处理
        complexity += code.count('try:')
        complexity += code.count('except ')

        # 逻辑运算
        complexity += code.count(' and ')
        complexity += code.count(' or ')

        return complexity

    def detect_duplicates(self, lines: List[str]) -> int:
        """检测重复行"""
        line_counts = Counter(lines)
        duplicates = sum(count - 1 for count in line_counts.values() if count > 1)
        return duplicates

    def features_to_vector(
        self,
        features: Dict[str, List[PatternFeature]]
    ) -> np.ndarray:
        """特征转向量"""
        vector = []

        for feature_type, feature_list in features.items():
            type_vector = np.zeros(10)  # 每种类型分配10个维度
            for i, feature in enumerate(feature_list[:10]):
                type_vector[i] = feature.weight * feature.confidence
            vector.extend(type_vector)

        return np.array(vector)

    def feature_to_vector(self, feature: PatternFeature) -> np.ndarray:
        """单个特征转向量"""
        # 简化实现
        vec = np.zeros(10)
        vec[0] = hash(feature.feature_type) % 10 / 10
        vec[1] = hash(feature.feature_name) % 10 / 10
        vec[2] = feature.weight
        vec[3] = feature.confidence
        return vec

    def calculate_pattern_similarity(
        self,
        feature_vector: np.ndarray,
        pattern: CodePattern
    ) -> float:
        """计算模式相似度"""
        # 简化实现
        pattern_vector = self.pattern_to_vector(pattern)

        # 余弦相似度
        dot_product = np.dot(feature_vector, pattern_vector)
        norm_product = np.linalg.norm(feature_vector) * np.linalg.norm(pattern_vector)

        if norm_product == 0:
            return 0.0

        return dot_product / norm_product

    def pattern_to_vector(self, pattern: CodePattern) -> np.ndarray:
        """模式转向量"""
        # 使用模式的特征生成向量
        vector = np.zeros(40)  # 4种特征类型 × 10维

        for i, feature in enumerate(pattern.features[:40]):
            vector[i] = feature.weight * feature.confidence

        return vector

    def matches_evolved_pattern(
        self,
        pattern: CodePattern,
        features: Dict[str, List[PatternFeature]]
    ) -> bool:
        """检查是否匹配演化模式"""
        # 简化实现
        required_features = set(pattern.keywords)
        present_features = set()

        for feature_list in features.values():
            for feature in feature_list:
                present_features.add(feature.feature_name)

        return len(required_features & present_features) / len(required_features) > 0.7

    def matches_known_pattern(
        self,
        cluster_features: List[np.ndarray]
    ) -> bool:
        """检查是否匹配已知模式"""
        # 简化实现
        for pattern in self.patterns.values():
            pattern_vec = self.pattern_to_vector(pattern)
            for feat_vec in cluster_features:
                similarity = np.dot(feat_vec, pattern_vec) / (np.linalg.norm(feat_vec) * np.linalg.norm(pattern_vec))
                if similarity > 0.8:
                    return True
        return False

    def analyze_pattern_changes(self, pattern: CodePattern) -> Dict[str, Any]:
        """分析模式变化"""
        changes = {
            "feature_additions": [],
            "feature_removals": [],
            "effectiveness_change": 0.0
        }

        # 分析最近的出现
        recent = pattern.occurrences[-10:] if len(pattern.occurrences) > 10 else pattern.occurrences
        old = pattern.occurrences[:10] if len(pattern.occurrences) > 20 else []

        if old:
            # 比较新旧效果
            old_effectiveness = sum(o.get("effectiveness", 0) for o in old) / len(old)
            recent_effectiveness = sum(o.get("effectiveness", 0) for o in recent) / len(recent)
            changes["effectiveness_change"] = recent_effectiveness - old_effectiveness

        return changes

    def deduplicate_and_rank(self, patterns: List[CodePattern]) -> List[CodePattern]:
        """去重和排序"""
        # 去重
        seen_ids = set()
        unique_patterns = []

        for pattern in patterns:
            if pattern.pattern_id not in seen_ids:
                seen_ids.add(pattern.pattern_id)
                unique_patterns.append(pattern)

        # 排序(按效果和演化阶段)
        unique_patterns.sort(
            key=lambda p: (p.effectiveness, p.evolution_stage, p.success_rate),
            reverse=True
        )

        return unique_patterns

    def update_pattern_library(
        self,
        patterns: List[CodePattern],
        context: Dict[str, Any]
    ) -> None:
        """更新模式库"""
        for pattern in patterns:
            if pattern.pattern_id not in self.patterns:
                # 新模式
                self.patterns[pattern.pattern_id] = pattern
                self.pattern_index[pattern.pattern_type].add(pattern.pattern_id)
            else:
                # 更新现有模式
                existing = self.patterns[pattern.pattern_id]
                self.evolve_pattern(existing, context)


# ============================================
# 单例模式
# ============================================

_pattern_recognizer_instance: Optional[AdvancedPatternRecognizer] = None

def get_pattern_recognizer() -> AdvancedPatternRecognizer:
    """获取模式识别器单例"""
    global _pattern_recognizer_instance
    if _pattern_recognizer_instance is None:
        _pattern_recognizer_instance = AdvancedPatternRecognizer()
    return _pattern_recognizer_instance
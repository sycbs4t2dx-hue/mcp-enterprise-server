"""
编码学习系统 - 智能进化核心服务
让AI从每次编码中学习，越用越聪明
"""

import os
import json
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import numpy as np
from sqlalchemy import create_engine, select, and_, or_, desc, func
from sqlalchemy.orm import Session, sessionmaker

from ..models.base import Base
from ..common.config import get_settings
from ..common.logger import get_logger
from ..services.embedding_service import get_embedding_service
from ..services.redis_client import get_redis_client

logger = get_logger(__name__)

# ============================================
# 数据模型
# ============================================

@dataclass
class CodingSession:
    """编码会话数据"""
    session_id: str
    project_id: str
    context_type: str  # bug_fix, feature, refactor, optimization
    problem_description: str
    solution_description: str
    code_before: str
    code_after: str
    files_modified: List[str]
    time_spent: int  # 秒
    lines_changed: int
    bugs_fixed: int = 0
    bugs_introduced: int = 0
    test_coverage_change: float = 0.0
    performance_metrics: Dict[str, Any] = None
    metadata: Dict[str, Any] = None

@dataclass
class CodePattern:
    """代码模式"""
    pattern_id: str
    pattern_type: str  # design, coding, error, optimization
    pattern_name: str
    pattern_description: str
    pattern_template: str
    examples: List[Dict[str, Any]]
    occurrence_count: int = 0
    success_count: int = 0
    effectiveness: float = 0.0
    applicable_contexts: List[str] = None

@dataclass
class LearningExperience:
    """学习经验"""
    experience_id: str
    context_type: str
    problem: str
    solution: str
    patterns: List[str]  # 模式ID列表
    reusability_score: float
    success_rate: float
    confidence: float

@dataclass
class SolutionRecommendation:
    """解决方案推荐"""
    solution: str
    confidence: float
    past_success_rate: float
    estimated_time: int
    similar_cases: List[str]
    reasoning: str

# ============================================
# 编码学习系统
# ============================================

class CodingLearningSystem:
    """编码学习系统 - 越用越聪明"""

    def __init__(self):
        """初始化学习系统"""
        settings = get_settings()
        self.db_engine = create_engine(settings.database.url)
        self.SessionLocal = sessionmaker(bind=self.db_engine)

        # 嵌入服务(用于语义相似度)
        self.embedding_service = get_embedding_service()

        # Redis缓存
        self.redis_client = get_redis_client()

        # 学习参数
        self.min_confidence = 0.7
        self.similarity_threshold = 0.8
        self.pattern_min_occurrences = 3

        logger.info("编码学习系统初始化完成")

    # ============================================
    # 核心学习功能
    # ============================================

    def learn_from_session(self, session_data: CodingSession) -> Dict[str, Any]:
        """
        从编码会话中学习

        Args:
            session_data: 编码会话数据

        Returns:
            学习结果
        """
        try:
            # 1. 提取代码模式
            patterns = self.extract_patterns(session_data)
            logger.info(f"提取到 {len(patterns)} 个代码模式")

            # 2. 识别最佳实践
            best_practices = self.identify_best_practices(patterns, session_data)
            logger.info(f"识别到 {len(best_practices)} 个最佳实践")

            # 3. 记录错误修复模式
            error_fixes = self.record_error_fixes(session_data)

            # 4. 计算经验价值
            experience_value = self.evaluate_experience_value(session_data, patterns)

            # 5. 存储学习成果
            experience_id = self.store_experience(
                session_data,
                patterns,
                best_practices,
                error_fixes,
                experience_value
            )

            # 6. 更新模式库
            self.update_pattern_library(patterns, session_data)

            # 7. 生成解决方案模板
            templates = self.generate_solution_templates(patterns, session_data)

            return {
                "experience_id": experience_id,
                "patterns_extracted": len(patterns),
                "best_practices": len(best_practices),
                "error_fixes": len(error_fixes),
                "experience_value": experience_value,
                "solution_templates": len(templates),
                "learning_summary": self.generate_learning_summary(
                    patterns, best_practices, experience_value
                )
            }

        except Exception as e:
            logger.error(f"学习失败: {e}")
            return {"error": str(e)}

    def extract_patterns(self, session_data: CodingSession) -> List[CodePattern]:
        """
        提取代码模式

        Args:
            session_data: 编码会话数据

        Returns:
            代码模式列表
        """
        patterns = []

        # 1. 分析代码变更
        code_diff = self.analyze_code_diff(
            session_data.code_before,
            session_data.code_after
        )

        # 2. 识别结构模式
        structural_patterns = self.identify_structural_patterns(code_diff)
        patterns.extend(structural_patterns)

        # 3. 识别重构模式
        if session_data.context_type == "refactor":
            refactor_patterns = self.identify_refactor_patterns(code_diff)
            patterns.extend(refactor_patterns)

        # 4. 识别性能优化模式
        if session_data.context_type == "optimization":
            optimization_patterns = self.identify_optimization_patterns(
                code_diff,
                session_data.performance_metrics
            )
            patterns.extend(optimization_patterns)

        # 5. 识别错误修复模式
        if session_data.context_type == "bug_fix":
            fix_patterns = self.identify_fix_patterns(code_diff)
            patterns.extend(fix_patterns)

        return patterns

    def identify_best_practices(
        self,
        patterns: List[CodePattern],
        session_data: CodingSession
    ) -> List[Dict[str, Any]]:
        """识别最佳实践"""
        best_practices = []

        for pattern in patterns:
            # 评估模式质量
            quality_score = self.evaluate_pattern_quality(pattern, session_data)

            if quality_score > 0.8:
                best_practice = {
                    "pattern_id": pattern.pattern_id,
                    "name": pattern.pattern_name,
                    "description": pattern.pattern_description,
                    "quality_score": quality_score,
                    "applicable_to": pattern.applicable_contexts,
                    "benefits": self.analyze_pattern_benefits(pattern, session_data)
                }
                best_practices.append(best_practice)

        return best_practices

    def record_error_fixes(self, session_data: CodingSession) -> List[Dict[str, Any]]:
        """记录错误修复"""
        error_fixes = []

        if session_data.context_type == "bug_fix" and session_data.bugs_fixed > 0:
            fix_record = {
                "error_type": self.classify_error_type(session_data.problem_description),
                "error_pattern": self.extract_error_pattern(session_data.code_before),
                "fix_pattern": self.extract_fix_pattern(session_data.code_after),
                "fix_description": session_data.solution_description,
                "prevention_tips": self.generate_prevention_tips(session_data)
            }
            error_fixes.append(fix_record)

        return error_fixes

    # ============================================
    # 智能推荐功能
    # ============================================

    def suggest_solution(
        self,
        current_context: Dict[str, Any],
        top_k: int = 5
    ) -> List[SolutionRecommendation]:
        """
        基于历史经验推荐解决方案

        Args:
            current_context: 当前上下文
            top_k: 返回前K个推荐

        Returns:
            解决方案推荐列表
        """
        try:
            # 1. 分析当前上下文
            context_features = self.analyze_context(current_context)
            context_embedding = self.embedding_service.encode_single(
                json.dumps(context_features)
            )

            # 2. 查找相似经验
            similar_cases = self.find_similar_experiences(
                context_embedding,
                context_features.get("context_type"),
                limit=top_k * 2  # 获取更多候选以便筛选
            )

            # 3. 生成推荐
            recommendations = []
            for case in similar_cases[:top_k]:
                # 适配解决方案到当前上下文
                adapted_solution = self.adapt_solution(
                    case["solution"],
                    case["context"],
                    current_context
                )

                # 计算置信度
                confidence = self.calculate_confidence(
                    case["similarity_score"],
                    case["success_rate"],
                    case["reusability_score"]
                )

                recommendation = SolutionRecommendation(
                    solution=adapted_solution,
                    confidence=confidence,
                    past_success_rate=case["success_rate"],
                    estimated_time=case["avg_time"],
                    similar_cases=[case["experience_id"]],
                    reasoning=self.generate_recommendation_reasoning(
                        case, current_context
                    )
                )
                recommendations.append(recommendation)

            # 4. 按置信度排序
            recommendations.sort(key=lambda x: x.confidence, reverse=True)

            return recommendations

        except Exception as e:
            logger.error(f"生成推荐失败: {e}")
            return []

    def find_similar_experiences(
        self,
        query_embedding: np.ndarray,
        context_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """查找相似经验"""
        with self.SessionLocal() as session:
            # 构建查询
            query = session.execute(
                """
                SELECT
                    e.*,
                    p.name as project_name
                FROM coding_experiences e
                LEFT JOIN projects p ON e.project_id = p.project_id
                WHERE 1=1
                {}
                ORDER BY e.reusability_score DESC, e.success_rate DESC
                LIMIT :limit
                """.format(
                    "AND e.context_type = :context_type" if context_type else ""
                ),
                {
                    "context_type": context_type,
                    "limit": limit
                }
            )

            experiences = []
            for row in query:
                # 计算相似度
                exp_embedding = json.loads(row.context_embedding) if row.context_embedding else None
                if exp_embedding:
                    similarity = self.embedding_service.calculate_similarity(
                        query_embedding,
                        np.array(exp_embedding)
                    )

                    if similarity >= self.similarity_threshold:
                        experiences.append({
                            "experience_id": row.experience_id,
                            "context": json.loads(row.problem_description),
                            "solution": row.solution_description,
                            "similarity_score": similarity,
                            "success_rate": row.success_rate,
                            "reusability_score": row.reusability_score,
                            "avg_time": row.time_spent,
                            "project_name": row.project_name
                        })

            return experiences

    def adapt_solution(
        self,
        original_solution: str,
        original_context: Dict[str, Any],
        current_context: Dict[str, Any]
    ) -> str:
        """适配解决方案到当前上下文"""
        # 1. 识别上下文差异
        context_diff = self.compare_contexts(original_context, current_context)

        # 2. 调整解决方案
        adapted = original_solution

        # 替换变量名
        if "variable_mappings" in context_diff:
            for old_var, new_var in context_diff["variable_mappings"].items():
                adapted = adapted.replace(old_var, new_var)

        # 调整路径
        if "path_mappings" in context_diff:
            for old_path, new_path in context_diff["path_mappings"].items():
                adapted = adapted.replace(old_path, new_path)

        # 添加上下文特定的说明
        if "additional_considerations" in context_diff:
            adapted += "\n\n注意事项:\n"
            for consideration in context_diff["additional_considerations"]:
                adapted += f"- {consideration}\n"

        return adapted

    # ============================================
    # 模式管理功能
    # ============================================

    def update_pattern_library(
        self,
        patterns: List[CodePattern],
        session_data: CodingSession
    ) -> None:
        """更新模式库"""
        with self.SessionLocal() as session:
            for pattern in patterns:
                # 检查模式是否已存在
                existing = session.execute(
                    """
                    SELECT * FROM learning_patterns
                    WHERE pattern_name = :name
                    AND pattern_type = :type
                    """,
                    {
                        "name": pattern.pattern_name,
                        "type": pattern.pattern_type
                    }
                ).first()

                if existing:
                    # 更新现有模式
                    success = 1 if session_data.bugs_introduced == 0 else 0
                    session.execute(
                        """
                        UPDATE learning_patterns
                        SET occurrence_count = occurrence_count + 1,
                            success_count = success_count + :success,
                            effectiveness = (success_count + :success) / (occurrence_count + 1),
                            updated_at = NOW()
                        WHERE pattern_id = :id
                        """,
                        {
                            "id": existing.pattern_id,
                            "success": success
                        }
                    )
                else:
                    # 创建新模式
                    pattern_id = self.generate_id("pattern", pattern.pattern_name)
                    session.execute(
                        """
                        INSERT INTO learning_patterns (
                            pattern_id, project_id, pattern_type, pattern_name,
                            pattern_description, pattern_template, pattern_examples,
                            occurrence_count, success_count, effectiveness
                        ) VALUES (
                            :id, :project_id, :type, :name,
                            :description, :template, :examples,
                            1, 1, 1.0
                        )
                        """,
                        {
                            "id": pattern_id,
                            "project_id": session_data.project_id,
                            "type": pattern.pattern_type,
                            "name": pattern.pattern_name,
                            "description": pattern.pattern_description,
                            "template": pattern.pattern_template,
                            "examples": json.dumps(pattern.examples)
                        }
                    )

                session.commit()

    def generate_solution_templates(
        self,
        patterns: List[CodePattern],
        session_data: CodingSession
    ) -> List[Dict[str, Any]]:
        """生成解决方案模板"""
        templates = []

        for pattern in patterns:
            if pattern.effectiveness > 0.7:
                template = {
                    "template_id": self.generate_id("template", pattern.pattern_name),
                    "pattern_id": pattern.pattern_id,
                    "name": f"{pattern.pattern_name}_template",
                    "description": f"基于{pattern.pattern_name}模式的解决方案模板",
                    "template_code": self.generate_template_code(pattern),
                    "variables": self.extract_template_variables(pattern),
                    "usage_guide": self.generate_usage_guide(pattern),
                    "applicable_scenarios": pattern.applicable_contexts
                }
                templates.append(template)

                # 缓存模板
                self.cache_template(template)

        return templates

    # ============================================
    # 评估和分析功能
    # ============================================

    def evaluate_experience_value(
        self,
        session_data: CodingSession,
        patterns: List[CodePattern]
    ) -> Dict[str, float]:
        """评估经验价值"""
        # 计算各维度分数
        quality_score = self.calculate_quality_score(session_data)
        complexity_score = self.calculate_complexity_score(session_data)
        reusability_score = self.calculate_reusability_score(patterns)
        learning_value = self.calculate_learning_value(patterns, session_data)

        # 综合评分
        overall_value = (
            quality_score * 0.3 +
            complexity_score * 0.2 +
            reusability_score * 0.3 +
            learning_value * 0.2
        )

        return {
            "overall": overall_value,
            "quality": quality_score,
            "complexity": complexity_score,
            "reusability": reusability_score,
            "learning": learning_value
        }

    def calculate_quality_score(self, session_data: CodingSession) -> float:
        """计算质量分数"""
        score = 1.0

        # Bug引入惩罚
        if session_data.bugs_introduced > 0:
            score *= (1 - 0.2 * session_data.bugs_introduced)

        # Bug修复奖励
        if session_data.bugs_fixed > 0:
            score *= (1 + 0.1 * session_data.bugs_fixed)

        # 测试覆盖率提升奖励
        if session_data.test_coverage_change > 0:
            score *= (1 + session_data.test_coverage_change)

        return min(max(score, 0.0), 1.0)

    def calculate_complexity_score(self, session_data: CodingSession) -> float:
        """计算复杂度分数"""
        # 基于代码变更量和时间的复杂度估算
        if session_data.lines_changed == 0:
            return 0.0

        efficiency = session_data.lines_changed / max(session_data.time_spent, 60)
        complexity = 1.0 / (1.0 + np.exp(-efficiency))

        return complexity

    def calculate_reusability_score(self, patterns: List[CodePattern]) -> float:
        """计算可复用性分数"""
        if not patterns:
            return 0.0

        # 基于模式的通用性和有效性
        scores = [p.effectiveness * len(p.applicable_contexts or []) / 10 for p in patterns]
        return min(np.mean(scores), 1.0)

    def calculate_learning_value(
        self,
        patterns: List[CodePattern],
        session_data: CodingSession
    ) -> float:
        """计算学习价值"""
        value = 0.0

        # 新模式发现奖励
        new_patterns = sum(1 for p in patterns if p.occurrence_count == 0)
        value += new_patterns * 0.2

        # 高质量模式奖励
        high_quality = sum(1 for p in patterns if p.effectiveness > 0.8)
        value += high_quality * 0.1

        # 问题解决奖励
        if session_data.context_type == "bug_fix" and session_data.bugs_fixed > 0:
            value += 0.3

        return min(value, 1.0)

    # ============================================
    # 辅助功能
    # ============================================

    def analyze_code_diff(self, code_before: str, code_after: str) -> Dict[str, Any]:
        """分析代码差异"""
        # 简化实现：实际应使用专业的diff库
        lines_before = code_before.split('\n')
        lines_after = code_after.split('\n')

        added_lines = []
        removed_lines = []
        modified_lines = []

        # 简单的行级对比
        max_lines = max(len(lines_before), len(lines_after))
        for i in range(max_lines):
            if i < len(lines_before) and i < len(lines_after):
                if lines_before[i] != lines_after[i]:
                    modified_lines.append({
                        "line": i + 1,
                        "before": lines_before[i],
                        "after": lines_after[i]
                    })
            elif i < len(lines_before):
                removed_lines.append({"line": i + 1, "content": lines_before[i]})
            else:
                added_lines.append({"line": i + 1, "content": lines_after[i]})

        return {
            "added": added_lines,
            "removed": removed_lines,
            "modified": modified_lines,
            "total_changes": len(added_lines) + len(removed_lines) + len(modified_lines)
        }

    def identify_structural_patterns(self, code_diff: Dict[str, Any]) -> List[CodePattern]:
        """识别结构模式"""
        patterns = []

        # 分析添加的代码结构
        for added in code_diff["added"]:
            content = added["content"].strip()

            # 识别常见结构模式
            if "class " in content:
                patterns.append(self.create_pattern("design", "class_definition", content))
            elif "def " in content:
                patterns.append(self.create_pattern("coding", "function_definition", content))
            elif "try:" in content:
                patterns.append(self.create_pattern("error", "exception_handling", content))
            elif "with " in content:
                patterns.append(self.create_pattern("coding", "context_manager", content))

        return patterns

    def create_pattern(
        self,
        pattern_type: str,
        pattern_name: str,
        content: str
    ) -> CodePattern:
        """创建模式对象"""
        return CodePattern(
            pattern_id=self.generate_id("pattern", pattern_name),
            pattern_type=pattern_type,
            pattern_name=pattern_name,
            pattern_description=f"Pattern: {pattern_name}",
            pattern_template=content,
            examples=[{"code": content}],
            applicable_contexts=[pattern_type]
        )

    def store_experience(
        self,
        session_data: CodingSession,
        patterns: List[CodePattern],
        best_practices: List[Dict[str, Any]],
        error_fixes: List[Dict[str, Any]],
        experience_value: Dict[str, float]
    ) -> str:
        """存储学习经验"""
        experience_id = self.generate_id("exp", session_data.session_id)

        # 生成嵌入向量
        context_embedding = self.embedding_service.encode_single(
            session_data.problem_description
        ).tolist()
        solution_embedding = self.embedding_service.encode_single(
            session_data.solution_description
        ).tolist()

        with self.SessionLocal() as session:
            session.execute(
                """
                INSERT INTO coding_experiences (
                    experience_id, project_id, session_id,
                    context_type, problem_description, solution_description,
                    code_before, code_after, files_modified,
                    time_spent, lines_changed,
                    bugs_fixed, bugs_introduced, test_coverage_change,
                    reusability_score, success_rate,
                    context_embedding, solution_embedding,
                    metadata
                ) VALUES (
                    :exp_id, :project_id, :session_id,
                    :context_type, :problem, :solution,
                    :code_before, :code_after, :files,
                    :time, :lines,
                    :bugs_fixed, :bugs_introduced, :coverage,
                    :reusability, :success,
                    :context_emb, :solution_emb,
                    :metadata
                )
                """,
                {
                    "exp_id": experience_id,
                    "project_id": session_data.project_id,
                    "session_id": session_data.session_id,
                    "context_type": session_data.context_type,
                    "problem": session_data.problem_description,
                    "solution": session_data.solution_description,
                    "code_before": session_data.code_before,
                    "code_after": session_data.code_after,
                    "files": json.dumps(session_data.files_modified),
                    "time": session_data.time_spent,
                    "lines": session_data.lines_changed,
                    "bugs_fixed": session_data.bugs_fixed,
                    "bugs_introduced": session_data.bugs_introduced,
                    "coverage": session_data.test_coverage_change,
                    "reusability": experience_value["reusability"],
                    "success": experience_value["quality"],
                    "context_emb": json.dumps(context_embedding),
                    "solution_emb": json.dumps(solution_embedding),
                    "metadata": json.dumps({
                        "patterns": [p.pattern_id for p in patterns],
                        "best_practices": best_practices,
                        "error_fixes": error_fixes,
                        "value_scores": experience_value
                    })
                }
            )
            session.commit()

        logger.info(f"存储经验: {experience_id}")
        return experience_id

    def generate_id(self, prefix: str, content: str) -> str:
        """生成唯一ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        hash_suffix = hashlib.md5(content.encode()).hexdigest()[:8]
        return f"{prefix}_{timestamp}_{hash_suffix}"

    def cache_template(self, template: Dict[str, Any]) -> None:
        """缓存模板"""
        key = f"template:{template['template_id']}"
        self.redis_client.set(
            key,
            json.dumps(template),
            ex=86400 * 7  # 缓存7天
        )

    def generate_learning_summary(
        self,
        patterns: List[CodePattern],
        best_practices: List[Dict[str, Any]],
        experience_value: Dict[str, float]
    ) -> str:
        """生成学习摘要"""
        summary = []

        summary.append(f"学习成果:")
        summary.append(f"- 识别 {len(patterns)} 个代码模式")
        summary.append(f"- 发现 {len(best_practices)} 个最佳实践")
        summary.append(f"- 经验价值: {experience_value['overall']:.2f}")

        if patterns:
            summary.append(f"\n主要模式:")
            for p in patterns[:3]:
                summary.append(f"  - {p.pattern_name}: {p.pattern_type}")

        if best_practices:
            summary.append(f"\n最佳实践:")
            for bp in best_practices[:3]:
                summary.append(f"  - {bp['name']}: 质量分数 {bp['quality_score']:.2f}")

        return "\n".join(summary)

    def analyze_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """分析上下文"""
        return {
            "context_type": context.get("type", "unknown"),
            "problem_keywords": self.extract_keywords(context.get("problem", "")),
            "file_types": self.extract_file_types(context.get("files", [])),
            "complexity_estimate": self.estimate_complexity(context),
            "domain": context.get("domain", "general")
        }

    def extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        # 简化实现
        import re
        words = re.findall(r'\b\w+\b', text.lower())
        # 过滤停用词
        stopwords = {'the', 'is', 'at', 'which', 'on', 'and', 'a', 'an'}
        keywords = [w for w in words if w not in stopwords and len(w) > 2]
        return list(set(keywords))[:10]

    def extract_file_types(self, files: List[str]) -> List[str]:
        """提取文件类型"""
        types = set()
        for file in files:
            ext = os.path.splitext(file)[1]
            if ext:
                types.add(ext)
        return list(types)

    def estimate_complexity(self, context: Dict[str, Any]) -> str:
        """估算复杂度"""
        indicators = 0

        if len(context.get("files", [])) > 5:
            indicators += 1
        if "refactor" in context.get("type", ""):
            indicators += 1
        if "optimization" in context.get("type", ""):
            indicators += 1
        if len(context.get("problem", "")) > 500:
            indicators += 1

        if indicators >= 3:
            return "high"
        elif indicators >= 1:
            return "medium"
        else:
            return "low"

    def calculate_confidence(
        self,
        similarity: float,
        success_rate: float,
        reusability: float
    ) -> float:
        """计算推荐置信度"""
        # 加权平均
        confidence = (
            similarity * 0.4 +
            success_rate * 0.4 +
            reusability * 0.2
        )
        return min(confidence, 1.0)

    def compare_contexts(
        self,
        context1: Dict[str, Any],
        context2: Dict[str, Any]
    ) -> Dict[str, Any]:
        """比较两个上下文的差异"""
        diff = {
            "variable_mappings": {},
            "path_mappings": {},
            "additional_considerations": []
        }

        # 简化实现
        if context1.get("language") != context2.get("language"):
            diff["additional_considerations"].append(
                f"语言差异: {context1.get('language')} vs {context2.get('language')}"
            )

        if context1.get("framework") != context2.get("framework"):
            diff["additional_considerations"].append(
                f"框架差异: {context1.get('framework')} vs {context2.get('framework')}"
            )

        return diff

    def generate_recommendation_reasoning(
        self,
        case: Dict[str, Any],
        current_context: Dict[str, Any]
    ) -> str:
        """生成推荐理由"""
        reasoning = []

        reasoning.append(f"基于相似案例 {case['experience_id']}:")
        reasoning.append(f"- 相似度: {case['similarity_score']:.2%}")
        reasoning.append(f"- 历史成功率: {case['success_rate']:.2%}")
        reasoning.append(f"- 来自项目: {case.get('project_name', 'Unknown')}")

        return "\n".join(reasoning)

    # 其他辅助方法...
    def identify_refactor_patterns(self, code_diff: Dict[str, Any]) -> List[CodePattern]:
        """识别重构模式"""
        patterns = []
        # 实现重构模式识别逻辑
        return patterns

    def identify_optimization_patterns(
        self,
        code_diff: Dict[str, Any],
        metrics: Optional[Dict[str, Any]]
    ) -> List[CodePattern]:
        """识别优化模式"""
        patterns = []
        # 实现优化模式识别逻辑
        return patterns

    def identify_fix_patterns(self, code_diff: Dict[str, Any]) -> List[CodePattern]:
        """识别错误修复模式"""
        patterns = []
        # 实现错误修复模式识别逻辑
        return patterns

    def evaluate_pattern_quality(
        self,
        pattern: CodePattern,
        session_data: CodingSession
    ) -> float:
        """评估模式质量"""
        # 简化实现
        return pattern.effectiveness

    def analyze_pattern_benefits(
        self,
        pattern: CodePattern,
        session_data: CodingSession
    ) -> List[str]:
        """分析模式优势"""
        benefits = []
        if pattern.effectiveness > 0.8:
            benefits.append("高成功率")
        if pattern.occurrence_count > 10:
            benefits.append("经过验证")
        return benefits

    def classify_error_type(self, problem: str) -> str:
        """分类错误类型"""
        problem_lower = problem.lower()
        if "syntax" in problem_lower:
            return "syntax_error"
        elif "type" in problem_lower:
            return "type_error"
        elif "null" in problem_lower or "none" in problem_lower:
            return "null_reference"
        else:
            return "general_error"

    def extract_error_pattern(self, code: str) -> str:
        """提取错误模式"""
        # 简化实现
        return code[:100]

    def extract_fix_pattern(self, code: str) -> str:
        """提取修复模式"""
        # 简化实现
        return code[:100]

    def generate_prevention_tips(self, session_data: CodingSession) -> List[str]:
        """生成预防建议"""
        tips = []
        if session_data.bugs_fixed > 0:
            tips.append("添加输入验证")
            tips.append("增加错误处理")
            tips.append("编写单元测试")
        return tips

    def generate_template_code(self, pattern: CodePattern) -> str:
        """生成模板代码"""
        return pattern.pattern_template

    def extract_template_variables(self, pattern: CodePattern) -> List[str]:
        """提取模板变量"""
        # 简化实现
        import re
        return re.findall(r'\${(\w+)}', pattern.pattern_template)

    def generate_usage_guide(self, pattern: CodePattern) -> str:
        """生成使用指南"""
        return f"使用 {pattern.pattern_name} 模式:\n1. 识别适用场景\n2. 应用模板\n3. 自定义参数"


# ============================================
# 单例模式
# ============================================

_learning_system_instance: Optional[CodingLearningSystem] = None

def get_learning_system() -> CodingLearningSystem:
    """获取学习系统单例"""
    global _learning_system_instance
    if _learning_system_instance is None:
        _learning_system_instance = CodingLearningSystem()
    return _learning_system_instance
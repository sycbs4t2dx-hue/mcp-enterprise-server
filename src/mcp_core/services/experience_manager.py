"""
智能经验管理系统 - 经验存储、检索、演化、共享
支持多级缓存、智能推荐、经验融合
"""

import json
import pickle
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import defaultdict, deque
import numpy as np
from sqlalchemy import create_engine, select, and_, or_, desc, func
from sqlalchemy.orm import Session, sessionmaker
import redis

from ..common.config import get_settings
from ..common.logger import get_logger
from ..services.embedding_service import get_embedding_service
from ..services.redis_client import get_redis_client

logger = get_logger(__name__)

# ============================================
# 数据模型
# ============================================

@dataclass
class Experience:
    """经验实体"""
    experience_id: str
    experience_type: str  # solution, pattern, trick, pitfall
    category: str  # bug_fix, optimization, refactor, feature

    # 经验内容
    title: str
    description: str
    problem: str
    solution: str
    code_example: Optional[str] = None

    # 上下文
    context: Dict[str, Any] = field(default_factory=dict)
    prerequisites: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)

    # 效果指标
    effectiveness: float = 0.0
    complexity: float = 0.0
    reusability: float = 0.0
    reliability: float = 0.0

    # 使用统计
    usage_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    average_time_saved: float = 0.0

    # 反馈
    ratings: List[float] = field(default_factory=list)
    comments: List[str] = field(default_factory=list)
    improvements: List[str] = field(default_factory=list)

    # 关系
    related_experiences: List[str] = field(default_factory=list)
    parent_experience: Optional[str] = None
    child_experiences: List[str] = field(default_factory=list)

    # 标签
    tags: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)

    # 元数据
    project_id: Optional[str] = None
    author_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    version: int = 1

@dataclass
class ExperienceCluster:
    """经验聚类"""
    cluster_id: str
    cluster_name: str
    cluster_type: str
    experiences: List[str]  # experience_ids
    representative: str  # 代表性经验ID
    common_features: Dict[str, Any]
    effectiveness_score: float
    size: int

@dataclass
class ExperienceRecommendation:
    """经验推荐"""
    experience: Experience
    relevance_score: float
    confidence: float
    reasoning: str
    expected_benefit: Dict[str, Any]
    risk_assessment: Dict[str, Any]

# ============================================
# 经验管理系统
# ============================================

class ExperienceManagementSystem:
    """智能经验管理系统"""

    def __init__(self):
        """初始化系统"""
        settings = get_settings()
        self.db_engine = create_engine(settings.database.url)
        self.SessionLocal = sessionmaker(bind=self.db_engine)

        # 嵌入服务
        self.embedding_service = get_embedding_service()

        # Redis缓存
        self.redis_client = get_redis_client()

        # 内存缓存(LRU)
        self.memory_cache: Dict[str, Experience] = {}
        self.cache_order: deque = deque(maxlen=1000)

        # 经验索引
        self.experience_index: Dict[str, Set[str]] = defaultdict(set)
        self.tag_index: Dict[str, Set[str]] = defaultdict(set)
        self.category_index: Dict[str, Set[str]] = defaultdict(set)

        # 经验聚类
        self.clusters: Dict[str, ExperienceCluster] = {}

        # 配置
        self.cache_ttl = 3600  # 1小时
        self.min_effectiveness = 0.6
        self.fusion_threshold = 0.85

        logger.info("经验管理系统初始化完成")

    # ============================================
    # 核心功能
    # ============================================

    def store_experience(self, experience: Experience) -> str:
        """
        存储经验

        Args:
            experience: 经验实体

        Returns:
            经验ID
        """
        try:
            # 1. 生成ID(如果没有)
            if not experience.experience_id:
                experience.experience_id = self.generate_experience_id(experience)

            # 2. 计算嵌入向量
            embedding = self.calculate_experience_embedding(experience)

            # 3. 检查重复或相似
            similar = self.find_similar_experiences(embedding, threshold=self.fusion_threshold)

            if similar:
                # 4. 融合相似经验
                merged = self.merge_experiences(experience, similar)
                experience = merged
                logger.info(f"融合 {len(similar)} 个相似经验")

            # 5. 评估经验价值
            self.evaluate_experience(experience)

            # 6. 存储到数据库
            self.save_to_database(experience, embedding)

            # 7. 更新缓存
            self.update_caches(experience)

            # 8. 更新索引
            self.update_indexes(experience)

            # 9. 触发聚类更新
            self.update_clusters_async(experience)

            logger.info(f"存储经验: {experience.experience_id}")

            return experience.experience_id

        except Exception as e:
            logger.error(f"存储经验失败: {e}")
            raise

    def retrieve_experience(
        self,
        query: str,
        context: Dict[str, Any],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ExperienceRecommendation]:
        """
        检索相关经验

        Args:
            query: 查询文本
            context: 上下文信息
            top_k: 返回数量
            filters: 过滤条件

        Returns:
            推荐列表
        """
        try:
            # 1. 查询向量化
            query_embedding = self.embedding_service.encode_single(query)

            # 2. 多路检索
            candidates = self.multi_path_retrieval(
                query_embedding,
                query,
                context,
                filters
            )

            # 3. 重排序
            ranked = self.rerank_experiences(candidates, query, context)

            # 4. 生成推荐
            recommendations = []
            for experience, score in ranked[:top_k]:
                recommendation = self.generate_recommendation(
                    experience,
                    score,
                    query,
                    context
                )
                recommendations.append(recommendation)

            # 5. 记录使用
            self.record_retrieval(query, recommendations)

            return recommendations

        except Exception as e:
            logger.error(f"检索经验失败: {e}")
            return []

    def evolve_experience(
        self,
        experience_id: str,
        feedback: Dict[str, Any]
    ) -> None:
        """
        演化经验

        Args:
            experience_id: 经验ID
            feedback: 反馈信息
        """
        try:
            # 1. 获取经验
            experience = self.get_experience(experience_id)
            if not experience:
                logger.warning(f"经验不存在: {experience_id}")
                return

            # 2. 更新统计
            self.update_statistics(experience, feedback)

            # 3. 分析反馈
            insights = self.analyze_feedback(feedback)

            # 4. 应用改进
            if insights.get("improvements"):
                self.apply_improvements(experience, insights["improvements"])

            # 5. 调整评分
            self.adjust_scores(experience, feedback)

            # 6. 检查演化条件
            if self.should_evolve(experience):
                # 7. 创建新版本
                new_version = self.create_evolved_version(experience)
                self.store_experience(new_version)

                # 8. 建立演化链
                experience.child_experiences.append(new_version.experience_id)
                new_version.parent_experience = experience.experience_id

            # 9. 更新存储
            self.update_experience(experience)

            logger.info(f"经验演化: {experience_id}")

        except Exception as e:
            logger.error(f"经验演化失败: {e}")

    def share_experience(
        self,
        experience_id: str,
        target_project: str,
        adapt: bool = True
    ) -> str:
        """
        共享经验到其他项目

        Args:
            experience_id: 经验ID
            target_project: 目标项目
            adapt: 是否适配

        Returns:
            新经验ID
        """
        try:
            # 1. 获取原经验
            experience = self.get_experience(experience_id)
            if not experience:
                raise ValueError(f"经验不存在: {experience_id}")

            # 2. 复制经验
            shared = self.clone_experience(experience)
            shared.project_id = target_project

            if adapt:
                # 3. 适配到目标项目
                self.adapt_to_project(shared, target_project)

            # 4. 存储共享经验
            new_id = self.store_experience(shared)

            # 5. 建立共享关系
            self.create_sharing_link(experience_id, new_id, target_project)

            logger.info(f"共享经验: {experience_id} -> {target_project}")

            return new_id

        except Exception as e:
            logger.error(f"共享经验失败: {e}")
            raise

    # ============================================
    # 检索功能
    # ============================================

    def multi_path_retrieval(
        self,
        query_embedding: np.ndarray,
        query_text: str,
        context: Dict[str, Any],
        filters: Optional[Dict[str, Any]]
    ) -> List[Tuple[Experience, float]]:
        """多路径检索"""
        candidates = []

        # 1. 向量检索
        vector_results = self.vector_search(query_embedding, limit=50)
        candidates.extend(vector_results)

        # 2. 关键词检索
        keyword_results = self.keyword_search(query_text, limit=30)
        candidates.extend(keyword_results)

        # 3. 标签检索
        if context.get("tags"):
            tag_results = self.tag_search(context["tags"], limit=20)
            candidates.extend(tag_results)

        # 4. 类别检索
        if context.get("category"):
            category_results = self.category_search(context["category"], limit=20)
            candidates.extend(category_results)

        # 5. 应用过滤器
        if filters:
            candidates = self.apply_filters(candidates, filters)

        # 6. 去重和合并分数
        merged = self.merge_results(candidates)

        return merged

    def vector_search(
        self,
        query_embedding: np.ndarray,
        limit: int = 50
    ) -> List[Tuple[Experience, float]]:
        """向量相似度检索"""
        results = []

        with self.SessionLocal() as session:
            # 从数据库检索
            rows = session.execute(
                """
                SELECT
                    experience_id,
                    context_embedding,
                    solution_embedding
                FROM coding_experiences
                WHERE context_embedding IS NOT NULL
                ORDER BY created_at DESC
                LIMIT :limit
                """,
                {"limit": limit * 2}  # 多获取一些用于计算
            )

            for row in rows:
                try:
                    # 计算相似度
                    context_emb = json.loads(row.context_embedding)
                    solution_emb = json.loads(row.solution_embedding)

                    # 综合相似度
                    context_sim = self.calculate_similarity(query_embedding, context_emb)
                    solution_sim = self.calculate_similarity(query_embedding, solution_emb)
                    similarity = (context_sim + solution_sim) / 2

                    if similarity > 0.5:
                        experience = self.get_experience(row.experience_id)
                        if experience:
                            results.append((experience, similarity))

                except Exception as e:
                    logger.debug(f"计算相似度失败: {e}")

            # 排序
            results.sort(key=lambda x: x[1], reverse=True)

        return results[:limit]

    def keyword_search(
        self,
        query_text: str,
        limit: int = 30
    ) -> List[Tuple[Experience, float]]:
        """关键词检索"""
        keywords = self.extract_keywords(query_text)
        results = []

        for keyword in keywords:
            if keyword in self.tag_index:
                for exp_id in self.tag_index[keyword]:
                    experience = self.get_experience(exp_id)
                    if experience:
                        score = self.calculate_keyword_score(experience, keywords)
                        results.append((experience, score))

        # 去重和排序
        unique_results = {}
        for exp, score in results:
            if exp.experience_id not in unique_results or unique_results[exp.experience_id][1] < score:
                unique_results[exp.experience_id] = (exp, score)

        sorted_results = sorted(unique_results.values(), key=lambda x: x[1], reverse=True)

        return sorted_results[:limit]

    def tag_search(
        self,
        tags: List[str],
        limit: int = 20
    ) -> List[Tuple[Experience, float]]:
        """标签检索"""
        results = []

        for tag in tags:
            if tag in self.tag_index:
                for exp_id in self.tag_index[tag]:
                    experience = self.get_experience(exp_id)
                    if experience:
                        # 计算标签匹配度
                        common_tags = set(experience.tags) & set(tags)
                        score = len(common_tags) / len(tags)
                        results.append((experience, score))

        # 去重
        unique_results = {}
        for exp, score in results:
            if exp.experience_id not in unique_results or unique_results[exp.experience_id][1] < score:
                unique_results[exp.experience_id] = (exp, score)

        sorted_results = sorted(unique_results.values(), key=lambda x: x[1], reverse=True)

        return sorted_results[:limit]

    def category_search(
        self,
        category: str,
        limit: int = 20
    ) -> List[Tuple[Experience, float]]:
        """类别检索"""
        results = []

        if category in self.category_index:
            for exp_id in self.category_index[category]:
                experience = self.get_experience(exp_id)
                if experience:
                    # 基础分数
                    score = 0.7

                    # 根据效果调整
                    score += experience.effectiveness * 0.3

                    results.append((experience, score))

        results.sort(key=lambda x: x[1], reverse=True)

        return results[:limit]

    # ============================================
    # 重排序与推荐
    # ============================================

    def rerank_experiences(
        self,
        candidates: List[Tuple[Experience, float]],
        query: str,
        context: Dict[str, Any]
    ) -> List[Tuple[Experience, float]]:
        """重排序经验"""
        reranked = []

        for experience, initial_score in candidates:
            # 计算多维度分数
            relevance = initial_score
            effectiveness = experience.effectiveness
            reusability = experience.reusability
            reliability = experience.reliability

            # 上下文匹配
            context_match = self.calculate_context_match(experience, context)

            # 时间衰减
            time_decay = self.calculate_time_decay(experience)

            # 使用频率
            usage_factor = min(1.0, experience.usage_count / 100)

            # 综合分数
            final_score = (
                relevance * 0.3 +
                effectiveness * 0.2 +
                reusability * 0.15 +
                reliability * 0.15 +
                context_match * 0.1 +
                usage_factor * 0.05 +
                time_decay * 0.05
            )

            reranked.append((experience, final_score))

        reranked.sort(key=lambda x: x[1], reverse=True)

        return reranked

    def generate_recommendation(
        self,
        experience: Experience,
        score: float,
        query: str,
        context: Dict[str, Any]
    ) -> ExperienceRecommendation:
        """生成推荐"""
        # 分析预期收益
        expected_benefit = self.analyze_expected_benefit(experience, context)

        # 风险评估
        risk_assessment = self.assess_risks(experience, context)

        # 生成推理说明
        reasoning = self.generate_reasoning(experience, score, query, context)

        # 计算置信度
        confidence = self.calculate_confidence(experience, score, context)

        return ExperienceRecommendation(
            experience=experience,
            relevance_score=score,
            confidence=confidence,
            reasoning=reasoning,
            expected_benefit=expected_benefit,
            risk_assessment=risk_assessment
        )

    # ============================================
    # 经验融合与演化
    # ============================================

    def merge_experiences(
        self,
        new_experience: Experience,
        similar_experiences: List[Experience]
    ) -> Experience:
        """融合相似经验"""
        # 使用最高效的作为基础
        base = max([new_experience] + similar_experiences, key=lambda e: e.effectiveness)

        # 合并解决方案
        solutions = [base.solution] + [e.solution for e in similar_experiences if e.solution != base.solution]
        if len(solutions) > 1:
            base.solution = self.combine_solutions(solutions)

        # 合并标签
        all_tags = set(base.tags)
        for exp in similar_experiences:
            all_tags.update(exp.tags)
        base.tags = list(all_tags)

        # 合并关键词
        all_keywords = set(base.keywords)
        for exp in similar_experiences:
            all_keywords.update(exp.keywords)
        base.keywords = list(all_keywords)

        # 更新统计
        base.usage_count += sum(e.usage_count for e in similar_experiences)
        base.success_count += sum(e.success_count for e in similar_experiences)
        base.failure_count += sum(e.failure_count for e in similar_experiences)

        # 重新评估
        self.evaluate_experience(base)

        # 记录融合关系
        base.related_experiences.extend([e.experience_id for e in similar_experiences])

        return base

    def should_evolve(self, experience: Experience) -> bool:
        """判断是否应该演化"""
        # 使用次数足够
        if experience.usage_count < 10:
            return False

        # 成功率变化明显
        success_rate = experience.success_count / max(1, experience.usage_count)
        if abs(success_rate - experience.effectiveness) > 0.2:
            return True

        # 收到改进建议
        if len(experience.improvements) > 5:
            return True

        # 时间因素
        age = (datetime.now() - experience.created_at).days
        if age > 90 and experience.version == 1:
            return True

        return False

    def create_evolved_version(self, experience: Experience) -> Experience:
        """创建演化版本"""
        # 复制基础信息
        evolved = self.clone_experience(experience)

        # 更新版本
        evolved.version = experience.version + 1
        evolved.experience_id = None  # 将生成新ID

        # 应用改进
        if experience.improvements:
            evolved.solution = self.apply_improvements_to_solution(
                evolved.solution,
                experience.improvements
            )

        # 更新评分
        success_rate = experience.success_count / max(1, experience.usage_count)
        evolved.effectiveness = success_rate

        # 重置统计
        evolved.usage_count = 0
        evolved.success_count = 0
        evolved.failure_count = 0

        return evolved

    # ============================================
    # 辅助方法
    # ============================================

    def generate_experience_id(self, experience: Experience) -> str:
        """生成经验ID"""
        content = f"{experience.title}_{experience.category}_{datetime.now()}"
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def calculate_experience_embedding(self, experience: Experience) -> np.ndarray:
        """计算经验嵌入"""
        # 组合多个文本字段
        text = f"{experience.title} {experience.description} {experience.problem} {experience.solution}"

        # 添加标签和关键词
        text += " ".join(experience.tags) + " " + " ".join(experience.keywords)

        return self.embedding_service.encode_single(text)

    def find_similar_experiences(
        self,
        embedding: np.ndarray,
        threshold: float = 0.8
    ) -> List[Experience]:
        """查找相似经验"""
        similar = []

        # 从缓存查找
        for exp_id, exp in self.memory_cache.items():
            try:
                exp_embedding = self.calculate_experience_embedding(exp)
                similarity = self.calculate_similarity(embedding, exp_embedding)

                if similarity > threshold:
                    similar.append(exp)

            except Exception as e:
                logger.debug(f"计算相似度失败: {e}")

        return similar

    def evaluate_experience(self, experience: Experience) -> None:
        """评估经验价值"""
        # 基础评分
        if experience.usage_count > 0:
            experience.effectiveness = experience.success_count / experience.usage_count
        else:
            experience.effectiveness = 0.7  # 默认值

        # 复杂度评估(基于解决方案长度)
        solution_length = len(experience.solution)
        if solution_length < 100:
            experience.complexity = 0.3
        elif solution_length < 500:
            experience.complexity = 0.6
        else:
            experience.complexity = 0.9

        # 可复用性(基于上下文依赖)
        context_deps = len(experience.prerequisites)
        if context_deps == 0:
            experience.reusability = 1.0
        elif context_deps < 3:
            experience.reusability = 0.7
        else:
            experience.reusability = 0.4

        # 可靠性(基于失败率)
        total = experience.success_count + experience.failure_count
        if total > 0:
            experience.reliability = 1 - (experience.failure_count / total)
        else:
            experience.reliability = 0.8  # 默认值

    def save_to_database(self, experience: Experience, embedding: np.ndarray) -> None:
        """保存到数据库"""
        with self.SessionLocal() as session:
            session.execute(
                """
                INSERT INTO coding_experiences (
                    experience_id, project_id, session_id,
                    context_type, problem_description, solution_description,
                    reusability_score, success_rate,
                    context_embedding, metadata
                ) VALUES (
                    :exp_id, :project_id, :session_id,
                    :category, :problem, :solution,
                    :reusability, :effectiveness,
                    :embedding, :metadata
                )
                ON DUPLICATE KEY UPDATE
                    solution_description = :solution,
                    reusability_score = :reusability,
                    success_rate = :effectiveness,
                    updated_at = NOW()
                """,
                {
                    "exp_id": experience.experience_id,
                    "project_id": experience.project_id or "default",
                    "session_id": f"exp_{experience.experience_id}",
                    "category": experience.category,
                    "problem": experience.problem,
                    "solution": experience.solution,
                    "reusability": experience.reusability,
                    "effectiveness": experience.effectiveness,
                    "embedding": json.dumps(embedding.tolist()),
                    "metadata": json.dumps(asdict(experience))
                }
            )
            session.commit()

    def update_caches(self, experience: Experience) -> None:
        """更新缓存"""
        # 内存缓存
        self.memory_cache[experience.experience_id] = experience
        self.cache_order.append(experience.experience_id)

        # 如果超过缓存大小，移除最旧的
        if len(self.memory_cache) > 1000:
            if self.cache_order:
                old_id = self.cache_order.popleft()
                if old_id in self.memory_cache:
                    del self.memory_cache[old_id]

        # Redis缓存
        self.redis_client.set(
            f"experience:{experience.experience_id}",
            pickle.dumps(experience),
            ex=self.cache_ttl
        )

    def update_indexes(self, experience: Experience) -> None:
        """更新索引"""
        exp_id = experience.experience_id

        # 标签索引
        for tag in experience.tags:
            self.tag_index[tag].add(exp_id)

        # 关键词索引
        for keyword in experience.keywords:
            self.tag_index[keyword].add(exp_id)

        # 类别索引
        self.category_index[experience.category].add(exp_id)

        # 类型索引
        self.experience_index[experience.experience_type].add(exp_id)

    def update_clusters_async(self, experience: Experience) -> None:
        """异步更新聚类"""
        # TODO: 实现异步聚类更新
        pass

    def get_experience(self, experience_id: str) -> Optional[Experience]:
        """获取经验"""
        # 从内存缓存
        if experience_id in self.memory_cache:
            return self.memory_cache[experience_id]

        # 从Redis缓存
        cached = self.redis_client.get(f"experience:{experience_id}")
        if cached:
            experience = pickle.loads(cached)
            self.memory_cache[experience_id] = experience
            return experience

        # 从数据库
        with self.SessionLocal() as session:
            result = session.execute(
                """
                SELECT metadata
                FROM coding_experiences
                WHERE experience_id = :exp_id
                """,
                {"exp_id": experience_id}
            ).first()

            if result and result.metadata:
                data = json.loads(result.metadata)
                experience = Experience(**data)
                self.update_caches(experience)
                return experience

        return None

    def update_experience(self, experience: Experience) -> None:
        """更新经验"""
        experience.updated_at = datetime.now()

        # 重新计算嵌入
        embedding = self.calculate_experience_embedding(experience)

        # 更新数据库
        self.save_to_database(experience, embedding)

        # 更新缓存
        self.update_caches(experience)

    def record_retrieval(
        self,
        query: str,
        recommendations: List[ExperienceRecommendation]
    ) -> None:
        """记录检索"""
        # TODO: 实现检索记录
        pass

    def update_statistics(
        self,
        experience: Experience,
        feedback: Dict[str, Any]
    ) -> None:
        """更新统计"""
        if feedback.get("success"):
            experience.success_count += 1
        else:
            experience.failure_count += 1

        experience.usage_count += 1

        # 更新评分
        if feedback.get("rating"):
            experience.ratings.append(feedback["rating"])

        # 添加评论
        if feedback.get("comment"):
            experience.comments.append(feedback["comment"])

        # 记录改进建议
        if feedback.get("improvement"):
            experience.improvements.append(feedback["improvement"])

    def analyze_feedback(self, feedback: Dict[str, Any]) -> Dict[str, Any]:
        """分析反馈"""
        insights = {
            "sentiment": "neutral",
            "improvements": [],
            "issues": []
        }

        # 情感分析
        if feedback.get("rating", 0) > 4:
            insights["sentiment"] = "positive"
        elif feedback.get("rating", 0) < 3:
            insights["sentiment"] = "negative"

        # 提取改进建议
        if feedback.get("improvement"):
            insights["improvements"].append(feedback["improvement"])

        # 识别问题
        if not feedback.get("success"):
            insights["issues"].append(feedback.get("error", "Unknown error"))

        return insights

    def apply_improvements(
        self,
        experience: Experience,
        improvements: List[str]
    ) -> None:
        """应用改进"""
        # 添加到改进列表
        experience.improvements.extend(improvements)

        # TODO: 实现自动改进逻辑

    def adjust_scores(
        self,
        experience: Experience,
        feedback: Dict[str, Any]
    ) -> None:
        """调整评分"""
        # 基于反馈调整各项评分
        if feedback.get("success"):
            experience.effectiveness = min(1.0, experience.effectiveness + 0.01)
            experience.reliability = min(1.0, experience.reliability + 0.01)
        else:
            experience.effectiveness = max(0.0, experience.effectiveness - 0.02)
            experience.reliability = max(0.0, experience.reliability - 0.02)

    def clone_experience(self, experience: Experience) -> Experience:
        """复制经验"""
        import copy
        return copy.deepcopy(experience)

    def adapt_to_project(
        self,
        experience: Experience,
        target_project: str
    ) -> None:
        """适配到目标项目"""
        # TODO: 实现项目适配逻辑
        pass

    def create_sharing_link(
        self,
        source_id: str,
        target_id: str,
        target_project: str
    ) -> None:
        """创建共享链接"""
        # TODO: 实现共享链接记录
        pass

    def extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        import re
        words = re.findall(r'\b\w+\b', text.lower())
        stopwords = {'the', 'is', 'at', 'which', 'on', 'and', 'a', 'an', 'as', 'are', 'was', 'were', 'been', 'be', 'to', 'for', 'in', 'of'}
        keywords = [w for w in words if w not in stopwords and len(w) > 2]
        return list(set(keywords))[:20]

    def calculate_similarity(
        self,
        vec1: np.ndarray,
        vec2: Union[np.ndarray, List[float]]
    ) -> float:
        """计算相似度"""
        if isinstance(vec2, list):
            vec2 = np.array(vec2)

        # 余弦相似度
        dot_product = np.dot(vec1, vec2)
        norm_product = np.linalg.norm(vec1) * np.linalg.norm(vec2)

        if norm_product == 0:
            return 0.0

        return float(dot_product / norm_product)

    def calculate_keyword_score(
        self,
        experience: Experience,
        keywords: List[str]
    ) -> float:
        """计算关键词得分"""
        exp_keywords = set(experience.keywords + experience.tags)
        query_keywords = set(keywords)

        if not query_keywords:
            return 0.0

        intersection = exp_keywords & query_keywords
        return len(intersection) / len(query_keywords)

    def apply_filters(
        self,
        candidates: List[Tuple[Experience, float]],
        filters: Dict[str, Any]
    ) -> List[Tuple[Experience, float]]:
        """应用过滤器"""
        filtered = []

        for experience, score in candidates:
            # 类别过滤
            if "category" in filters:
                if experience.category != filters["category"]:
                    continue

            # 效果过滤
            if "min_effectiveness" in filters:
                if experience.effectiveness < filters["min_effectiveness"]:
                    continue

            # 项目过滤
            if "project_id" in filters:
                if experience.project_id != filters["project_id"]:
                    continue

            filtered.append((experience, score))

        return filtered

    def merge_results(
        self,
        candidates: List[Tuple[Experience, float]]
    ) -> List[Tuple[Experience, float]]:
        """合并结果"""
        merged = {}

        for experience, score in candidates:
            exp_id = experience.experience_id
            if exp_id not in merged:
                merged[exp_id] = (experience, score)
            else:
                # 取最高分
                if score > merged[exp_id][1]:
                    merged[exp_id] = (experience, score)

        return list(merged.values())

    def calculate_context_match(
        self,
        experience: Experience,
        context: Dict[str, Any]
    ) -> float:
        """计算上下文匹配度"""
        match_score = 0.0
        factors = 0

        # 类别匹配
        if context.get("category") == experience.category:
            match_score += 1.0
            factors += 1

        # 标签匹配
        if context.get("tags"):
            common_tags = set(experience.tags) & set(context["tags"])
            if common_tags:
                match_score += len(common_tags) / len(context["tags"])
                factors += 1

        # 项目匹配
        if context.get("project_id") == experience.project_id:
            match_score += 0.5
            factors += 1

        if factors == 0:
            return 0.5  # 默认值

        return match_score / factors

    def calculate_time_decay(self, experience: Experience) -> float:
        """计算时间衰减"""
        age_days = (datetime.now() - experience.updated_at).days

        # 指数衰减
        decay_rate = 0.01
        return np.exp(-decay_rate * age_days)

    def analyze_expected_benefit(
        self,
        experience: Experience,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """分析预期收益"""
        return {
            "time_saved": experience.average_time_saved,
            "success_probability": experience.effectiveness,
            "quality_improvement": experience.reliability,
            "reusability": experience.reusability
        }

    def assess_risks(
        self,
        experience: Experience,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """风险评估"""
        risks = {
            "compatibility": 0.0,
            "complexity": experience.complexity,
            "reliability": 1 - experience.reliability
        }

        # 兼容性风险
        if experience.project_id != context.get("project_id"):
            risks["compatibility"] = 0.3

        # 先决条件风险
        if len(experience.prerequisites) > 3:
            risks["prerequisites"] = 0.5

        return risks

    def generate_reasoning(
        self,
        experience: Experience,
        score: float,
        query: str,
        context: Dict[str, Any]
    ) -> str:
        """生成推理说明"""
        reasoning = []

        reasoning.append(f"相关性评分: {score:.2%}")
        reasoning.append(f"历史成功率: {experience.effectiveness:.2%}")
        reasoning.append(f"已被使用 {experience.usage_count} 次")

        if experience.tags:
            reasoning.append(f"相关标签: {', '.join(experience.tags[:5])}")

        if experience.average_time_saved > 0:
            reasoning.append(f"平均节省时间: {experience.average_time_saved:.1f}分钟")

        return " | ".join(reasoning)

    def calculate_confidence(
        self,
        experience: Experience,
        score: float,
        context: Dict[str, Any]
    ) -> float:
        """计算置信度"""
        # 基础置信度
        confidence = score

        # 根据使用次数调整
        if experience.usage_count > 10:
            confidence *= 1.1
        elif experience.usage_count < 3:
            confidence *= 0.9

        # 根据成功率调整
        confidence *= experience.effectiveness

        # 根据上下文匹配调整
        context_match = self.calculate_context_match(experience, context)
        confidence *= (0.5 + context_match * 0.5)

        return min(1.0, confidence)

    def combine_solutions(self, solutions: List[str]) -> str:
        """组合多个解决方案"""
        # 简单实现：选择最长的
        return max(solutions, key=len)

    def apply_improvements_to_solution(
        self,
        solution: str,
        improvements: List[str]
    ) -> str:
        """将改进应用到解决方案"""
        # 简单实现：添加改进说明
        improved = solution
        if improvements:
            improved += "\n\n改进建议:\n"
            for imp in improvements[:5]:
                improved += f"- {imp}\n"
        return improved


# ============================================
# 单例模式
# ============================================

_experience_manager_instance: Optional[ExperienceManagementSystem] = None

def get_experience_manager() -> ExperienceManagementSystem:
    """获取经验管理系统单例"""
    global _experience_manager_instance
    if _experience_manager_instance is None:
        _experience_manager_instance = ExperienceManagementSystem()
    return _experience_manager_instance
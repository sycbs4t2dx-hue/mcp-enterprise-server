#!/usr/bin/env python3
"""
质量守护者服务

持续监控项目代码质量，检测代码异味，评估技术债务
"""

import os
from typing import List, Dict, Any, Optional, Set, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
from sqlalchemy import Column, String, Integer, Float, Text, JSON, DateTime, ForeignKey, Index, func, Boolean
from sqlalchemy.orm import Session
# from sqlalchemy.ext.declarative import declarative_base  # ❌ 已废弃
from mcp_core.models.base import Base

from .code_knowledge_service import CodeKnowledgeGraphService, CodeEntityModel, CodeRelationModel

# Base = declarative_base()  # ❌ 已废弃: 使用统一的Base


# ==================== 数据模型 ====================

class QualityIssue(Base):
    """质量问题记录"""
    __tablename__ = "quality_issues"
    __table_args__ = (
        Index('idx_project_type', 'project_id', 'issue_type'),
        Index('idx_severity', 'severity'),
        Index('idx_status', 'status'),
        {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"}
    )

    issue_id = Column(String(64), primary_key=True)
    project_id = Column(String(64), ForeignKey('code_projects.project_id', ondelete='CASCADE'), nullable=False)

    # 问题类型
    issue_type = Column(String(64), nullable=False)  # circular_dependency, long_function, duplicate_code, god_class, tight_coupling
    severity = Column(String(32), nullable=False)   # low, medium, high, critical

    # 关联信息
    entity_id = Column(String(64))  # 关联的代码实体
    file_path = Column(String(512))
    line_number = Column(Integer)

    # 问题描述
    title = Column(String(255), nullable=False)
    description = Column(Text)
    suggestion = Column(Text)

    # 详细数据
    meta_data = Column(JSON, default=dict)  # 详细信息（JSON）

    # 状态
    status = Column(String(32), default="open")  # open, in_progress, resolved, ignored
    detected_at = Column(DateTime, server_default=func.now())
    resolved_at = Column(DateTime)
    resolved_by = Column(String(255))

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class DebtSnapshot(Base):
    """技术债务快照"""
    __tablename__ = "debt_snapshots"
    __table_args__ = (
        Index('idx_project_date', 'project_id', 'created_at'),
        {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"}
    )

    snapshot_id = Column(String(64), primary_key=True)
    project_id = Column(String(64), ForeignKey('code_projects.project_id', ondelete='CASCADE'), nullable=False)

    # 总体评分
    overall_score = Column(Float, nullable=False)  # 0-10分

    # 各维度评分
    code_quality_score = Column(Float)
    test_quality_score = Column(Float)
    documentation_score = Column(Float)
    dependencies_score = Column(Float)
    todos_score = Column(Float)

    # 统计
    issues_count = Column(Integer, default=0)
    critical_issues = Column(Integer, default=0)
    high_issues = Column(Integer, default=0)
    medium_issues = Column(Integer, default=0)
    low_issues = Column(Integer, default=0)

    estimated_days_to_fix = Column(Float)

    # 详细数据
    meta_data = Column(JSON, default=dict)

    created_at = Column(DateTime, server_default=func.now())


class QualityWarning(Base):
    """质量预警"""
    __tablename__ = "quality_warnings"
    __table_args__ = (
        Index('idx_project_type', 'project_id', 'warning_type'),
        Index('idx_predicted_date', 'predicted_date'),
        {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"}
    )

    warning_id = Column(String(64), primary_key=True)
    project_id = Column(String(64), ForeignKey('code_projects.project_id', ondelete='CASCADE'), nullable=False)

    warning_type = Column(String(64), nullable=False)  # complexity_growth, performance_bottleneck, maintenance_burden
    entity_id = Column(String(64))
    severity = Column(String(32), nullable=False)

    # 预测信息
    predicted_date = Column(DateTime)  # 预测问题发生日期
    message = Column(Text, nullable=False)
    suggestion = Column(Text)

    # 元数据
    meta_data = Column(JSON, default=dict)

    # 状态
    acknowledged = Column(Boolean, default=False)
    acknowledged_at = Column(DateTime)

    created_at = Column(DateTime, server_default=func.now())


class RefactoringSuggestion(Base):
    """重构建议"""
    __tablename__ = "refactoring_suggestions"
    __table_args__ = (
        Index('idx_project_roi', 'project_id', 'roi_score'),
        Index('idx_status', 'status'),
        {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"}
    )

    suggestion_id = Column(String(64), primary_key=True)
    project_id = Column(String(64), ForeignKey('code_projects.project_id', ondelete='CASCADE'), nullable=False)
    issue_id = Column(String(64), ForeignKey('quality_issues.issue_id', ondelete='CASCADE'))

    refactoring_type = Column(String(64), nullable=False)  # extract_method, split_class, introduce_interface, etc.
    title = Column(String(255), nullable=False)

    # 重构计划
    plan = Column(JSON)  # 详细步骤（JSON）
    estimated_hours = Column(Float)
    roi_score = Column(Float)  # 投资回报率分数

    # 状态
    status = Column(String(32), default="pending")  # pending, accepted, rejected, completed
    created_at = Column(DateTime, server_default=func.now())
    applied_at = Column(DateTime)


# ==================== 质量守护服务 ====================

class QualityGuardianService:
    """质量守护服务"""

    def __init__(self, db: Session, code_service: CodeKnowledgeGraphService):
        self.db = db
        self.code_service = code_service

    # ==================== 代码异味检测 ====================

    def detect_code_smells(self, project_id: str, smell_types: Optional[List[str]] = None) -> List[QualityIssue]:
        """检测代码异味"""
        issues = []

        # 如果未指定类型，检测所有类型
        if not smell_types:
            smell_types = [
                "circular_dependency",
                "long_function",
                "duplicate_code",
                "god_class",
                "tight_coupling"
            ]

        if "circular_dependency" in smell_types:
            issues.extend(self._detect_circular_dependencies(project_id))

        if "long_function" in smell_types:
            issues.extend(self._detect_long_functions(project_id))

        if "god_class" in smell_types:
            issues.extend(self._detect_god_classes(project_id))

        if "tight_coupling" in smell_types:
            issues.extend(self._detect_tight_coupling(project_id))

        # 保存到数据库
        for issue in issues:
            self.db.add(issue)

        self.db.commit()

        return issues

    def _detect_circular_dependencies(self, project_id: str) -> List[QualityIssue]:
        """检测循环依赖"""
        issues = []

        # 获取所有import和depends关系
        relations = self.code_service.query_relations(
            project_id=project_id,
            relation_type="imports"
        )

        # 构建依赖图
        graph = defaultdict(list)
        for rel in relations:
            graph[rel.source_id].append(rel.target_id)

        # DFS检测环
        def find_cycles():
            visited = set()
            rec_stack = set()
            cycles = []

            def dfs(node, path):
                visited.add(node)
                rec_stack.add(node)
                path.append(node)

                for neighbor in graph.get(node, []):
                    if neighbor not in visited:
                        dfs(neighbor, path)
                    elif neighbor in rec_stack:
                        # 找到环
                        cycle_start = path.index(neighbor)
                        cycle = path[cycle_start:] + [neighbor]
                        cycles.append(cycle)

                path.pop()
                rec_stack.remove(node)

            for node in graph.keys():
                if node not in visited:
                    dfs(node, [])

            return cycles

        cycles = find_cycles()

        # 为每个环创建问题记录
        for cycle in cycles:
            if len(cycle) >= 2:  # 至少2个节点的环
                import uuid
                issue_id = f"issue_{uuid.uuid4().hex[:16]}"

                # 获取实体名称
                entity_names = []
                for entity_id in cycle[:-1]:  # 排除重复的最后一个
                    entity = self.code_service.query_entity(project_id, entity_id)
                    if entity:
                        entity_names.append(entity.name)

                cycle_path = " → ".join(entity_names + [entity_names[0]])

                issue = QualityIssue(
                    issue_id=issue_id,
                    project_id=project_id,
                    issue_type="circular_dependency",
                    severity="high" if len(cycle) <= 3 else "critical",
                    title=f"循环依赖: {len(cycle)-1}个模块",
                    description=f"检测到循环依赖: {cycle_path}",
                    suggestion="建议: 引入依赖注入或事件总线解耦，或重新设计模块边界",
                    meta_data={
                        "cycle": cycle,
                        "cycle_length": len(cycle) - 1,
                        "entities": entity_names
                    }
                )
                issues.append(issue)

        return issues

    def _detect_long_functions(self, project_id: str) -> List[QualityIssue]:
        """检测过长函数"""
        issues = []

        # 获取所有函数和方法
        functions = self.code_service.query_entities_by_type(project_id, "function")
        methods = self.code_service.query_entities_by_type(project_id, "method")

        all_functions = list(functions) + list(methods)

        for func in all_functions:
            if not func.end_line or not func.line_number:
                continue

            lines_of_code = func.end_line - func.line_number

            # 判断严重程度
            if lines_of_code > 200:
                severity = "critical"
            elif lines_of_code > 100:
                severity = "high"
            elif lines_of_code > 50:
                severity = "medium"
            else:
                continue  # 不报告

            import uuid
            issue_id = f"issue_{uuid.uuid4().hex[:16]}"

            issue = QualityIssue(
                issue_id=issue_id,
                project_id=project_id,
                issue_type="long_function",
                severity=severity,
                entity_id=func.entity_id,
                file_path=func.file_path,
                line_number=func.line_number,
                title=f"过长函数: {func.name} ({lines_of_code}行)",
                description=f"函数 {func.qualified_name} 有 {lines_of_code} 行代码，超过建议的50行",
                suggestion=f"建议: 拆分为多个小函数，每个函数专注单一职责。考虑Extract Method重构模式。",
                meta_data={
                    "function_name": func.name,
                    "qualified_name": func.qualified_name,
                    "lines_of_code": lines_of_code
                }
            )
            issues.append(issue)

        return issues

    def _detect_god_classes(self, project_id: str) -> List[QualityIssue]:
        """检测上帝类（职责过多）"""
        issues = []

        # 获取所有类
        classes = self.code_service.query_entities_by_type(project_id, "class")

        for cls in classes:
            # 统计方法数
            methods = [
                e for e in self.db.query(CodeEntityModel).filter_by(
                    project_id=project_id,
                    parent_id=cls.entity_id
                ).all()
            ]

            methods_count = len(methods)
            lines_of_code = cls.end_line - cls.line_number if cls.end_line and cls.line_number else 0

            # 判断是否为上帝类
            is_god_class = False
            severity = "low"

            if methods_count > 30 or lines_of_code > 800:
                is_god_class = True
                severity = "critical"
            elif methods_count > 20 or lines_of_code > 500:
                is_god_class = True
                severity = "high"
            elif methods_count > 15 or lines_of_code > 300:
                is_god_class = True
                severity = "medium"

            if is_god_class:
                import uuid
                issue_id = f"issue_{uuid.uuid4().hex[:16]}"

                issue = QualityIssue(
                    issue_id=issue_id,
                    project_id=project_id,
                    issue_type="god_class",
                    severity=severity,
                    entity_id=cls.entity_id,
                    file_path=cls.file_path,
                    line_number=cls.line_number,
                    title=f"上帝类: {cls.name} ({methods_count}个方法, {lines_of_code}行)",
                    description=f"类 {cls.qualified_name} 职责过多，包含 {methods_count} 个方法",
                    suggestion="建议: 应用单一职责原则（SRP），将类拆分为多个专注的小类。考虑Extract Class重构模式。",
                    meta_data={
                        "class_name": cls.name,
                        "qualified_name": cls.qualified_name,
                        "methods_count": methods_count,
                        "lines_of_code": lines_of_code
                    }
                )
                issues.append(issue)

        return issues

    def _detect_tight_coupling(self, project_id: str) -> List[QualityIssue]:
        """检测过度耦合"""
        issues = []

        # 获取所有实体
        entities = self.db.query(CodeEntityModel).filter_by(project_id=project_id).all()

        for entity in entities:
            # 计算入度和出度
            fan_in = self.db.query(CodeRelationModel).filter_by(
                project_id=project_id,
                target_id=entity.entity_id
            ).count()

            fan_out = self.db.query(CodeRelationModel).filter_by(
                project_id=project_id,
                source_id=entity.entity_id
            ).count()

            # 判断耦合度
            is_tightly_coupled = False
            severity = "low"

            if fan_in > 20 or fan_out > 20:
                is_tightly_coupled = True
                severity = "high"
            elif fan_in > 10 or fan_out > 10:
                is_tightly_coupled = True
                severity = "medium"

            if is_tightly_coupled:
                import uuid
                issue_id = f"issue_{uuid.uuid4().hex[:16]}"

                coupling_type = "被过度依赖" if fan_in > fan_out else "依赖过多"

                issue = QualityIssue(
                    issue_id=issue_id,
                    project_id=project_id,
                    issue_type="tight_coupling",
                    severity=severity,
                    entity_id=entity.entity_id,
                    file_path=entity.file_path,
                    line_number=entity.line_number,
                    title=f"过度耦合: {entity.name} ({coupling_type})",
                    description=f"{entity.qualified_name} 耦合度过高 (入度: {fan_in}, 出度: {fan_out})",
                    suggestion="建议: 引入接口层或依赖注入降低耦合度。考虑应用依赖倒置原则（DIP）。",
                    meta_data={
                        "entity_name": entity.name,
                        "qualified_name": entity.qualified_name,
                        "fan_in": fan_in,
                        "fan_out": fan_out,
                        "coupling_ratio": fan_in / fan_out if fan_out > 0 else fan_in
                    }
                )
                issues.append(issue)

        return issues

    # ==================== 技术债务评估 ====================

    def assess_technical_debt(self, project_id: str) -> DebtSnapshot:
        """评估技术债务"""
        import uuid

        # 获取所有未解决的问题
        open_issues = self.db.query(QualityIssue).filter_by(
            project_id=project_id,
            status="open"
        ).all()

        # 按严重程度统计
        critical_count = len([i for i in open_issues if i.severity == "critical"])
        high_count = len([i for i in open_issues if i.severity == "high"])
        medium_count = len([i for i in open_issues if i.severity == "medium"])
        low_count = len([i for i in open_issues if i.severity == "low"])

        # 计算代码质量分数 (0-10)
        # 权重: critical=4, high=2, medium=1, low=0.5
        issue_score_deduction = (critical_count * 4 + high_count * 2 + medium_count * 1 + low_count * 0.5)
        code_quality_score = max(0, 10 - issue_score_deduction / 10)

        # TODO: 实现其他维度的评分
        test_quality_score = 7.0  # 暂时固定值
        documentation_score = 6.5  # 暂时固定值
        dependencies_score = 8.0  # 暂时固定值
        todos_score = 7.5  # 暂时固定值

        # 计算总体分数（加权平均）
        overall_score = (
            code_quality_score * 0.4 +
            test_quality_score * 0.25 +
            documentation_score * 0.15 +
            dependencies_score * 0.1 +
            todos_score * 0.1
        )

        # 预估修复时间
        estimated_hours = critical_count * 8 + high_count * 4 + medium_count * 2 + low_count * 1
        estimated_days = estimated_hours / 8

        snapshot = DebtSnapshot(
            snapshot_id=f"snapshot_{uuid.uuid4().hex[:16]}",
            project_id=project_id,
            overall_score=round(overall_score, 2),
            code_quality_score=round(code_quality_score, 2),
            test_quality_score=test_quality_score,
            documentation_score=documentation_score,
            dependencies_score=dependencies_score,
            todos_score=todos_score,
            issues_count=len(open_issues),
            critical_issues=critical_count,
            high_issues=high_count,
            medium_issues=medium_count,
            low_issues=low_count,
            estimated_days_to_fix=round(estimated_days, 1)
        )

        self.db.add(snapshot)
        self.db.commit()
        self.db.refresh(snapshot)

        return snapshot

    def identify_debt_hotspots(self, project_id: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """识别技术债务热点"""
        # 按文件分组统计问题
        file_issues = defaultdict(list)

        open_issues = self.db.query(QualityIssue).filter_by(
            project_id=project_id,
            status="open"
        ).all()

        for issue in open_issues:
            if issue.file_path:
                file_issues[issue.file_path].append(issue)

        # 计算每个文件的债务分数
        hotspots = []
        for file_path, issues in file_issues.items():
            # 债务分数 = 严重问题*4 + 高*2 + 中*1 + 低*0.5
            debt_score = sum(
                4 if i.severity == "critical" else
                2 if i.severity == "high" else
                1 if i.severity == "medium" else 0.5
                for i in issues
            )

            # 预估修复时间
            estimated_hours = sum(
                8 if i.severity == "critical" else
                4 if i.severity == "high" else
                2 if i.severity == "medium" else 1
                for i in issues
            )

            hotspots.append({
                "file": file_path,
                "debt_score": round(debt_score, 2),
                "issues_count": len(issues),
                "main_issues": [
                    f"{i.severity.upper()}: {i.title}"
                    for i in sorted(issues, key=lambda x: {"critical": 0, "high": 1, "medium": 2, "low": 3}[x.severity])[:3]
                ],
                "estimated_hours": estimated_hours,
                "priority": "critical" if debt_score >= 8 else "high" if debt_score >= 4 else "medium"
            })

        # 按债务分数排序
        hotspots.sort(key=lambda x: x["debt_score"], reverse=True)

        return hotspots[:top_k]

    def get_quality_trends(self, project_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """获取质量趋势"""
        since_date = datetime.now() - timedelta(days=days)

        snapshots = self.db.query(DebtSnapshot).filter(
            DebtSnapshot.project_id == project_id,
            DebtSnapshot.created_at >= since_date
        ).order_by(DebtSnapshot.created_at).all()

        return [
            {
                "date": s.created_at.isoformat(),
                "overall_score": s.overall_score,
                "issues_count": s.issues_count,
                "estimated_days": s.estimated_days_to_fix
            }
            for s in snapshots
        ]

    # ==================== 辅助方法 ====================

    def resolve_issue(self, issue_id: str, resolved_by: str = "auto") -> None:
        """标记问题已解决"""
        issue = self.db.query(QualityIssue).filter_by(issue_id=issue_id).first()
        if issue:
            issue.status = "resolved"
            issue.resolved_at = datetime.now()
            issue.resolved_by = resolved_by
            self.db.commit()

    def ignore_issue(self, issue_id: str) -> None:
        """忽略问题"""
        issue = self.db.query(QualityIssue).filter_by(issue_id=issue_id).first()
        if issue:
            issue.status = "ignored"
            self.db.commit()


# ==================== 测试代码 ====================

def test_quality_guardian():
    """测试质量守护"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    import logging

    logger = logging.getLogger(__name__)

    DB_URL = "mysql+pymysql://root:Wxwy.2025%40%23@localhost:3306/mcp_db?charset=utf8mb4"
    engine = create_engine(DB_URL)
    Base.metadata.create_all(engine)

    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    code_service = CodeKnowledgeGraphService(db)
    quality_service = QualityGuardianService(db, code_service)

    logger.info("=" * 60)
    logger.info("质量守护者测试")
    logger.info("=" * 60)

    # 测试项目
    project_id = "test_project_001"

    # 检测代码异味
    logger.info("\n检测代码异味...")
    issues = quality_service.detect_code_smells(project_id)
    logger.info(f"✅ 检测到 {len(issues)} 个问题")

    # 评估技术债务
    logger.info("\n评估技术债务...")
    snapshot = quality_service.assess_technical_debt(project_id)
    logger.info(f"✅ 总体评分: {snapshot.overall_score}/10")
    logger.info(f"   问题数量: {snapshot.issues_count}")
    logger.info(f"   预估修复: {snapshot.estimated_days_to_fix}天")

    # 识别热点
    logger.info("\n识别债务热点...")
    hotspots = quality_service.identify_debt_hotspots(project_id, top_k=5)
    logger.info(f"✅ 发现 {len(hotspots)} 个热点")
    for i, hotspot in enumerate(hotspots, 1):
        logger.info(f"{i}. {hotspot['file']} (分数: {hotspot['debt_score']})")

    db.close()


if __name__ == "__main__":
    test_quality_guardian()

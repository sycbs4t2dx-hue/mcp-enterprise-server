#!/usr/bin/env python3
"""
质量守护者 - MCP工具

提供代码质量检测、技术债务评估等MCP工具
"""

from typing import Dict, Any, List
from .quality_guardian_service import QualityGuardianService


# ==================== MCP工具定义 ====================

QUALITY_GUARDIAN_TOOLS = [
    {
        "name": "detect_code_smells",
        "description": "检测代码异味（循环依赖、过长函数、上帝类、过度耦合等）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "项目ID"
                },
                "smell_types": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["circular_dependency", "long_function", "god_class", "tight_coupling"]
                    },
                    "description": "要检测的异味类型（可选，默认全部）"
                }
            },
            "required": ["project_id"]
        }
    },
    {
        "name": "assess_technical_debt",
        "description": "评估项目技术债务，生成质量评分和债务快照",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "项目ID"
                }
            },
            "required": ["project_id"]
        }
    },
    {
        "name": "identify_debt_hotspots",
        "description": "识别技术债务热点，找出最需要重构的文件",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "项目ID"
                },
                "top_k": {
                    "type": "integer",
                    "description": "返回前K个热点（默认10）",
                    "default": 10
                }
            },
            "required": ["project_id"]
        }
    },
    {
        "name": "get_quality_trends",
        "description": "获取项目质量趋势（过去N天）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "项目ID"
                },
                "days": {
                    "type": "integer",
                    "description": "查询天数（默认30天）",
                    "default": 30
                }
            },
            "required": ["project_id"]
        }
    },
    {
        "name": "resolve_quality_issue",
        "description": "标记质量问题已解决",
        "inputSchema": {
            "type": "object",
            "properties": {
                "issue_id": {
                    "type": "string",
                    "description": "问题ID"
                },
                "resolved_by": {
                    "type": "string",
                    "description": "解决人"
                }
            },
            "required": ["issue_id"]
        }
    },
    {
        "name": "ignore_quality_issue",
        "description": "忽略质量问题（标记为不需要修复）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "issue_id": {
                    "type": "string",
                    "description": "问题ID"
                }
            },
            "required": ["issue_id"]
        }
    },
    {
        "name": "generate_quality_report",
        "description": "生成完整的代码质量报告（Markdown格式）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "项目ID"
                }
            },
            "required": ["project_id"]
        }
    },
    {
        "name": "list_quality_issues",
        "description": "列出项目的所有质量问题",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "项目ID"
                },
                "severity": {
                    "type": "string",
                    "enum": ["critical", "high", "medium", "low"],
                    "description": "按严重程度筛选（可选）"
                },
                "status": {
                    "type": "string",
                    "enum": ["open", "in_progress", "resolved", "ignored"],
                    "description": "按状态筛选（可选）"
                }
            },
            "required": ["project_id"]
        }
    }
]


# ==================== 工具实现 ====================

class QualityGuardianTools:
    """质量守护者工具"""

    def __init__(self, quality_service: QualityGuardianService):
        self.quality_service = quality_service

    def detect_code_smells(self, project_id: str, smell_types: List[str] = None) -> Dict[str, Any]:
        """检测代码异味"""
        try:
            issues = self.quality_service.detect_code_smells(project_id, smell_types)

            # 按严重程度分组
            by_severity = {
                "critical": [],
                "high": [],
                "medium": [],
                "low": []
            }

            for issue in issues:
                by_severity[issue.severity].append({
                    "issue_id": issue.issue_id,
                    "type": issue.issue_type,
                    "title": issue.title,
                    "file": issue.file_path,
                    "line": issue.line_number,
                    "suggestion": issue.suggestion
                })

            return {
                "success": True,
                "total_issues": len(issues),
                "by_severity": {
                    "critical": len(by_severity["critical"]),
                    "high": len(by_severity["high"]),
                    "medium": len(by_severity["medium"]),
                    "low": len(by_severity["low"])
                },
                "issues": {
                    "critical": by_severity["critical"],
                    "high": by_severity["high"],
                    "medium": by_severity["medium"][:5],  # 只返回前5个中等问题
                    "low": []  # 不返回低级问题
                },
                "message": f"✅ 检测完成，发现 {len(issues)} 个代码异味"
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def assess_technical_debt(self, project_id: str) -> Dict[str, Any]:
        """评估技术债务"""
        try:
            snapshot = self.quality_service.assess_technical_debt(project_id)

            # 获取债务等级
            if snapshot.overall_score >= 8:
                debt_level = "excellent"
            elif snapshot.overall_score >= 6:
                debt_level = "good"
            elif snapshot.overall_score >= 4:
                debt_level = "medium"
            else:
                debt_level = "high"

            return {
                "success": True,
                "snapshot_id": snapshot.snapshot_id,
                "overall_score": snapshot.overall_score,
                "debt_level": debt_level,
                "breakdown": {
                    "code_quality": snapshot.code_quality_score,
                    "test_quality": snapshot.test_quality_score,
                    "documentation": snapshot.documentation_score,
                    "dependencies": snapshot.dependencies_score,
                    "todos": snapshot.todos_score
                },
                "issues_summary": {
                    "total": snapshot.issues_count,
                    "critical": snapshot.critical_issues,
                    "high": snapshot.high_issues,
                    "medium": snapshot.medium_issues,
                    "low": snapshot.low_issues
                },
                "estimated_days_to_fix": snapshot.estimated_days_to_fix,
                "message": f"✅ 技术债务评分: {snapshot.overall_score}/10 ({debt_level})"
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def identify_debt_hotspots(self, project_id: str, top_k: int = 10) -> Dict[str, Any]:
        """识别债务热点"""
        try:
            hotspots = self.quality_service.identify_debt_hotspots(project_id, top_k)

            return {
                "success": True,
                "total_hotspots": len(hotspots),
                "hotspots": hotspots,
                "message": f"✅ 发现 {len(hotspots)} 个技术债务热点"
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_quality_trends(self, project_id: str, days: int = 30) -> Dict[str, Any]:
        """获取质量趋势"""
        try:
            trends = self.quality_service.get_quality_trends(project_id, days)

            # 计算趋势方向
            if len(trends) >= 2:
                recent_score = trends[-1]["overall_score"]
                old_score = trends[0]["overall_score"]
                trend_direction = "improving" if recent_score > old_score else "declining" if recent_score < old_score else "stable"
            else:
                trend_direction = "insufficient_data"

            return {
                "success": True,
                "period_days": days,
                "data_points": len(trends),
                "trend_direction": trend_direction,
                "trends": trends,
                "message": f"✅ 获取到 {days} 天的质量趋势数据"
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def resolve_quality_issue(self, issue_id: str, resolved_by: str = "user") -> Dict[str, Any]:
        """解决质量问题"""
        try:
            self.quality_service.resolve_issue(issue_id, resolved_by)
            return {
                "success": True,
                "issue_id": issue_id,
                "message": f"✅ 问题已标记为解决"
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def ignore_quality_issue(self, issue_id: str) -> Dict[str, Any]:
        """忽略质量问题"""
        try:
            self.quality_service.ignore_issue(issue_id)
            return {
                "success": True,
                "issue_id": issue_id,
                "message": f"✅ 问题已标记为忽略"
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def generate_quality_report(self, project_id: str) -> Dict[str, Any]:
        """生成质量报告"""
        try:
            # 获取各项数据
            snapshot = self.quality_service.assess_technical_debt(project_id)
            hotspots = self.quality_service.identify_debt_hotspots(project_id, 5)
            issues = self.quality_service.db.query(
                self.quality_service.db.query.__self__.query.__class__
            ).filter_by(project_id=project_id, status="open").all()

            # 生成Markdown报告
            report = f"""# 代码质量报告

## 总体评分: {snapshot.overall_score}/10

{'🟢' if snapshot.overall_score >= 8 else '🟡' if snapshot.overall_score >= 6 else '🟠' if snapshot.overall_score >= 4 else '🔴'} 债务等级: {'优秀' if snapshot.overall_score >= 8 else '良好' if snapshot.overall_score >= 6 else '中等' if snapshot.overall_score >= 4 else '严重'}

## 各维度评分

| 维度 | 评分 | 状态 |
|------|------|------|
| 代码质量 | {snapshot.code_quality_score}/10 | {'✅' if snapshot.code_quality_score >= 7 else '⚠️'} |
| 测试质量 | {snapshot.test_quality_score}/10 | {'✅' if snapshot.test_quality_score >= 7 else '⚠️'} |
| 文档完整度 | {snapshot.documentation_score}/10 | {'✅' if snapshot.documentation_score >= 7 else '⚠️'} |
| 依赖健康度 | {snapshot.dependencies_score}/10 | {'✅' if snapshot.dependencies_score >= 7 else '⚠️'} |
| TODO管理 | {snapshot.todos_score}/10 | {'✅' if snapshot.todos_score >= 7 else '⚠️'} |

## 问题统计

- **总问题数**: {snapshot.issues_count}
  - 🔴 严重: {snapshot.critical_issues}
  - 🟠 高: {snapshot.high_issues}
  - 🟡 中等: {snapshot.medium_issues}
  - ⚪ 低: {snapshot.low_issues}

- **预估修复时间**: {snapshot.estimated_days_to_fix}天

## 技术债务热点 (Top 5)

{chr(10).join([f"{i+1}. **{h['file']}** (分数: {h['debt_score']}, {h['issues_count']}个问题)" for i, h in enumerate(hotspots)])}

## 建议

1. 优先处理 {snapshot.critical_issues} 个严重问题
2. 重点关注债务热点文件
3. 制定重构计划，逐步降低技术债务

---

*报告生成时间: {snapshot.created_at.isoformat()}*
"""

            return {
                "success": True,
                "report": report,
                "message": "✅ 质量报告已生成"
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_quality_issues(self, project_id: str, severity: str = None, status: str = None) -> Dict[str, Any]:
        """列出质量问题"""
        try:
            query = self.quality_service.db.query(
                self.quality_service.QualityIssue.__class__
            ).filter_by(project_id=project_id)

            if severity:
                query = query.filter_by(severity=severity)
            if status:
                query = query.filter_by(status=status)

            issues = query.all()

            return {
                "success": True,
                "total": len(issues),
                "issues": [
                    {
                        "issue_id": issue.issue_id,
                        "type": issue.issue_type,
                        "severity": issue.severity,
                        "title": issue.title,
                        "file": issue.file_path,
                        "line": issue.line_number,
                        "status": issue.status,
                        "detected_at": issue.detected_at.isoformat() if issue.detected_at else None
                    }
                    for issue in issues
                ]
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

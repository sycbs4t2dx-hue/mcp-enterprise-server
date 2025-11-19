#!/usr/bin/env python3
"""
项目上下文管理 - MCP工具

提供MCP工具供AI使用，管理开发会话、设计决策、TODO等
"""

from typing import List, Dict, Any
from .project_context_service import ProjectContextManager


# ==================== MCP工具定义 ====================

MCP_TOOLS = [
    {
        "name": "start_dev_session",
        "description": "开始新的开发会话。记录本次开发的目标，用于后续的上下文恢复。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "项目ID"
                },
                "goals": {
                    "type": "string",
                    "description": "本次开发的目标（例如：实现用户认证模块、修复订单bug）"
                }
            },
            "required": ["project_id", "goals"]
        }
    },
    {
        "name": "end_dev_session",
        "description": "结束开发会话，总结本次完成的内容和下次继续点。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "会话ID"
                },
                "achievements": {
                    "type": "string",
                    "description": "本次完成的内容"
                },
                "next_steps": {
                    "type": "string",
                    "description": "下次继续的步骤（可选）"
                },
                "files_modified": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "修改的文件列表（可选）"
                }
            },
            "required": ["session_id", "achievements"]
        }
    },
    {
        "name": "record_design_decision",
        "description": "记录重要的设计决策，包括为什么选择某个方案、考虑过哪些替代方案。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "项目ID"
                },
                "title": {
                    "type": "string",
                    "description": "决策标题（例如：使用JWT进行身份认证）"
                },
                "reasoning": {
                    "type": "string",
                    "description": "选择这个方案的原因"
                },
                "category": {
                    "type": "string",
                    "enum": ["architecture", "technology", "pattern", "optimization"],
                    "description": "决策类别"
                },
                "description": {
                    "type": "string",
                    "description": "决策的详细描述（可选）"
                },
                "alternatives": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "pros": {"type": "string"},
                            "cons": {"type": "string"}
                        }
                    },
                    "description": "考虑过的其他方案（可选）"
                },
                "impact_scope": {
                    "type": "string",
                    "description": "影响范围（可选）"
                }
            },
            "required": ["project_id", "title", "reasoning"]
        }
    },
    {
        "name": "add_project_note",
        "description": "添加项目笔记，记录陷阱、技巧、待优化点等。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "项目ID"
                },
                "category": {
                    "type": "string",
                    "enum": ["pitfall", "tip", "optimization", "issue", "reminder"],
                    "description": "笔记类别"
                },
                "title": {
                    "type": "string",
                    "description": "笔记标题"
                },
                "content": {
                    "type": "string",
                    "description": "笔记内容"
                },
                "importance": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 5,
                    "description": "重要性（1-5，5最重要）"
                },
                "related_code": {
                    "type": "string",
                    "description": "相关代码片段（可选）"
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "标签（可选）"
                }
            },
            "required": ["project_id", "category", "title", "content"]
        }
    },
    {
        "name": "create_todo",
        "description": "创建开发TODO，记录需要完成的任务。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "项目ID"
                },
                "title": {
                    "type": "string",
                    "description": "TODO标题"
                },
                "description": {
                    "type": "string",
                    "description": "详细描述"
                },
                "category": {
                    "type": "string",
                    "enum": ["feature", "bugfix", "refactor", "test", "documentation"],
                    "description": "类别"
                },
                "priority": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 5,
                    "description": "优先级（1-5，5最高）"
                },
                "estimated_hours": {
                    "type": "integer",
                    "description": "预估工时（小时）"
                },
                "depends_on": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "依赖的其他TODO ID"
                }
            },
            "required": ["project_id", "title"]
        }
    },
    {
        "name": "update_todo_status",
        "description": "更新TODO状态（pending/in_progress/completed/blocked）。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "todo_id": {
                    "type": "string",
                    "description": "TODO ID"
                },
                "status": {
                    "type": "string",
                    "enum": ["pending", "in_progress", "completed", "blocked", "cancelled"],
                    "description": "新状态"
                },
                "progress": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 100,
                    "description": "进度（0-100）"
                },
                "completion_note": {
                    "type": "string",
                    "description": "完成备注"
                }
            },
            "required": ["todo_id", "status"]
        }
    },
    {
        "name": "get_project_context",
        "description": "获取项目当前上下文，包括最近的会话、进行中的TODO、未解决的问题等。用于快速恢复开发状态。",
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
        "name": "list_todos",
        "description": "列出项目的TODO列表，可按状态、类别、优先级筛选。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "项目ID"
                },
                "status": {
                    "type": "string",
                    "enum": ["pending", "in_progress", "completed", "blocked", "cancelled"],
                    "description": "按状态筛选（可选）"
                },
                "category": {
                    "type": "string",
                    "description": "按类别筛选（可选）"
                },
                "min_priority": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 5,
                    "description": "最低优先级（可选）"
                }
            },
            "required": ["project_id"]
        }
    },
    {
        "name": "get_next_todo",
        "description": "获取建议的下一个TODO（考虑依赖关系和优先级）。",
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
        "name": "list_design_decisions",
        "description": "列出项目的设计决策记录。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "项目ID"
                },
                "category": {
                    "type": "string",
                    "description": "按类别筛选（可选）"
                }
            },
            "required": ["project_id"]
        }
    },
    {
        "name": "list_project_notes",
        "description": "列出项目笔记（陷阱、技巧、优化点等）。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "项目ID"
                },
                "category": {
                    "type": "string",
                    "description": "按类别筛选（可选）"
                },
                "min_importance": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 5,
                    "description": "最低重要性（可选）"
                },
                "unresolved_only": {
                    "type": "boolean",
                    "description": "只显示未解决的（可选）"
                }
            },
            "required": ["project_id"]
        }
    },
    {
        "name": "get_project_statistics",
        "description": "获取项目的统计信息（会话数、开发时间、TODO完成率等）。",
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
    }
]


# ==================== 工具实现 ====================

class ProjectContextTools:
    """项目上下文管理工具"""

    def __init__(self, manager: ProjectContextManager):
        self.manager = manager

    def start_dev_session(self, project_id: str, goals: str) -> Dict[str, Any]:
        """开始开发会话"""
        try:
            session = self.manager.start_session(project_id, goals)
            return {
                "success": True,
                "session_id": session.session_id,
                "project_id": session.project_id,
                "start_time": session.start_time.isoformat(),
                "goals": session.goals,
                "message": f"✅ 开发会话已开始: {session.session_id}"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def end_dev_session(self,
                       session_id: str,
                       achievements: str,
                       next_steps: str = None,
                       files_modified: List[str] = None) -> Dict[str, Any]:
        """结束开发会话"""
        try:
            session = self.manager.end_session(
                session_id=session_id,
                achievements=achievements,
                next_steps=next_steps,
                files_modified=files_modified
            )
            return {
                "success": True,
                "session_id": session.session_id,
                "duration_minutes": session.duration_minutes,
                "achievements": session.achievements,
                "next_steps": session.next_steps,
                "message": f"✅ 开发会话已结束，持续 {session.duration_minutes} 分钟"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def record_design_decision(self,
                              project_id: str,
                              title: str,
                              reasoning: str,
                              category: str = "architecture",
                              description: str = None,
                              alternatives: List[Dict] = None,
                              impact_scope: str = None) -> Dict[str, Any]:
        """记录设计决策"""
        try:
            decision = self.manager.record_decision(
                project_id=project_id,
                title=title,
                reasoning=reasoning,
                category=category,
                description=description,
                alternatives=alternatives,
                impact_scope=impact_scope
            )
            return {
                "success": True,
                "decision_id": decision.decision_id,
                "title": decision.title,
                "category": decision.category,
                "message": f"✅ 设计决策已记录: {title}"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def add_project_note(self,
                        project_id: str,
                        category: str,
                        title: str,
                        content: str,
                        importance: int = 3,
                        related_code: str = None,
                        tags: List[str] = None) -> Dict[str, Any]:
        """添加项目笔记"""
        try:
            note = self.manager.add_note(
                project_id=project_id,
                category=category,
                title=title,
                content=content,
                importance=importance,
                related_code=related_code,
                tags=tags
            )
            return {
                "success": True,
                "note_id": note.note_id,
                "title": note.title,
                "category": note.category,
                "importance": note.importance,
                "message": f"✅ 笔记已添加: {title}"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def create_todo(self,
                   project_id: str,
                   title: str,
                   description: str = None,
                   category: str = "feature",
                   priority: int = 3,
                   estimated_hours: int = None,
                   depends_on: List[str] = None) -> Dict[str, Any]:
        """创建TODO"""
        try:
            todo = self.manager.create_todo(
                project_id=project_id,
                title=title,
                description=description,
                category=category,
                priority=priority,
                estimated_hours=estimated_hours,
                depends_on=depends_on
            )
            return {
                "success": True,
                "todo_id": todo.todo_id,
                "title": todo.title,
                "priority": todo.priority,
                "category": todo.category,
                "message": f"✅ TODO已创建: {title}"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def update_todo_status(self,
                          todo_id: str,
                          status: str,
                          progress: int = None,
                          completion_note: str = None) -> Dict[str, Any]:
        """更新TODO状态"""
        try:
            todo = self.manager.update_todo_status(
                todo_id=todo_id,
                status=status,
                progress=progress,
                completion_note=completion_note
            )
            return {
                "success": True,
                "todo_id": todo.todo_id,
                "title": todo.title,
                "status": todo.status,
                "progress": todo.progress,
                "message": f"✅ TODO已更新: {todo.title} → {status}"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_project_context(self, project_id: str) -> Dict[str, Any]:
        """获取项目上下文"""
        try:
            context = self.manager.generate_resume_context(project_id)
            return {
                "success": True,
                "project_id": project_id,
                "context": context,
                "message": "✅ 项目上下文已加载"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_todos(self,
                  project_id: str,
                  status: str = None,
                  category: str = None,
                  min_priority: int = 1) -> Dict[str, Any]:
        """列出TODO"""
        try:
            todos = self.manager.get_todos(
                project_id=project_id,
                status=status,
                category=category,
                min_priority=min_priority
            )
            return {
                "success": True,
                "total": len(todos),
                "todos": [
                    {
                        "todo_id": todo.todo_id,
                        "title": todo.title,
                        "description": todo.description,
                        "category": todo.category,
                        "status": todo.status,
                        "priority": todo.priority,
                        "progress": todo.progress,
                        "estimated_hours": todo.estimated_hours,
                        "depends_on": todo.depends_on,
                        "created_at": todo.created_at.isoformat()
                    }
                    for todo in todos
                ]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_next_todo(self, project_id: str) -> Dict[str, Any]:
        """获取建议的下一个TODO"""
        try:
            todo = self.manager.get_next_todo(project_id)
            if not todo:
                return {
                    "success": True,
                    "message": "没有可用的TODO（所有TODO都已完成或被阻塞）"
                }
            return {
                "success": True,
                "todo": {
                    "todo_id": todo.todo_id,
                    "title": todo.title,
                    "description": todo.description,
                    "category": todo.category,
                    "priority": todo.priority,
                    "estimated_hours": todo.estimated_hours
                },
                "message": f"💡 建议下一步: {todo.title}"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_design_decisions(self, project_id: str, category: str = None) -> Dict[str, Any]:
        """列出设计决策"""
        try:
            decisions = self.manager.get_decisions(project_id, category)
            return {
                "success": True,
                "total": len(decisions),
                "decisions": [
                    {
                        "decision_id": decision.decision_id,
                        "title": decision.title,
                        "category": decision.category,
                        "reasoning": decision.reasoning,
                        "alternatives": decision.alternatives,
                        "impact_scope": decision.impact_scope,
                        "status": decision.status,
                        "created_at": decision.created_at.isoformat()
                    }
                    for decision in decisions
                ]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_project_notes(self,
                          project_id: str,
                          category: str = None,
                          min_importance: int = 1,
                          unresolved_only: bool = False) -> Dict[str, Any]:
        """列出项目笔记"""
        try:
            notes = self.manager.get_notes(
                project_id=project_id,
                category=category,
                min_importance=min_importance,
                unresolved_only=unresolved_only
            )
            return {
                "success": True,
                "total": len(notes),
                "notes": [
                    {
                        "note_id": note.note_id,
                        "category": note.category,
                        "title": note.title,
                        "content": note.content,
                        "importance": note.importance,
                        "related_code": note.related_code,
                        "tags": note.tags,
                        "is_resolved": note.is_resolved,
                        "created_at": note.created_at.isoformat()
                    }
                    for note in notes
                ]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_project_statistics(self, project_id: str) -> Dict[str, Any]:
        """获取项目统计"""
        try:
            stats = self.manager.get_project_statistics(project_id)
            return {
                "success": True,
                "project_id": project_id,
                "statistics": stats
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

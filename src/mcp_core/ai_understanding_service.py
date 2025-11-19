#!/usr/bin/env python3
"""
AI辅助代码理解服务

利用Claude API进行深度代码理解，生成上下文摘要，智能TODO分解等
"""

import os
from typing import List, Dict, Any, Optional

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    anthropic = None

from .code_knowledge_service import CodeKnowledgeGraphService
from .project_context_service import ProjectContextManager


class AICodeUnderstandingService:
    """AI辅助代码理解服务"""

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-5-sonnet-20241022"):
        """
        初始化AI服务

        Args:
            api_key: Claude API密钥（可选，也可从环境变量ANTHROPIC_API_KEY读取）
            model: 使用的模型
        """
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("anthropic包未安装，请运行: pip install anthropic")

        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("需要提供Claude API密钥或设置环境变量ANTHROPIC_API_KEY")

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = model

    def _call_claude(self, prompt: str, max_tokens: int = 4000) -> str:
        """调用Claude API"""
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return message.content[0].text
        except Exception as e:
            print(f"❌ Claude API调用失败: {e}")
            return f"AI理解失败: {str(e)}"

    # ==================== 代码理解 ====================

    def understand_function(self,
                           function_info: Dict[str, Any],
                           related_code: Optional[str] = None) -> str:
        """
        理解函数意图

        Args:
            function_info: 函数信息（来自代码知识图谱）
            related_code: 相关代码片段（可选）
        """
        # 构建相关代码部分
        related_code_section = ""
        if related_code:
            related_code_section = f"相关代码:\n```\n{related_code}\n```"

        prompt = f"""基于以下函数信息，深度理解这个函数的意图和作用：

函数名: {function_info.get('name')}
完整名称: {function_info.get('qualified_name')}
签名: {function_info.get('signature', '无')}
文件位置: {function_info.get('file_path')}:{function_info.get('line_number')}
文档字符串: {function_info.get('docstring', '无')}

元数据:
{function_info.get('metadata', {})}

{related_code_section}

请回答以下问题:
1. 这个函数的主要目的是什么？
2. 它在整体架构中扮演什么角色？
3. 有哪些边界情况或特殊逻辑需要注意？
4. 如果要修改这个函数，可能会影响哪些地方？
5. 这个函数的设计有什么优点和可能的改进点？

请用简洁清晰的中文回答。"""

        return self._call_claude(prompt)

    def understand_module(self,
                         module_name: str,
                         entities: List[Dict[str, Any]],
                         relations: List[Dict[str, Any]]) -> str:
        """
        理解模块职责

        Args:
            module_name: 模块名
            entities: 模块中的实体列表
            relations: 相关关系列表
        """
        # 统计信息
        classes = [e for e in entities if e['type'] == 'class']
        functions = [e for e in entities if e['type'] == 'function']

        prompt = f"""基于以下信息，分析模块的职责和设计：

模块名: {module_name}

包含内容:
- 类: {len(classes)}个
  {chr(10).join([f"  - {c['name']}" for c in classes[:10]])}
  {f"  ... 还有{len(classes)-10}个" if len(classes) > 10 else ""}

- 函数: {len(functions)}个
  {chr(10).join([f"  - {f['name']}" for f in functions[:10]])}
  {f"  ... 还有{len(functions)-10}个" if len(functions) > 10 else ""}

关系统计:
- 总关系数: {len(relations)}

请分析:
1. 这个模块的核心职责是什么？
2. 模块使用了哪些主要的设计模式？
3. 模块如何与其他模块交互？
4. 模块设计的优点和可以改进的地方？
5. 如果要扩展这个模块，应该注意什么？

请用简洁清晰的中文回答。"""

        return self._call_claude(prompt)

    def explain_architecture(self, project_info: Dict[str, Any]) -> str:
        """
        解释整体架构

        Args:
            project_info: 项目信息（来自代码知识图谱）
        """
        prompt = f"""基于完整的代码知识图谱，分析项目的整体架构：

项目信息:
- 项目名: {project_info.get('name')}
- 语言: {project_info.get('language')}
- 总文件数: {project_info.get('total_files')}
- 总代码行数: {project_info.get('total_lines')}

实体统计:
{project_info.get('entity_stats', {})}

关系统计:
{project_info.get('relation_stats', {})}

文件结构:
{project_info.get('file_tree', {})}

请分析:
1. 这个项目采用什么架构模式？（例如：MVC、微服务、分层架构等）
2. 核心模块及其职责是什么？
3. 数据是如何在系统中流转的？
4. 关键的设计决策有哪些？（根据代码结构推断）
5. 这个架构的优点和潜在的改进点？

请用简洁清晰的中文回答，使用Markdown格式。"""

        return self._call_claude(prompt, max_tokens=6000)

    # ==================== 会话摘要 ====================

    def generate_session_summary(self,
                                 session_info: Dict[str, Any],
                                 files_modified: List[str],
                                 achievements: str) -> str:
        """
        生成会话摘要

        Args:
            session_info: 会话信息
            files_modified: 修改的文件
            achievements: 完成的内容
        """
        prompt = f"""生成开发会话的简洁摘要：

会话时间: {session_info.get('duration_minutes')}分钟
会话目标: {session_info.get('goals')}

完成内容:
{achievements}

修改的文件:
{chr(10).join([f"- {f}" for f in files_modified]) if files_modified else "无"}

请生成一个简洁的摘要（3-5句话），包括：
1. 本次会话的主要成果
2. 关键的技术点或难点
3. 对后续开发的影响

使用中文，直接输出摘要内容，不需要标题。"""

        return self._call_claude(prompt, max_tokens=500)

    def generate_resumption_briefing(self, context: Dict[str, Any]) -> str:
        """
        生成恢复briefing

        Args:
            context: 项目上下文（来自generate_resume_context）
        """
        last_session = context.get('last_session', {})

        prompt = f"""生成开发恢复briefing，帮助开发者快速回到开发状态：

上次会话:
- 时间: {last_session.get('end_time', '未知')}
- 目标: {last_session.get('goals', '无')}
- 完成内容: {last_session.get('achievements', '无')}
- 下一步计划: {last_session.get('next_steps', '无')}
- 修改的文件: {', '.join(last_session.get('files_modified', []))}

进行中的任务:
{chr(10).join([f"- {t['title']} ({t['progress']}%)" for t in context.get('in_progress', [])])}

待处理任务（高优先级）:
{chr(10).join([f"- [{t['priority']}] {t['title']}" for t in context.get('pending_todos', [])[:5]])}

最近的设计决策:
{chr(10).join([f"- {d['title']}" for d in context.get('recent_decisions', [])])}

未解决的问题:
{chr(10).join([f"- [{n['importance']}] {n['title']}" for n in context.get('unresolved_issues', [])])}

重要提示:
{chr(10).join([f"- {n['title']}: {n['content'][:100]}..." for n in context.get('important_notes', [])])}

请生成一个清晰友好的恢复briefing，包括：
1. 欢迎语和上次开发的时间距离
2. 上次开发的状态总结
3. 代码变更情况
4. 下一步的具体建议（考虑依赖关系）
5. 需要注意的问题和提示

使用Markdown格式，语气友好自然。"""

        return self._call_claude(prompt, max_tokens=4000)

    # ==================== TODO管理 ====================

    def generate_todos_from_goal(self,
                                goal: str,
                                project_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        从目标自动生成TODO列表

        Args:
            goal: 开发目标
            project_context: 项目上下文
        """
        prompt = f"""基于以下信息，生成详细的TODO列表：

开发目标:
{goal}

当前项目状态:
- 项目名: {project_context.get('name')}
- 语言: {project_context.get('language')}
- 已有模块: {', '.join(list(project_context.get('file_tree', {}).keys())[:10])}

已完成功能:
{project_context.get('completed_features', '待提供')}

请生成具体可执行的TODO列表，每个TODO包括：
1. 标题（简洁描述任务）
2. 详细描述（具体要做什么）
3. 类别（feature/bugfix/refactor/test/documentation）
4. 优先级（1-5）
5. 预估难度（1-5）
6. 预估工时（小时）
7. 依赖关系（需要先完成哪些）
8. 可能的风险

请输出JSON格式的列表：
```json
[
  {{
    "title": "...",
    "description": "...",
    "category": "feature",
    "priority": 5,
    "estimated_difficulty": 3,
    "estimated_hours": 2,
    "depends_on": [],
    "risks": ["..."]
  }}
]
```

只输出JSON，不要其他内容。"""

        response = self._call_claude(prompt, max_tokens=4000)

        # 解析JSON
        try:
            import json
            import re
            # 提取JSON部分
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                todos = json.loads(json_match.group(1))
                return todos
            else:
                # 尝试直接解析
                return json.loads(response)
        except Exception as e:
            print(f"❌ 解析TODO失败: {e}")
            return []

    def suggest_next_task(self,
                         todos: List[Dict[str, Any]],
                         recent_completed: List[Dict[str, Any]],
                         developer_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        建议下一个应该做的任务

        Args:
            todos: 待处理TODO列表
            recent_completed: 最近完成的任务
            developer_context: 开发者状态（例如：可用时间、当前精力）
        """
        prompt = f"""基于以下信息，推荐下一个最合适的任务：

待处理任务:
{chr(10).join([f"- [{t['priority']}] {t['title']} (难度{t.get('estimated_difficulty', 3)}, 预计{t.get('estimated_hours', 2)}小时)" for t in todos[:10]])}

最近完成:
{chr(10).join([f"- {t.get('title', 'Unknown')}" for t in recent_completed[-3:]])}

开发者状态:
{developer_context}

请推荐最合适的下一个任务，考虑：
1. 任务依赖关系（必须先完成的）
2. 优先级（重要且紧急的）
3. 难度和时间（当前状态是否适合）
4. 连贯性（延续之前的思路）

请输出JSON格式：
```json
{{
  "recommended_todo": "...",
  "reason": "推荐原因",
  "preparation": ["需要准备的内容"],
  "estimated_time": "预估时间"
}}
```

只输出JSON，不要其他内容。"""

        response = self._call_claude(prompt, max_tokens=1000)

        # 解析JSON
        try:
            import json
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            else:
                return json.loads(response)
        except Exception as e:
            print(f"❌ 解析建议失败: {e}")
            return {"error": str(e)}

    def decompose_task(self, task: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        分解复杂任务为小步骤

        Args:
            task: 要分解的任务
        """
        prompt = f"""将以下复杂任务分解为可执行的小步骤：

任务标题: {task.get('title')}
任务描述: {task.get('description')}
预估难度: {task.get('estimated_difficulty')}/5
预估总工时: {task.get('estimated_hours')}小时

分解要求：
1. 每个步骤1-2小时可完成
2. 明确输入输出
3. 可独立验证
4. 有清晰的完成标准

请输出JSON格式的步骤列表：
```json
[
  {{
    "step": 1,
    "title": "...",
    "description": "...",
    "input": "需要什么",
    "output": "产出什么",
    "validation": "如何验证完成",
    "estimated_hours": 1
  }}
]
```

只输出JSON，不要其他内容。"""

        response = self._call_claude(prompt, max_tokens=3000)

        # 解析JSON
        try:
            import json
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            else:
                return json.loads(response)
        except Exception as e:
            print(f"❌ 解析步骤失败: {e}")
            return []

    # ==================== 质量分析 ====================

    def analyze_code_quality(self,
                            entity_stats: Dict[str, int],
                            relation_stats: Dict[str, int],
                            issues: List[Dict[str, Any]]) -> str:
        """
        分析代码质量

        Args:
            entity_stats: 实体统计
            relation_stats: 关系统计
            issues: 已知问题列表
        """
        prompt = f"""基于以下信息，分析代码质量并给出建议：

实体统计:
{entity_stats}

关系统计:
{relation_stats}

已知问题:
{chr(10).join([f"- [{i.get('importance')}] {i.get('title')}" for i in issues[:10]])}

请分析：
1. 整体代码质量评分（1-10分）
2. 主要优点
3. 潜在问题（架构、复杂度、耦合度等）
4. 优先改进建议（前3项）
5. 长期优化方向

使用Markdown格式，包含具体的指标和建议。"""

        return self._call_claude(prompt, max_tokens=3000)


# ==================== MCP工具定义 ====================

AI_MCP_TOOLS = [
    {
        "name": "ai_understand_function",
        "description": "使用AI深度理解函数的意图和作用。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "项目ID"},
                "entity_id": {"type": "string", "description": "函数实体ID"}
            },
            "required": ["project_id", "entity_id"]
        }
    },
    {
        "name": "ai_understand_module",
        "description": "使用AI分析模块的职责和设计。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "项目ID"},
                "module_name": {"type": "string", "description": "模块名（文件路径）"}
            },
            "required": ["project_id", "module_name"]
        }
    },
    {
        "name": "ai_explain_architecture",
        "description": "使用AI解释项目的整体架构。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "项目ID"}
            },
            "required": ["project_id"]
        }
    },
    {
        "name": "ai_generate_resumption_briefing",
        "description": "使用AI生成开发恢复briefing，快速回到开发状态。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "项目ID"}
            },
            "required": ["project_id"]
        }
    },
    {
        "name": "ai_generate_todos_from_goal",
        "description": "使用AI从开发目标自动生成详细的TODO列表。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "项目ID"},
                "goal": {"type": "string", "description": "开发目标"}
            },
            "required": ["project_id", "goal"]
        }
    },
    {
        "name": "ai_decompose_task",
        "description": "使用AI将复杂任务分解为可执行的小步骤。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "todo_id": {"type": "string", "description": "TODO ID"}
            },
            "required": ["todo_id"]
        }
    },
    {
        "name": "ai_analyze_code_quality",
        "description": "使用AI分析项目代码质量并给出改进建议。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "项目ID"}
            },
            "required": ["project_id"]
        }
    }
]


# ==================== AI工具实现类 ====================

class AIAssistantTools:
    """AI辅助工具"""

    def __init__(self,
                 ai_service: AICodeUnderstandingService,
                 code_service: CodeKnowledgeGraphService,
                 context_manager: ProjectContextManager):
        self.ai_service = ai_service
        self.code_service = code_service
        self.context_manager = context_manager

    def ai_understand_function(self, project_id: str, entity_id: str) -> Dict[str, Any]:
        """AI理解函数"""
        try:
            entity = self.code_service.query_entity(project_id, entity_id)
            if not entity:
                return {"success": False, "error": "函数不存在"}

            function_info = {
                "name": entity.name,
                "qualified_name": entity.qualified_name,
                "signature": entity.signature,
                "file_path": entity.file_path,
                "line_number": entity.line_number,
                "docstring": entity.docstring,
                "metadata": entity.metadata
            }

            understanding = self.ai_service.understand_function(function_info)
            return {
                "success": True,
                "entity_id": entity_id,
                "function_name": entity.name,
                "understanding": understanding
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def ai_understand_module(self, project_id: str, module_name: str) -> Dict[str, Any]:
        """AI理解模块"""
        try:
            entities = self.code_service.query_entities_by_file(project_id, module_name)
            if not entities:
                return {"success": False, "error": "模块不存在或为空"}

            entity_dicts = [
                {"name": e.name, "type": e.entity_type, "qualified_name": e.qualified_name}
                for e in entities
            ]

            relations = self.code_service.query_relations(project_id)
            relation_dicts = [
                {"source_id": r.source_id, "target_id": r.target_id, "type": r.relation_type}
                for r in relations
            ]

            understanding = self.ai_service.understand_module(module_name, entity_dicts, relation_dicts)
            return {
                "success": True,
                "module_name": module_name,
                "understanding": understanding
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def ai_explain_architecture(self, project_id: str) -> Dict[str, Any]:
        """AI解释架构"""
        try:
            architecture = self.code_service.query_architecture(project_id)
            explanation = self.ai_service.explain_architecture(architecture['project'])
            return {
                "success": True,
                "project_id": project_id,
                "explanation": explanation
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def ai_generate_resumption_briefing(self, project_id: str) -> Dict[str, Any]:
        """AI生成恢复briefing"""
        try:
            context = self.context_manager.generate_resume_context(project_id)
            briefing = self.ai_service.generate_resumption_briefing(context)
            return {
                "success": True,
                "project_id": project_id,
                "briefing": briefing
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def ai_generate_todos_from_goal(self, project_id: str, goal: str) -> Dict[str, Any]:
        """AI生成TODO列表"""
        try:
            architecture = self.code_service.query_architecture(project_id)
            todos = self.ai_service.generate_todos_from_goal(goal, architecture['project'])
            return {
                "success": True,
                "project_id": project_id,
                "goal": goal,
                "todos": todos,
                "message": f"✅ 已生成 {len(todos)} 个TODO"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def ai_decompose_task(self, todo_id: str) -> Dict[str, Any]:
        """AI分解任务"""
        try:
            # 这里需要从数据库获取TODO信息
            # 简化版本，实际需要完整实现
            steps = self.ai_service.decompose_task({"title": "示例任务", "description": "待实现"})
            return {
                "success": True,
                "todo_id": todo_id,
                "steps": steps
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def ai_analyze_code_quality(self, project_id: str) -> Dict[str, Any]:
        """AI分析代码质量"""
        try:
            architecture = self.code_service.query_architecture(project_id)
            issues = self.context_manager.get_notes(project_id, category="issue", unresolved_only=True)

            issue_dicts = [
                {"title": n.title, "importance": n.importance}
                for n in issues
            ]

            analysis = self.ai_service.analyze_code_quality(
                architecture['entity_stats'],
                architecture['relation_stats'],
                issue_dicts
            )

            return {
                "success": True,
                "project_id": project_id,
                "analysis": analysis
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

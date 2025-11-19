#!/usr/bin/env python3
"""
MCP代码分析工具

为MCP协议提供代码分析相关的工具
"""

from typing import Dict, Any, Optional
from pathlib import Path
import json

from .code_analyzer import ProjectAnalyzer
from .code_knowledge_service import CodeKnowledgeGraphService


class MCPCodeAnalysisTools:
    """MCP代码分析工具集"""

    def __init__(self, db_session):
        self.db = db_session
        self.knowledge_service = CodeKnowledgeGraphService(db_session)

    # ==================== 工具定义 ====================

    @staticmethod
    def get_tools_definition() -> list:
        """获取工具定义（供MCP服务端注册）"""
        return [
            {
                "name": "analyze_codebase",
                "description": "深度分析代码库，构建知识图谱。分析包括类、函数、调用关系、依赖关系等",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "项目唯一标识"
                        },
                        "project_name": {
                            "type": "string",
                            "description": "项目名称"
                        },
                        "project_path": {
                            "type": "string",
                            "description": "项目根目录绝对路径"
                        },
                        "language": {
                            "type": "string",
                            "enum": ["python", "javascript", "java"],
                            "description": "编程语言",
                            "default": "python"
                        }
                    },
                    "required": ["project_id", "project_name", "project_path"]
                }
            },
            {
                "name": "query_architecture",
                "description": "查询项目整体架构，包括模块组成、文件结构、实体统计",
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
                "name": "find_entity",
                "description": "查找特定的代码实体（类、函数、方法）",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "项目ID"
                        },
                        "entity_name": {
                            "type": "string",
                            "description": "实体名称（支持模糊搜索）"
                        },
                        "entity_type": {
                            "type": "string",
                            "enum": ["class", "function", "method", "all"],
                            "description": "实体类型",
                            "default": "all"
                        }
                    },
                    "required": ["project_id", "entity_name"]
                }
            },
            {
                "name": "trace_function_calls",
                "description": "追踪函数调用链，查看函数调用了哪些其他函数",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "项目ID"
                        },
                        "function_name": {
                            "type": "string",
                            "description": "函数名称（完全限定名）"
                        },
                        "depth": {
                            "type": "integer",
                            "description": "追踪深度（1-5）",
                            "default": 3,
                            "minimum": 1,
                            "maximum": 5
                        }
                    },
                    "required": ["project_id", "function_name"]
                }
            },
            {
                "name": "find_dependencies",
                "description": "查找实体的依赖关系（这个实体依赖谁，谁依赖这个实体）",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "项目ID"
                        },
                        "entity_name": {
                            "type": "string",
                            "description": "实体名称"
                        }
                    },
                    "required": ["project_id", "entity_name"]
                }
            },
            {
                "name": "list_modules",
                "description": "列出项目中的所有模块和文件",
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
                "name": "explain_module",
                "description": "解释某个模块的功能和包含的主要实体",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "项目ID"
                        },
                        "file_path": {
                            "type": "string",
                            "description": "文件路径（相对路径）"
                        }
                    },
                    "required": ["project_id", "file_path"]
                }
            },
            {
                "name": "search_code_pattern",
                "description": "搜索特定模式的代码（如：所有继承某个类的类）",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "项目ID"
                        },
                        "pattern": {
                            "type": "string",
                            "enum": ["inherits_from", "calls_function", "uses_decorator"],
                            "description": "搜索模式"
                        },
                        "target": {
                            "type": "string",
                            "description": "目标名称（如类名、函数名）"
                        }
                    },
                    "required": ["project_id", "pattern", "target"]
                }
            }
        ]

    # ==================== 工具实现 ====================

    def analyze_codebase(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """分析代码库"""
        project_id = args["project_id"]
        project_name = args["project_name"]
        project_path = args["project_path"]
        language = args.get("language", "python")

        try:
            # 验证路径
            if not Path(project_path).exists():
                return {
                    "success": False,
                    "error": f"路径不存在: {project_path}"
                }

            # 创建项目记录
            self.knowledge_service.create_project(
                project_id=project_id,
                name=project_name,
                path=project_path,
                language=language
            )

            # 分析代码
            analyzer = ProjectAnalyzer(project_path)
            result = analyzer.analyze_project()

            # 存储结果
            self.knowledge_service.store_analysis_result(
                project_id=project_id,
                entities=result["entities"],
                relations=result["relations"],
                stats=result["stats"]
            )

            return {
                "success": True,
                "project_id": project_id,
                "message": f"项目分析完成",
                "stats": result["stats"]
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def query_architecture(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """查询架构"""
        project_id = args["project_id"]

        try:
            result = self.knowledge_service.query_architecture(project_id)
            return {
                "success": True,
                "architecture": result
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def find_entity(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """查找实体"""
        project_id = args["project_id"]
        entity_name = args["entity_name"]
        entity_type = args.get("entity_type", "all")

        try:
            # 搜索实体
            entities = self.knowledge_service.search_by_name(project_id, entity_name, fuzzy=True)

            # 过滤类型
            if entity_type != "all":
                entities = [e for e in entities if e.entity_type == entity_type]

            # 格式化结果
            results = []
            for entity in entities[:20]:  # 最多返回20个
                results.append({
                    "name": entity.name,
                    "qualified_name": entity.qualified_name,
                    "type": entity.entity_type,
                    "file_path": entity.file_path,
                    "line_number": entity.line_number,
                    "signature": entity.signature,
                    "docstring": entity.docstring[:200] if entity.docstring else None
                })

            return {
                "success": True,
                "count": len(results),
                "entities": results
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def trace_function_calls(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """追踪函数调用"""
        project_id = args["project_id"]
        function_name = args["function_name"]
        depth = args.get("depth", 3)

        try:
            # 先找到函数实体
            entities = self.knowledge_service.search_by_name(project_id, function_name, fuzzy=False)
            function_entities = [e for e in entities if e.entity_type in ["function", "method"]]

            if not function_entities:
                return {
                    "success": False,
                    "error": f"找不到函数: {function_name}"
                }

            # 使用第一个匹配的函数
            entity = function_entities[0]

            # 追踪调用链
            call_tree = self.knowledge_service.trace_calls(project_id, entity.entity_id, depth)

            return {
                "success": True,
                "call_tree": call_tree
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def find_dependencies(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """查找依赖"""
        project_id = args["project_id"]
        entity_name = args["entity_name"]

        try:
            # 查找实体
            entities = self.knowledge_service.search_by_name(project_id, entity_name, fuzzy=False)

            if not entities:
                return {
                    "success": False,
                    "error": f"找不到实体: {entity_name}"
                }

            entity = entities[0]

            # 查找依赖
            dependencies = self.knowledge_service.find_dependencies(project_id, entity.entity_id)

            return {
                "success": True,
                "dependencies": dependencies
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def list_modules(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """列出模块"""
        project_id = args["project_id"]

        try:
            # 获取所有文件
            entities = self.knowledge_service.db.query(
                self.knowledge_service.db.query(
                    type('obj', (), {'file_path': None})
                ).model.CodeEntityModel.file_path
            ).filter_by(project_id=project_id).distinct().all()

            files = [f[0] for f in entities]

            return {
                "success": True,
                "count": len(files),
                "files": sorted(files)
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def explain_module(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """解释模块"""
        project_id = args["project_id"]
        file_path = args["file_path"]

        try:
            # 获取文件中的所有实体
            entities = self.knowledge_service.query_entities_by_file(project_id, file_path)

            if not entities:
                return {
                    "success": False,
                    "error": f"文件不存在或未分析: {file_path}"
                }

            # 按类型分组
            classes = [e for e in entities if e.entity_type == "class"]
            functions = [e for e in entities if e.entity_type == "function"]
            methods = [e for e in entities if e.entity_type == "method"]

            # 提取模块文档
            module_doc = None
            for entity in entities:
                if entity.docstring:
                    module_doc = entity.docstring
                    break

            return {
                "success": True,
                "file_path": file_path,
                "module_doc": module_doc,
                "summary": {
                    "classes": len(classes),
                    "functions": len(functions),
                    "methods": len(methods)
                },
                "classes": [
                    {
                        "name": c.name,
                        "docstring": c.docstring[:100] if c.docstring else None,
                        "line": c.line_number
                    }
                    for c in classes
                ],
                "functions": [
                    {
                        "name": f.name,
                        "signature": f.signature,
                        "docstring": f.docstring[:100] if f.docstring else None,
                        "line": f.line_number
                    }
                    for f in functions
                ]
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def search_code_pattern(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """搜索代码模式"""
        project_id = args["project_id"]
        pattern = args["pattern"]
        target = args["target"]

        try:
            results = []

            if pattern == "inherits_from":
                # 查找所有继承关系
                relations = self.knowledge_service.query_relations(
                    project_id=project_id,
                    relation_type="inherits"
                )

                # 过滤目标基类
                for rel in relations:
                    if target in rel.metadata.get("base_class", ""):
                        source = self.knowledge_service.query_entity(project_id, rel.source_id)
                        if source:
                            results.append({
                                "name": source.name,
                                "qualified_name": source.qualified_name,
                                "file_path": source.file_path,
                                "line": source.line_number
                            })

            elif pattern == "calls_function":
                # 查找所有调用目标函数的地方
                relations = self.knowledge_service.query_relations(
                    project_id=project_id,
                    relation_type="calls"
                )

                for rel in relations:
                    if target in rel.metadata.get("function", ""):
                        source = self.knowledge_service.query_entity(project_id, rel.source_id)
                        if source:
                            results.append({
                                "caller": source.name,
                                "file_path": source.file_path,
                                "line": source.line_number
                            })

            return {
                "success": True,
                "pattern": pattern,
                "target": target,
                "count": len(results),
                "results": results
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


# ==================== 工具注册辅助函数 ====================

def register_code_analysis_tools(mcp_server, db_session):
    """
    将代码分析工具注册到MCP服务器

    用法:
        from mcp_http_server import app
        from code_mcp_tools import register_code_analysis_tools

        register_code_analysis_tools(app, db_session)
    """
    tools = MCPCodeAnalysisTools(db_session)

    # 注册到MCP服务器的工具列表
    # （具体实现取决于MCP服务器的架构）
    pass


# ==================== MCP工具列表导出 ====================

MCP_TOOLS = MCPCodeAnalysisTools.get_tools_definition()

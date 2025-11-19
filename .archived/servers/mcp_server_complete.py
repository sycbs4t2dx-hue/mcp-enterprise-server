#!/usr/bin/env python3
"""
MCP Server - 完整集成版

集成所有功能:
- 基础记忆管理 (4个工具)
- 代码知识图谱 (8个工具)
- 项目上下文管理 (12个工具)
- AI辅助功能 (7个工具)

总计: 31个MCP工具
"""

import json
import sys
import os
import logging
from typing import Any, Dict, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.mcp_core.services.memory_service import MemoryService
from src.mcp_core.code_knowledge_service import CodeKnowledgeGraphService
from src.mcp_core.project_context_service import ProjectContextManager
from src.mcp_core.code_mcp_tools import MCP_TOOLS as CODE_TOOLS
from src.mcp_core.context_mcp_tools import MCP_TOOLS as CONTEXT_TOOLS, ProjectContextTools
from src.mcp_core.ai_understanding_service import (
    AICodeUnderstandingService,
    AI_MCP_TOOLS,
    AIAssistantTools
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr)  # MCP要求错误输出到stderr
    ]
)
logger = logging.getLogger(__name__)


class CompleteMCPServer:
    """完整的MCP服务器"""

    PROTOCOL_VERSION = "2024-11-05"
    SERVER_NAME = "mcp-ai-assisted-dev"
    SERVER_VERSION = "1.5.0"

    def __init__(self):
        """初始化服务器"""
        self.db_session = None
        self.memory_service = None
        self.code_service = None
        self.context_manager = None
        self.context_tools = None
        self.ai_service = None
        self.ai_tools = None

        self._init_services()

    def _init_services(self):
        """初始化所有服务"""
        try:
            # 数据库连接
            DB_URL = os.getenv("DATABASE_URL", "mysql+pymysql://root:Wxwy.2025%40%23@localhost:3306/mcp_db?charset=utf8mb4")
            engine = create_engine(DB_URL, pool_pre_ping=True)
            SessionLocal = sessionmaker(bind=engine)
            self.db_session = SessionLocal()

            # 基础服务
            self.memory_service = MemoryService(self.db_session)
            self.code_service = CodeKnowledgeGraphService(self.db_session)
            self.context_manager = ProjectContextManager(self.db_session)
            self.context_tools = ProjectContextTools(self.context_manager)

            # AI服务（可选）
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if api_key:
                self.ai_service = AICodeUnderstandingService(api_key=api_key)
                self.ai_tools = AIAssistantTools(
                    self.ai_service,
                    self.code_service,
                    self.context_manager
                )
                logger.info("✅ AI服务已启用")
            else:
                logger.warning("⚠️  未设置ANTHROPIC_API_KEY，AI功能将不可用")

            logger.info("✅ 所有服务初始化完成")

        except Exception as e:
            logger.error(f"❌ 服务初始化失败: {e}")
            raise

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """处理JSON-RPC 2.0请求"""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")

        try:
            if method == "initialize":
                result = self._handle_initialize(params)
            elif method == "tools/list":
                result = self._handle_tools_list(params)
            elif method == "tools/call":
                result = self._handle_tools_call(params)
            else:
                return self._error_response(request_id, -32601, f"Method not found: {method}")

            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }

        except Exception as e:
            logger.error(f"请求处理失败: {e}", exc_info=True)
            return self._error_response(request_id, -32603, f"Internal error: {str(e)}")

    def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理初始化"""
        client_info = params.get("clientInfo", {})
        logger.info(f"客户端连接: {client_info.get('name', 'unknown')}")

        return {
            "protocolVersion": self.PROTOCOL_VERSION,
            "serverInfo": {
                "name": self.SERVER_NAME,
                "version": self.SERVER_VERSION
            },
            "capabilities": {
                "tools": {}
            }
        }

    def _handle_tools_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """列出所有可用工具"""
        tools = []

        # 基础记忆工具
        tools.extend([
            {
                "name": "store_memory",
                "description": "存储新的记忆到项目中",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "项目ID"},
                        "content": {"type": "string", "description": "记忆内容"},
                        "memory_level": {
                            "type": "string",
                            "enum": ["short", "mid", "long"],
                            "description": "记忆级别"
                        }
                    },
                    "required": ["project_id", "content"]
                }
            },
            {
                "name": "retrieve_memory",
                "description": "检索相关记忆",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "项目ID"},
                        "query": {"type": "string", "description": "检索查询"},
                        "top_k": {"type": "integer", "description": "返回结果数量"}
                    },
                    "required": ["project_id", "query"]
                }
            }
        ])

        # 代码知识图谱工具 (8个)
        tools.extend(CODE_TOOLS)

        # 项目上下文管理工具 (12个)
        tools.extend(CONTEXT_TOOLS)

        # AI辅助工具 (7个，如果启用)
        if self.ai_service:
            tools.extend(AI_MCP_TOOLS)

        logger.info(f"提供 {len(tools)} 个MCP工具")
        return {"tools": tools}

    def _handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具调用"""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        logger.info(f"执行工具: {tool_name}")

        try:
            # 基础记忆工具
            if tool_name == "store_memory":
                result = self._call_store_memory(arguments)
            elif tool_name == "retrieve_memory":
                result = self._call_retrieve_memory(arguments)

            # 代码知识图谱工具
            elif tool_name == "analyze_codebase":
                result = self._call_analyze_codebase(arguments)
            elif tool_name == "query_architecture":
                result = self._call_query_architecture(arguments)
            elif tool_name == "find_entity":
                result = self._call_find_entity(arguments)
            elif tool_name == "trace_function_calls":
                result = self._call_trace_function_calls(arguments)
            elif tool_name == "find_dependencies":
                result = self._call_find_dependencies(arguments)
            elif tool_name == "list_modules":
                result = self._call_list_modules(arguments)
            elif tool_name == "explain_module":
                result = self._call_explain_module(arguments)
            elif tool_name == "search_code_pattern":
                result = self._call_search_code_pattern(arguments)

            # 项目上下文管理工具
            elif tool_name == "start_dev_session":
                result = self.context_tools.start_dev_session(**arguments)
            elif tool_name == "end_dev_session":
                result = self.context_tools.end_dev_session(**arguments)
            elif tool_name == "record_design_decision":
                result = self.context_tools.record_design_decision(**arguments)
            elif tool_name == "add_project_note":
                result = self.context_tools.add_project_note(**arguments)
            elif tool_name == "create_todo":
                result = self.context_tools.create_todo(**arguments)
            elif tool_name == "update_todo_status":
                result = self.context_tools.update_todo_status(**arguments)
            elif tool_name == "get_project_context":
                result = self.context_tools.get_project_context(**arguments)
            elif tool_name == "list_todos":
                result = self.context_tools.list_todos(**arguments)
            elif tool_name == "get_next_todo":
                result = self.context_tools.get_next_todo(**arguments)
            elif tool_name == "list_design_decisions":
                result = self.context_tools.list_design_decisions(**arguments)
            elif tool_name == "list_project_notes":
                result = self.context_tools.list_project_notes(**arguments)
            elif tool_name == "get_project_statistics":
                result = self.context_tools.get_project_statistics(**arguments)

            # AI辅助工具
            elif tool_name.startswith("ai_") and self.ai_tools:
                result = self._call_ai_tool(tool_name, arguments)

            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            return {
                "content": [{
                    "type": "text",
                    "text": json.dumps(result, ensure_ascii=False, indent=2)
                }]
            }

        except Exception as e:
            logger.error(f"工具执行失败: {e}", exc_info=True)
            return {
                "content": [{
                    "type": "text",
                    "text": f"错误: {str(e)}"
                }],
                "isError": True
            }

    # ==================== 基础记忆工具 ====================

    def _call_store_memory(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """存储记忆"""
        memory = self.memory_service.store_memory(
            project_id=args["project_id"],
            content=args["content"],
            memory_level=args.get("memory_level", "mid"),
            tags=args.get("tags", []),
            metadata={}
        )
        return {
            "success": True,
            "memory_id": memory.memory_id,
            "message": "记忆存储成功"
        }

    def _call_retrieve_memory(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """检索记忆"""
        results = self.memory_service.retrieve_memory(
            project_id=args["project_id"],
            query=args["query"],
            top_k=args.get("top_k", 5)
        )
        return {
            "success": True,
            "count": len(results),
            "memories": [
                {
                    "content": m.content,
                    "memory_level": m.memory_level,
                    "created_at": m.created_at.isoformat() if m.created_at else None
                }
                for m in results
            ]
        }

    # ==================== 代码知识图谱工具 ====================

    def _call_analyze_codebase(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """分析代码库"""
        from src.mcp_core.multi_lang_analyzer import MultiLanguageAnalyzer

        project_path = args["project_path"]
        project_id = args.get("project_id", f"project_{os.path.basename(project_path)}")

        # 创建项目
        try:
            self.code_service.create_project(
                project_id=project_id,
                name=os.path.basename(project_path),
                path=project_path
            )
        except:
            pass  # 项目可能已存在

        # 分析代码
        analyzer = MultiLanguageAnalyzer(project_path)
        result = analyzer.analyze_project()

        # 存储到数据库
        self.code_service.store_analysis_result(
            project_id=project_id,
            entities=result["entities"],
            relations=result["relations"],
            stats=result["stats"]
        )

        return {
            "success": True,
            "project_id": project_id,
            "stats": result["stats"],
            "message": f"✅ 代码分析完成: {result['stats']['total_files']}个文件"
        }

    def _call_query_architecture(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """查询架构"""
        architecture = self.code_service.query_architecture(args["project_id"])
        return architecture

    def _call_find_entity(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """查找实体"""
        entities = self.code_service.search_by_name(
            project_id=args["project_id"],
            name=args["name"],
            fuzzy=args.get("fuzzy", True)
        )
        return {
            "success": True,
            "count": len(entities),
            "entities": [
                {
                    "entity_id": e.entity_id,
                    "name": e.name,
                    "type": e.entity_type,
                    "qualified_name": e.qualified_name,
                    "file_path": e.file_path,
                    "line_number": e.line_number
                }
                for e in entities
            ]
        }

    def _call_trace_function_calls(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """追踪函数调用"""
        result = self.code_service.trace_calls(
            project_id=args["project_id"],
            entity_id=args["entity_id"],
            depth=args.get("depth", 3)
        )
        return result

    def _call_find_dependencies(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """查找依赖"""
        result = self.code_service.find_dependencies(
            project_id=args["project_id"],
            entity_id=args["entity_id"]
        )
        return result

    def _call_list_modules(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """列出模块"""
        entities = self.code_service.query_entities_by_type(
            project_id=args["project_id"],
            entity_type="module"
        )
        return {
            "success": True,
            "count": len(entities),
            "modules": [{"name": e.name, "path": e.file_path} for e in entities]
        }

    def _call_explain_module(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """解释模块"""
        entities = self.code_service.query_entities_by_file(
            project_id=args["project_id"],
            file_path=args["module_path"]
        )
        return {
            "success": True,
            "module_path": args["module_path"],
            "entities_count": len(entities),
            "entities": [
                {"name": e.name, "type": e.entity_type}
                for e in entities[:20]
            ]
        }

    def _call_search_code_pattern(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """搜索代码模式"""
        # 简化实现
        return {
            "success": True,
            "message": "代码模式搜索功能待完善"
        }

    # ==================== AI辅助工具 ====================

    def _call_ai_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """调用AI工具"""
        if not self.ai_tools:
            return {"success": False, "error": "AI服务未启用"}

        if tool_name == "ai_understand_function":
            return self.ai_tools.ai_understand_function(**args)
        elif tool_name == "ai_understand_module":
            return self.ai_tools.ai_understand_module(**args)
        elif tool_name == "ai_explain_architecture":
            return self.ai_tools.ai_explain_architecture(**args)
        elif tool_name == "ai_generate_resumption_briefing":
            return self.ai_tools.ai_generate_resumption_briefing(**args)
        elif tool_name == "ai_generate_todos_from_goal":
            return self.ai_tools.ai_generate_todos_from_goal(**args)
        elif tool_name == "ai_decompose_task":
            return self.ai_tools.ai_decompose_task(**args)
        elif tool_name == "ai_analyze_code_quality":
            return self.ai_tools.ai_analyze_code_quality(**args)
        else:
            raise ValueError(f"Unknown AI tool: {tool_name}")

    def _error_response(self, request_id: Any, code: int, message: str) -> Dict[str, Any]:
        """构造错误响应"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": message
            }
        }

    def run(self):
        """运行服务器"""
        logger.info(f"=== {self.SERVER_NAME} v{self.SERVER_VERSION} ===")
        logger.info(f"MCP协议版本: {self.PROTOCOL_VERSION}")
        logger.info("等待客户端连接...")

        for line in sys.stdin:
            try:
                request = json.loads(line.strip())
                response = self.handle_request(request)
                print(json.dumps(response), flush=True)

            except json.JSONDecodeError as e:
                logger.error(f"JSON解析失败: {e}")
                error_response = self._error_response(None, -32700, "Parse error")
                print(json.dumps(error_response), flush=True)

            except Exception as e:
                logger.error(f"未处理异常: {e}", exc_info=True)


def main():
    """主入口"""
    server = CompleteMCPServer()
    server.run()


if __name__ == "__main__":
    main()

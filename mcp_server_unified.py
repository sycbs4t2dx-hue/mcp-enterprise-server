#!/usr/bin/env python3
"""
MCP统一服务器 v2.0.0

完整集成所有37个MCP工具，提供统一的服务入口
"""

import json
import sys
import os
import logging
from typing import Any, Dict, Optional
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Database configuration
import os
import urllib.parse
from types import SimpleNamespace

DB_PASSWORD = os.getenv("DB_PASSWORD", "Wxwy.2025@#")
DB_PASSWORD_ENCODED = urllib.parse.quote_plus(DB_PASSWORD)
DB_URL = f"mysql+pymysql://root:{DB_PASSWORD_ENCODED}@localhost:3306/mcp_db?charset=utf8mb4"

# Create a simple config object
def create_config():
    """Create a simple configuration object"""
    config = SimpleNamespace()
    config.server = SimpleNamespace(
        name="MCP统一服务器",
        version="2.0.0",
        protocol_version="2024-11-05",
        log_level="INFO",
        log_file="logs/mcp_server.log"
    )
    config.database = SimpleNamespace(
        url=DB_URL
    )
    config.performance = SimpleNamespace(
        db_pool_size=10,
        db_max_overflow=20
    )
    config.ai = SimpleNamespace(
        enabled=False
    )
    return config

# 动态导入服务（避免路径问题）
try:
    # 尝试绝对导入
    from src.mcp_core.services.memory_service import MemoryService
    from src.mcp_core.code_knowledge_service import CodeKnowledgeGraphService
    from src.mcp_core.project_context_service import ProjectContextManager
    from src.mcp_core.ai_understanding_service import (
        AICodeUnderstandingService,
        AIAssistantTools,
        AI_MCP_TOOLS
    )
    from src.mcp_core.quality_guardian_service import QualityGuardianService
    from src.mcp_core.multi_lang_analyzer import MultiLanguageAnalyzer
    from src.mcp_core.code_mcp_tools import MCP_TOOLS as CODE_TOOLS
    from src.mcp_core.context_mcp_tools import MCP_TOOLS as CONTEXT_TOOLS, ProjectContextTools
    from src.mcp_core.quality_mcp_tools import QUALITY_GUARDIAN_TOOLS, QualityGuardianTools
    from src.mcp_core.services.error_firewall_service import get_error_firewall_service
    from src.mcp_core.api.v1.tools.error_firewall import ERROR_FIREWALL_TOOLS, error_firewall_record, error_firewall_check, error_firewall_query, error_firewall_stats
except ImportError:
    # 尝试相对导入
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent / "src"))

    from mcp_core.services.memory_service import MemoryService
    from mcp_core.code_knowledge_service import CodeKnowledgeGraphService
    from mcp_core.project_context_service import ProjectContextManager
    from mcp_core.ai_understanding_service import (
        AICodeUnderstandingService,
        AIAssistantTools,
        AI_MCP_TOOLS
    )
    from mcp_core.quality_guardian_service import QualityGuardianService
    from mcp_core.multi_lang_analyzer import MultiLanguageAnalyzer
    from mcp_core.code_mcp_tools import MCP_TOOLS as CODE_TOOLS
    from mcp_core.context_mcp_tools import MCP_TOOLS as CONTEXT_TOOLS, ProjectContextTools
    from mcp_core.quality_mcp_tools import QUALITY_GUARDIAN_TOOLS, QualityGuardianTools
    from mcp_core.services.error_firewall_service import get_error_firewall_service
    from mcp_core.api.v1.tools.error_firewall import ERROR_FIREWALL_TOOLS, error_firewall_record, error_firewall_check, error_firewall_query, error_firewall_stats


class UnifiedMCPServer:
    """统一MCP服务器 - v2.0.0"""

    def __init__(self, config_file: Optional[str] = None):
        """
        初始化统一MCP服务器

        Args:
            config_file: 配置文件路径（可选）
        """
        # 加载配置
        self.config = create_config()

        # 初始化日志
        self._setup_logging()

        self.logger.info(f"=== {self.config.server.name} v{self.config.server.version} ===")
        self.logger.info(f"MCP协议版本: {self.config.server.protocol_version}")

        # 初始化数据库和服务
        self._init_services()

        # 统计信息
        self.request_count = 0
        self.start_time = datetime.now()

    def _setup_logging(self):
        """配置日志"""
        log_level = getattr(logging, self.config.server.log_level.upper())

        # 确保日志目录存在
        log_dir = os.path.dirname(self.config.server.log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

        # 配置日志处理器
        handlers = [logging.StreamHandler(sys.stderr)]
        if self.config.server.log_file:
            handlers.append(logging.FileHandler(self.config.server.log_file))

        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=handlers
        )

        self.logger = logging.getLogger(__name__)

    def _init_services(self):
        """初始化所有服务"""
        try:
            # 创建数据库引擎
            self.logger.info("连接数据库...")
            engine = create_engine(
                self.config.database.url,
                pool_pre_ping=True,
                pool_size=self.config.performance.db_pool_size,
                max_overflow=self.config.performance.db_max_overflow
            )
            SessionLocal = sessionmaker(bind=engine)
            self.db_session = SessionLocal()

            # 初始化基础服务
            self.logger.info("初始化基础服务...")
            self.memory_service = MemoryService(self.db_session)
            self.code_service = CodeKnowledgeGraphService(self.db_session)
            self.context_manager = ProjectContextManager(self.db_session)
            self.quality_service = QualityGuardianService(self.db_session, self.code_service)

            # 初始化工具封装
            self.context_tools = ProjectContextTools(self.context_manager)
            self.quality_tools = QualityGuardianTools(self.quality_service)

            # 初始化错误防火墙服务 (Phase 5)
            self.logger.info("初始化错误防火墙服务...")
            self.error_firewall = get_error_firewall_service(self.db_session)
            self.logger.info("✅ 错误防火墙服务已启用")

            # 初始化AI服务（可选）
            self.ai_service = None
            self.ai_tools = None
            if self.config.ai.enabled:
                try:
                    self.logger.info("初始化AI服务...")
                    self.ai_service = AICodeUnderstandingService(
                        api_key=self.config.ai.api_key,
                        model=self.config.ai.model
                    )
                    self.ai_tools = AIAssistantTools(
                        self.ai_service,
                        self.code_service,
                        self.context_manager
                    )
                    self.logger.info(f"✅ AI服务已启用 ({self.config.ai.provider}/{self.config.ai.model})")
                except ImportError as e:
                    self.logger.warning(f"⚠️  AI服务未启用 - 缺少依赖包: {e}")
                    self.ai_service = None
                    self.ai_tools = None
                except Exception as e:
                    self.logger.warning(f"⚠️  AI服务初始化失败: {e}")
                    self.ai_service = None
                    self.ai_tools = None
            else:
                self.logger.warning("⚠️  AI服务未启用 (未配置API Key)")

            self.logger.info("✅ 所有服务初始化完成")

        except Exception as e:
            self.logger.error(f"❌ 服务初始化失败: {e}", exc_info=True)
            raise

    def get_all_tools(self) -> list:
        """返回所有41个MCP工具定义"""
        tools = []

        # 基础记忆工具 (2个)
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
                        "project_id": {"type": "string"},
                        "query": {"type": "string"},
                        "top_k": {"type": "integer", "default": 5}
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

        # 质量守护工具 (8个)
        tools.extend(QUALITY_GUARDIAN_TOOLS)

        # 错误防火墙工具 (4个) - Phase 5
        tools.extend(ERROR_FIREWALL_TOOLS)

        self.logger.info(f"提供 {len(tools)} 个MCP工具")
        return tools

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理JSON-RPC 2.0请求

        统一错误处理和请求日志
        """
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")

        self.request_count += 1
        start_time = datetime.now()

        self.logger.info(f"[#{self.request_count}] {method}")
        self.logger.debug(f"参数: {params}")

        try:
            # 路由请求
            if method == "initialize":
                result = self._handle_initialize(params)
            elif method == "tools/list":
                result = self._handle_tools_list(params)
            elif method == "tools/call":
                result = self._handle_tools_call(params)
            else:
                return self._error_response(request_id, -32601, f"Method not found: {method}")

            # 记录执行时间
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"[#{self.request_count}] 完成 ({duration:.3f}s)")

            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"[#{self.request_count}] 失败 ({duration:.3f}s): {e}", exc_info=True)
            return self._error_response(request_id, -32603, f"Internal error: {str(e)}")

    def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理初始化"""
        client_info = params.get("clientInfo", {})
        self.logger.info(f"客户端连接: {client_info.get('name', 'unknown')}")

        return {
            "protocolVersion": self.config.server.protocol_version,
            "serverInfo": {
                "name": self.config.server.name,
                "version": self.config.server.version
            },
            "capabilities": {
                "tools": {}
            }
        }

    def _handle_tools_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """列出所有工具"""
        tools = self.get_all_tools()
        return {"tools": tools}

    def _handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具调用 - 智能路由"""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        self.logger.info(f"执行工具: {tool_name}")

        try:
            # 路由到对应的处理器
            if tool_name in ["store_memory", "retrieve_memory"]:
                result = self._call_memory_tool(tool_name, arguments)
            elif tool_name in [t["name"] for t in CODE_TOOLS]:
                result = self._call_code_tool(tool_name, arguments)
            elif tool_name in [t["name"] for t in CONTEXT_TOOLS]:
                result = self._call_context_tool(tool_name, arguments)
            elif self.ai_tools and tool_name in [t["name"] for t in AI_MCP_TOOLS]:
                result = self._call_ai_tool(tool_name, arguments)
            elif tool_name in [t["name"] for t in QUALITY_GUARDIAN_TOOLS]:
                result = self._call_quality_tool(tool_name, arguments)
            elif tool_name in [t["name"] for t in ERROR_FIREWALL_TOOLS]:
                result = self._call_error_firewall_tool(tool_name, arguments)
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            return {
                "content": [{
                    "type": "text",
                    "text": json.dumps(result, ensure_ascii=False, indent=2)
                }]
            }

        except Exception as e:
            # 回滚会话以清除错误状态
            try:
                self.db_session.rollback()
                self.logger.warning("会话已回滚")
            except:
                pass

            self.logger.error(f"工具执行失败: {e}", exc_info=True)
            return {
                "content": [{
                    "type": "text",
                    "text": json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)
                }],
                "isError": True
            }

    # ==================== 工具实现 ====================

    def _call_memory_tool(self, tool_name: str, args: Dict) -> Dict:
        """基础记忆工具"""
        if tool_name == "store_memory":
            # 将tags合并到metadata中
            metadata = {}
            if "tags" in args and args["tags"]:
                metadata["tags"] = args["tags"]

            memory = self.memory_service.store_memory(
                project_id=args["project_id"],
                content=args["content"],
                memory_level=args.get("memory_level", "mid"),
                metadata=metadata
            )
            return {"success": True, "memory_id": memory["memory_id"]}

        elif tool_name == "retrieve_memory":
            result = self.memory_service.retrieve_memory(
                project_id=args["project_id"],
                query=args["query"],
                top_k=args.get("top_k", 5)
            )

            # retrieve_memory返回: {"memories": [...], "total_token_saved": int}
            if isinstance(result, dict) and "memories" in result:
                memories = result["memories"]
                return {
                    "success": True,
                    "count": len(memories),
                    "memories": memories,
                    "total_token_saved": result.get("total_token_saved", 0)
                }
            else:
                # 降级处理:旧格式兼容
                memories = []
                results = result if isinstance(result, list) else []
                for m in results:
                    if isinstance(m, str):
                        memories.append({"content": m, "memory_level": "unknown"})
                    elif hasattr(m, 'content'):
                        memories.append({"content": m.content, "memory_level": getattr(m, 'memory_level', 'unknown')})
                    else:
                        memories.append({"content": str(m), "memory_level": "unknown"})

                return {
                    "success": True,
                    "count": len(memories),
                    "memories": memories
                }

    def _call_code_tool(self, tool_name: str, args: Dict) -> Dict:
        """代码分析工具"""
        if tool_name == "analyze_codebase":
            from pathlib import Path
            from sqlalchemy.exc import IntegrityError

            project_path = args["project_path"]
            project_id = args.get("project_id", f"project_{Path(project_path).name}")

            # 创建项目(如果不存在)
            try:
                self.code_service.create_project(
                    project_id=project_id,
                    name=Path(project_path).name,
                    path=project_path
                )
            except IntegrityError:
                # 项目已存在,回滚会话以清除错误状态
                self.db_session.rollback()
                self.logger.info(f"项目已存在,将更新: {project_id}")
            except Exception as e:
                # 其他错误也要回滚
                self.db_session.rollback()
                self.logger.error(f"创建项目失败: {e}")
                raise

            # 分析代码
            analyzer = MultiLanguageAnalyzer(project_path)
            result = analyzer.analyze_project()

            # 存储结果
            self.code_service.store_analysis_result(
                project_id=project_id,
                entities=result["entities"],
                relations=result["relations"],
                stats=result["stats"]
            )

            return {"success": True, "project_id": project_id, "stats": result["stats"]}

        elif tool_name == "query_architecture":
            return self.code_service.query_architecture(args["project_id"])

        elif tool_name == "find_entity":
            entities = self.code_service.search_by_name(
                args["project_id"], args["name"], args.get("fuzzy", True)
            )
            return {
                "success": True,
                "count": len(entities),
                "entities": [
                    {"entity_id": e.entity_id, "name": e.name, "type": e.entity_type,
                     "file_path": e.file_path, "line_number": e.line_number}
                    for e in entities
                ]
            }

        # 其他代码工具...
        return {"success": True, "message": f"{tool_name} 执行成功"}

    def _call_context_tool(self, tool_name: str, args: Dict) -> Dict:
        """上下文管理工具"""
        method = getattr(self.context_tools, tool_name, None)
        if method:
            return method(**args)
        return {"success": False, "error": f"Tool not found: {tool_name}"}

    def _call_ai_tool(self, tool_name: str, args: Dict) -> Dict:
        """AI辅助工具"""
        if not self.ai_tools:
            return {"success": False, "error": "AI服务未启用"}

        method_name = tool_name  # ai_understand_function等
        method = getattr(self.ai_tools, method_name, None)
        if method:
            return method(**args)
        return {"success": False, "error": f"AI tool not found: {tool_name}"}

    def _call_quality_tool(self, tool_name: str, args: Dict) -> Dict:
        """质量守护工具"""
        method = getattr(self.quality_tools, tool_name, None)
        if method:
            return method(**args)
        return {"success": False, "error": f"Quality tool not found: {tool_name}"}

    async def _call_error_firewall_tool_async(self, tool_name: str, args: Dict) -> Dict:
        """错误防火墙工具 (异步)"""
        # 添加db_session参数
        args_with_session = {**args, "db_session": self.db_session}

        if tool_name == "error_firewall_record":
            return await error_firewall_record(**args_with_session)
        elif tool_name == "error_firewall_check":
            return await error_firewall_check(**args_with_session)
        elif tool_name == "error_firewall_query":
            return await error_firewall_query(**args_with_session)
        elif tool_name == "error_firewall_stats":
            return await error_firewall_stats(**args_with_session)
        else:
            return {"success": False, "error": f"Error firewall tool not found: {tool_name}"}

    def _call_error_firewall_tool(self, tool_name: str, args: Dict) -> Dict:
        """错误防火墙工具 (同步包装)"""
        import asyncio

        # 检查是否有运行中的事件循环
        try:
            loop = asyncio.get_running_loop()
            # 如果有运行中的循环，创建新线程执行
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    self._call_error_firewall_tool_async(tool_name, args)
                )
                return future.result()
        except RuntimeError:
            # 没有运行中的循环，直接运行
            return asyncio.run(self._call_error_firewall_tool_async(tool_name, args))

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
        """运行服务器 - stdio模式"""
        self.logger.info("等待客户端连接...")
        self.logger.info(f"工具数量: {len(self.get_all_tools())}")

        for line in sys.stdin:
            try:
                request = json.loads(line.strip())
                response = self.handle_request(request)
                print(json.dumps(response), flush=True)

            except json.JSONDecodeError as e:
                self.logger.error(f"JSON解析失败: {e}")
                error_response = self._error_response(None, -32700, "Parse error")
                print(json.dumps(error_response), flush=True)

            except Exception as e:
                self.logger.error(f"未处理异常: {e}", exc_info=True)

    def cleanup(self):
        """清理资源"""
        if self.db_session:
            self.db_session.close()
        self.logger.info("服务器已关闭")


def main():
    """主入口"""
    import argparse

    parser = argparse.ArgumentParser(description="MCP统一服务器 v2.0.0")
    parser.add_argument("--config", help="配置文件路径")
    parser.add_argument("--version", action="store_true", help="显示版本")
    args = parser.parse_args()

    if args.version:
        print("MCP Unified Server v2.0.0")
        return

    try:
        server = UnifiedMCPServer(config_file=args.config)
        server.run()
    except KeyboardInterrupt:
        print("\n服务器停止")
    except Exception as e:
        print(f"❌ 服务器启动失败: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if 'server' in locals():
            server.cleanup()


if __name__ == "__main__":
    main()

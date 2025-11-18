"""
MCP Core - 记忆控制机制

高性能、生产级的MCP实现
"""

__version__ = "1.0.0"
__author__ = "MCP Development Team"

from .common.config import load_config, get_settings

__all__ = ["load_config", "get_settings", "__version__"]

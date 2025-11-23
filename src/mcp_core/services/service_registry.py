"""
服务注册表 - 统一管理所有服务的初始化
"""

from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class ServiceRegistry:
    """统一的服务注册表"""

    _instance = None
    _services: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._services = {}
        return cls._instance

    def register(self, name: str, service: Any):
        """注册服务"""
        self._services[name] = service
        logger.info(f"Service registered: {name}")

    def get(self, name: str) -> Optional[Any]:
        """获取服务"""
        return self._services.get(name)

    def get_all(self) -> Dict[str, Any]:
        """获取所有服务"""
        return self._services.copy()

    def initialize_all(self, config: Dict[str, Any]):
        """初始化所有服务"""
        logger.info("Initializing all services...")

        # Import all services here to avoid circular imports
        try:
            from .memory_service import MemoryService
            self.register('memory', MemoryService())
        except ImportError as e:
            logger.warning(f"Memory service not available: {e}")

        try:
            from .vector_db import get_vector_db
            self.register('vector_db', get_vector_db())
        except ImportError as e:
            logger.warning(f"Vector DB not available: {e}")

        try:
            from .embedding_service import get_embedding_service
            self.register('embedding', get_embedding_service())
        except ImportError as e:
            logger.warning(f"Embedding service not available: {e}")

        try:
            from .error_firewall_service import get_error_firewall_service
            self.register('error_firewall', get_error_firewall_service())
        except ImportError as e:
            logger.warning(f"Error firewall not available: {e}")

        # WebSocket service (lazy loaded)
        self._services['websocket'] = None  # Will be loaded on demand

        logger.info(f"Services initialized: {len(self._services)} registered")

# Global instance
_registry = ServiceRegistry()

def get_service_registry() -> ServiceRegistry:
    """获取服务注册表单例"""
    return _registry

def get_service(name: str) -> Optional[Any]:
    """便捷函数：获取服务"""
    return _registry.get(name)

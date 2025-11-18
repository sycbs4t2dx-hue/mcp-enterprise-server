"""
MCP项目 - FastAPI主应用

提供REST API接口用于:
- 记忆管理
- Token优化
- 幻觉检测
- 项目管理
- 用户认证
"""

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .common.config import get_settings
from .common.logger import get_logger
from .models.database import Base
from .api.dependencies.database import engine, SessionLocal

# 导入API路由
from .api.v1 import auth, memory, project, token, validate

logger = get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动
    logger.info("Starting MCP application...")

    # 初始化数据库表
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized")

    # 初始化服务
    from .services import get_redis_client, get_vector_db_client, get_embedding_service

    try:
        redis_client = get_redis_client()
        logger.info(f"Redis connected: {redis_client.client.ping()}")
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}")

    try:
        vector_db = get_vector_db_client()
        logger.info(f"Milvus connected: {vector_db.client is not None}")
    except Exception as e:
        logger.warning(f"Milvus connection failed: {e}")

    embedding_service = get_embedding_service()
    logger.info(f"Embedding service initialized: {embedding_service.model_name}")

    logger.info("MCP application started successfully")

    yield

    # 关闭
    logger.info("Shutting down MCP application...")

    # 清理资源
    try:
        redis_client.client.close()
        logger.info("Redis connection closed")
    except:
        pass

    logger.info("MCP application shutdown complete")


# 创建FastAPI应用
app = FastAPI(
    title="MCP - Memory Control Protocol",
    description="智能记忆管理与幻觉抑制系统",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 全局异常处理
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """处理请求验证错误"""
    logger.warning(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": "Validation error",
            "details": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """处理通用异常"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": "Internal server error",
            "message": str(exc) if settings.app.debug else "An error occurred",
        },
    )


# 健康检查
@app.get("/health", tags=["system"])
async def health_check() -> dict[str, Any]:
    """健康检查端点"""
    from .services import get_redis_client, get_vector_db_client

    health_status = {
        "status": "healthy",
        "version": "1.0.0",
        "services": {}
    }

    # 检查Redis
    try:
        redis_client = get_redis_client()
        redis_client.client.ping()
        health_status["services"]["redis"] = "healthy"
    except Exception as e:
        health_status["services"]["redis"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"

    # 检查Milvus
    try:
        vector_db = get_vector_db_client()
        if vector_db.client:
            health_status["services"]["milvus"] = "healthy"
        else:
            health_status["services"]["milvus"] = "not_initialized"
    except Exception as e:
        health_status["services"]["milvus"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"

    # 检查数据库
    try:
        with SessionLocal() as db:
            db.execute("SELECT 1")
        health_status["services"]["database"] = "healthy"
    except Exception as e:
        health_status["services"]["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "unhealthy"

    return health_status


@app.get("/", tags=["system"])
async def root() -> dict[str, str]:
    """根路径"""
    return {
        "message": "Welcome to MCP - Memory Control Protocol",
        "version": "1.0.0",
        "docs": "/docs",
    }


# 注册API路由
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(memory.router, prefix="/api/v1/memory", tags=["memory"])
app.include_router(token.router, prefix="/api/v1/token", tags=["token"])
app.include_router(validate.router, prefix="/api/v1/validate", tags=["validate"])
app.include_router(project.router, prefix="/api/v1/project", tags=["project"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.mcp_core.main:app",
        host=settings.api.host,
        port=settings.api.port,
        reload=settings.app.debug,
        log_level="info",
    )

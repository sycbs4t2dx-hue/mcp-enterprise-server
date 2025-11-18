"""
记忆管理API路由
"""

from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ...common.logger import get_logger
from ...models.tables import User
from ...services import MemoryService
from ..dependencies import check_permission, get_db

logger = get_logger(__name__)
router = APIRouter()


class StoreMemoryRequest(BaseModel):
    """存储记忆请求"""

    project_id: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1, max_length=10000)
    memory_level: str = Field(default="mid", pattern="^(short|mid|long)$")
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    metadata: Optional[dict] = None


class StoreMemoryResponse(BaseModel):
    """存储记忆响应"""

    success: bool
    memory_id: str
    message: str


class RetrieveMemoryRequest(BaseModel):
    """检索记忆请求"""

    project_id: str
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=50)
    memory_levels: Optional[List[str]] = None


class MemoryItem(BaseModel):
    """记忆项"""

    memory_id: str
    content: str
    relevance_score: float
    memory_level: str
    token_count: int


class RetrieveMemoryResponse(BaseModel):
    """检索记忆响应"""

    success: bool
    memories: List[MemoryItem]
    total_count: int
    total_token_saved: int


class UpdateMemoryRequest(BaseModel):
    """更新记忆请求"""

    content: Optional[str] = None
    importance: Optional[float] = Field(None, ge=0.0, le=1.0)
    metadata: Optional[dict] = None


class DeleteMemoryResponse(BaseModel):
    """删除记忆响应"""

    success: bool
    message: str


@router.post("/store", response_model=StoreMemoryResponse)
async def store_memory(
    request: StoreMemoryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("memory.write")),
) -> Any:
    """
    存储记忆

    权限: memory.write
    """
    try:
        memory_service = MemoryService(db)

        result = memory_service.store_memory(
            project_id=request.project_id,
            content=request.content,
            memory_level=request.memory_level,
            importance=request.importance,
            metadata=request.metadata or {},
        )

        logger.info(
            f"Memory stored by {current_user.username}: "
            f"{result['memory_id']} (project: {request.project_id})"
        )

        return StoreMemoryResponse(
            success=True,
            memory_id=result["memory_id"],
            message="Memory stored successfully",
        )

    except Exception as e:
        logger.error(f"Failed to store memory: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store memory: {str(e)}",
        )


@router.post("/retrieve", response_model=RetrieveMemoryResponse)
async def retrieve_memory(
    request: RetrieveMemoryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("memory.read")),
) -> Any:
    """
    检索记忆

    权限: memory.read
    """
    try:
        memory_service = MemoryService(db)

        result = memory_service.retrieve_memory(
            project_id=request.project_id,
            query=request.query,
            top_k=request.top_k,
            memory_levels=request.memory_levels,
        )

        memories = [
            MemoryItem(
                memory_id=mem["memory_id"],
                content=mem["content"],
                relevance_score=mem["relevance_score"],
                memory_level=mem.get("memory_level", "mid"),
                token_count=mem.get("token_count", 0),
            )
            for mem in result["memories"]
        ]

        logger.info(
            f"Memory retrieved by {current_user.username}: "
            f"{len(memories)} items (project: {request.project_id})"
        )

        return RetrieveMemoryResponse(
            success=True,
            memories=memories,
            total_count=result["total_count"],
            total_token_saved=result.get("total_token_saved", 0),
        )

    except Exception as e:
        logger.error(f"Failed to retrieve memory: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve memory: {str(e)}",
        )


@router.put("/{memory_id}", response_model=dict)
async def update_memory(
    memory_id: str,
    request: UpdateMemoryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("memory.write")),
) -> Any:
    """
    更新记忆

    权限: memory.write
    """
    try:
        memory_service = MemoryService(db)

        result = memory_service.update_memory(
            memory_id=memory_id,
            content=request.content,
            importance=request.importance,
            metadata=request.metadata,
        )

        logger.info(f"Memory updated by {current_user.username}: {memory_id}")

        return {
            "success": True,
            "memory_id": memory_id,
            "message": "Memory updated successfully",
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to update memory: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update memory: {str(e)}",
        )


@router.delete("/{memory_id}", response_model=DeleteMemoryResponse)
async def delete_memory(
    memory_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("memory.delete")),
) -> Any:
    """
    删除记忆

    权限: memory.delete
    """
    try:
        memory_service = MemoryService(db)

        memory_service.delete_memory(memory_id)

        logger.info(f"Memory deleted by {current_user.username}: {memory_id}")

        return DeleteMemoryResponse(
            success=True,
            message="Memory deleted successfully",
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to delete memory: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete memory: {str(e)}",
        )


@router.get("/stats/{project_id}")
async def get_memory_stats(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("memory.read")),
) -> dict[str, Any]:
    """
    获取项目记忆统计

    权限: memory.read
    """
    try:
        memory_service = MemoryService(db)

        stats = memory_service.get_memory_stats(project_id)

        logger.info(
            f"Memory stats retrieved by {current_user.username} for project: {project_id}"
        )

        return {
            "success": True,
            "project_id": project_id,
            "stats": stats,
        }

    except Exception as e:
        logger.error(f"Failed to get memory stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get memory stats: {str(e)}",
        )

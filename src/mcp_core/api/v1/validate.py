"""
幻觉检测API路由
"""

from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ...common.logger import get_logger
from ...models.tables import User
from ...services import MemoryService, create_hallucination_service
from ..dependencies import check_permission, get_db

logger = get_logger(__name__)
router = APIRouter()


class ValidateRequest(BaseModel):
    """验证请求"""

    project_id: str
    output: str = Field(..., min_length=1)
    context: Optional[dict] = None
    threshold: Optional[float] = Field(None, ge=0.0, le=1.0)


class ValidateResponse(BaseModel):
    """验证响应"""

    success: bool
    is_hallucination: bool
    confidence: float
    threshold_used: float
    reason: str
    matched_memories: int


class BatchValidateRequest(BaseModel):
    """批量验证请求"""

    project_id: str
    outputs: List[str] = Field(..., min_items=1, max_items=50)
    context: Optional[dict] = None


class BatchValidateItem(BaseModel):
    """批量验证项"""

    output: str
    is_hallucination: bool
    confidence: float
    threshold_used: float


class BatchValidateResponse(BaseModel):
    """批量验证响应"""

    success: bool
    results: List[BatchValidateItem]
    total_count: int
    hallucination_count: int
    hallucination_rate: float


@router.post("/detect", response_model=ValidateResponse)
async def detect_hallucination(
    request: ValidateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("memory.read")),
) -> Any:
    """
    检测幻觉

    权限: memory.read
    """
    try:
        memory_service = MemoryService(db)
        hallucination_service = create_hallucination_service(memory_service)

        result = hallucination_service.detect_hallucination(
            project_id=request.project_id,
            output=request.output,
            context=request.context,
            threshold=request.threshold,
        )

        logger.info(
            f"Hallucination detection by {current_user.username}: "
            f"project={request.project_id}, "
            f"is_hallucination={result['is_hallucination']}, "
            f"confidence={result['confidence']:.3f}"
        )

        return ValidateResponse(
            success=True,
            is_hallucination=result["is_hallucination"],
            confidence=result["confidence"],
            threshold_used=result["threshold_used"],
            reason=result["reason"],
            matched_memories=len(result.get("matched_memories", [])),
        )

    except Exception as e:
        logger.error(f"Failed to detect hallucination: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to detect hallucination: {str(e)}",
        )


@router.post("/detect/batch", response_model=BatchValidateResponse)
async def batch_detect(
    request: BatchValidateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("memory.read")),
) -> Any:
    """
    批量检测幻觉

    权限: memory.read
    """
    try:
        memory_service = MemoryService(db)
        hallucination_service = create_hallucination_service(memory_service)

        results_raw = hallucination_service.batch_detect(
            project_id=request.project_id,
            outputs=request.outputs,
            context=request.context,
        )

        results = [
            BatchValidateItem(
                output=request.outputs[i],
                is_hallucination=r["is_hallucination"],
                confidence=r["confidence"],
                threshold_used=r["threshold_used"],
            )
            for i, r in enumerate(results_raw)
        ]

        hallucination_count = sum(1 for r in results if r.is_hallucination)
        hallucination_rate = hallucination_count / len(results) if results else 0.0

        logger.info(
            f"Batch hallucination detection by {current_user.username}: "
            f"{len(results)} items, {hallucination_count} hallucinations "
            f"({hallucination_rate:.1%})"
        )

        return BatchValidateResponse(
            success=True,
            results=results,
            total_count=len(results),
            hallucination_count=hallucination_count,
            hallucination_rate=hallucination_rate,
        )

    except Exception as e:
        logger.error(f"Failed to batch detect hallucination: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to batch detect hallucination: {str(e)}",
        )


@router.get("/stats/{project_id}")
async def get_hallucination_stats(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("memory.read")),
) -> dict[str, Any]:
    """
    获取幻觉统计

    权限: memory.read
    """
    try:
        memory_service = MemoryService(db)
        hallucination_service = create_hallucination_service(memory_service)

        stats = hallucination_service.get_hallucination_stats(project_id)

        logger.info(
            f"Hallucination stats retrieved by {current_user.username} "
            f"for project: {project_id}"
        )

        return {
            "success": True,
            "project_id": project_id,
            "stats": stats,
        }

    except Exception as e:
        logger.error(f"Failed to get hallucination stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get hallucination stats: {str(e)}",
        )

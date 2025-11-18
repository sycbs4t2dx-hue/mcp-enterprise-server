"""
Token优化API路由
"""

from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ...common.logger import get_logger
from ...models.tables import User
from ...services import get_token_service
from ..dependencies import check_permission

logger = get_logger(__name__)
router = APIRouter()


class CompressRequest(BaseModel):
    """压缩请求"""

    content: str = Field(..., min_length=1)
    content_type: str = Field(default="auto", pattern="^(code|text|auto)$")
    target_ratio: float = Field(default=0.5, ge=0.1, le=0.9)


class CompressResponse(BaseModel):
    """压缩响应"""

    success: bool
    compressed_content: str
    original_tokens: int
    compressed_tokens: int
    compression_rate: float
    tokens_saved: int


class BatchCompressRequest(BaseModel):
    """批量压缩请求"""

    items: List[CompressRequest] = Field(..., min_items=1, max_items=100)


class BatchCompressResponse(BaseModel):
    """批量压缩响应"""

    success: bool
    results: List[CompressResponse]
    total_original_tokens: int
    total_compressed_tokens: int
    total_tokens_saved: int


class TokenStatsResponse(BaseModel):
    """Token统计响应"""

    success: bool
    total_processed: int
    total_saved: int
    average_compression_rate: float


@router.post("/compress", response_model=CompressResponse)
async def compress_content(
    request: CompressRequest,
    current_user: User = Depends(check_permission("memory.read")),
) -> Any:
    """
    压缩内容

    权限: memory.read
    """
    try:
        token_service = get_token_service()

        result = token_service.compress_content(
            content=request.content,
            content_type=request.content_type,
            target_ratio=request.target_ratio,
        )

        logger.info(
            f"Content compressed by {current_user.username}: "
            f"{result['original_tokens']} -> {result['compressed_tokens']} tokens "
            f"({result['compression_rate']:.1%} compression)"
        )

        return CompressResponse(
            success=True,
            compressed_content=result["compressed_content"],
            original_tokens=result["original_tokens"],
            compressed_tokens=result["compressed_tokens"],
            compression_rate=result["compression_rate"],
            tokens_saved=result["tokens_saved"],
        )

    except Exception as e:
        logger.error(f"Failed to compress content: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compress content: {str(e)}",
        )


@router.post("/compress/batch", response_model=BatchCompressResponse)
async def batch_compress(
    request: BatchCompressRequest,
    current_user: User = Depends(check_permission("memory.read")),
) -> Any:
    """
    批量压缩

    权限: memory.read
    """
    try:
        token_service = get_token_service()

        results = []
        total_original = 0
        total_compressed = 0

        for item in request.items:
            result = token_service.compress_content(
                content=item.content,
                content_type=item.content_type,
                target_ratio=item.target_ratio,
            )

            results.append(
                CompressResponse(
                    success=True,
                    compressed_content=result["compressed_content"],
                    original_tokens=result["original_tokens"],
                    compressed_tokens=result["compressed_tokens"],
                    compression_rate=result["compression_rate"],
                    tokens_saved=result["tokens_saved"],
                )
            )

            total_original += result["original_tokens"]
            total_compressed += result["compressed_tokens"]

        logger.info(
            f"Batch compression by {current_user.username}: "
            f"{len(results)} items, {total_original} -> {total_compressed} tokens"
        )

        return BatchCompressResponse(
            success=True,
            results=results,
            total_original_tokens=total_original,
            total_compressed_tokens=total_compressed,
            total_tokens_saved=total_original - total_compressed,
        )

    except Exception as e:
        logger.error(f"Failed to batch compress: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to batch compress: {str(e)}",
        )


@router.get("/stats", response_model=TokenStatsResponse)
async def get_token_stats(
    current_user: User = Depends(check_permission("memory.read")),
) -> Any:
    """
    获取Token统计

    权限: memory.read
    """
    try:
        token_service = get_token_service()

        stats = token_service.get_stats()

        logger.info(f"Token stats retrieved by {current_user.username}")

        return TokenStatsResponse(
            success=True,
            total_processed=stats["total_processed"],
            total_saved=stats["total_saved"],
            average_compression_rate=stats["average_compression_rate"],
        )

    except Exception as e:
        logger.error(f"Failed to get token stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get token stats: {str(e)}",
        )


class CalculateTokenRequest(BaseModel):
    """计算Token请求"""

    content: str = Field(..., min_length=1)


@router.post("/calculate")
async def calculate_tokens(
    request: CalculateTokenRequest,
    current_user: User = Depends(check_permission("memory.read")),
) -> dict[str, Any]:
    """
    计算Token数量

    权限: memory.read
    """
    try:
        token_service = get_token_service()

        token_count = token_service._calculate_tokens(request.content)

        return {
            "success": True,
            "content_length": len(request.content),
            "token_count": token_count,
        }

    except Exception as e:
        logger.error(f"Failed to calculate tokens: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate tokens: {str(e)}",
        )

"""
项目管理API路由
"""

from datetime import datetime
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ...common.logger import get_logger
from ...common.utils import generate_id
from ...models.tables import Project, User
from ..dependencies import check_permission, get_db

logger = get_logger(__name__)
router = APIRouter()


class CreateProjectRequest(BaseModel):
    """创建项目请求"""

    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    metadata: Optional[dict] = None


class CreateProjectResponse(BaseModel):
    """创建项目响应"""

    success: bool
    project_id: str
    name: str
    message: str


class UpdateProjectRequest(BaseModel):
    """更新项目请求"""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    metadata: Optional[dict] = None
    is_active: Optional[bool] = None


class ProjectResponse(BaseModel):
    """项目响应"""

    project_id: str
    name: str
    description: Optional[str]
    owner_id: str
    is_active: bool
    created_at: str
    updated_at: str


class ListProjectsResponse(BaseModel):
    """项目列表响应"""

    success: bool
    projects: List[ProjectResponse]
    total_count: int


@router.post("/create", response_model=CreateProjectResponse)
async def create_project(
    request: CreateProjectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("project.write")),
) -> Any:
    """
    创建项目

    权限: project.write
    """
    try:
        # 检查项目名称是否已存在
        existing = (
            db.query(Project)
            .filter(
                Project.name == request.name,
                Project.owner_id == current_user.user_id,
            )
            .first()
        )

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project name already exists",
            )

        # 创建项目
        project_id = generate_id("proj")
        new_project = Project(
            project_id=project_id,
            name=request.name,
            description=request.description,
            owner_id=current_user.user_id,
            metadata=request.metadata or {},
            is_active=True,
        )

        db.add(new_project)
        db.commit()
        db.refresh(new_project)

        logger.info(
            f"Project created by {current_user.username}: "
            f"{request.name} ({project_id})"
        )

        return CreateProjectResponse(
            success=True,
            project_id=project_id,
            name=request.name,
            message="Project created successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create project: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create project: {str(e)}",
        )


@router.get("/list", response_model=ListProjectsResponse)
async def list_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("project.read")),
) -> Any:
    """
    列出项目

    权限: project.read
    """
    try:
        # 管理员可以看到所有项目，普通用户只能看到自己的
        query = db.query(Project)

        if current_user.role != "admin":
            query = query.filter(Project.owner_id == current_user.user_id)

        total_count = query.count()
        projects = query.order_by(Project.created_at.desc()).offset(skip).limit(limit).all()

        project_list = [
            ProjectResponse(
                project_id=p.project_id,
                name=p.name,
                description=p.description,
                owner_id=p.owner_id,
                is_active=p.is_active,
                created_at=p.created_at.isoformat(),
                updated_at=p.updated_at.isoformat(),
            )
            for p in projects
        ]

        logger.info(
            f"Projects listed by {current_user.username}: "
            f"{len(project_list)} items"
        )

        return ListProjectsResponse(
            success=True,
            projects=project_list,
            total_count=total_count,
        )

    except Exception as e:
        logger.error(f"Failed to list projects: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list projects: {str(e)}",
        )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("project.read")),
) -> Any:
    """
    获取项目详情

    权限: project.read
    """
    try:
        project = db.query(Project).filter(Project.project_id == project_id).first()

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )

        # 检查权限：管理员或项目所有者
        if current_user.role != "admin" and project.owner_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

        return ProjectResponse(
            project_id=project.project_id,
            name=project.name,
            description=project.description,
            owner_id=project.owner_id,
            is_active=project.is_active,
            created_at=project.created_at.isoformat(),
            updated_at=project.updated_at.isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get project: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get project: {str(e)}",
        )


@router.put("/{project_id}", response_model=dict)
async def update_project(
    project_id: str,
    request: UpdateProjectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("project.write")),
) -> Any:
    """
    更新项目

    权限: project.write
    """
    try:
        project = db.query(Project).filter(Project.project_id == project_id).first()

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )

        # 检查权限：管理员或项目所有者
        if current_user.role != "admin" and project.owner_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

        # 更新字段
        if request.name is not None:
            project.name = request.name
        if request.description is not None:
            project.description = request.description
        if request.metadata is not None:
            project.metadata = request.metadata
        if request.is_active is not None:
            project.is_active = request.is_active

        project.updated_at = datetime.utcnow()

        db.commit()

        logger.info(
            f"Project updated by {current_user.username}: {project_id}"
        )

        return {
            "success": True,
            "project_id": project_id,
            "message": "Project updated successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update project: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update project: {str(e)}",
        )


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("project.delete")),
) -> dict[str, Any]:
    """
    删除项目

    权限: project.delete
    """
    try:
        project = db.query(Project).filter(Project.project_id == project_id).first()

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )

        # 检查权限：管理员或项目所有者
        if current_user.role != "admin" and project.owner_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

        # 软删除：设置为非活跃
        project.is_active = False
        project.updated_at = datetime.utcnow()

        db.commit()

        logger.info(
            f"Project deleted by {current_user.username}: {project_id}"
        )

        return {
            "success": True,
            "project_id": project_id,
            "message": "Project deleted successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete project: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete project: {str(e)}",
        )

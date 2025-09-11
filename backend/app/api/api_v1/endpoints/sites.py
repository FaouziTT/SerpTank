"""
Sites API endpoint - provides site management functionality.

This endpoint serves as an interface to manage sites (which are essentially projects
with URLs). It provides CRUD operations for sites that are used by the frontend.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Any, Dict
import logging

from app.db.session import get_db
from app.models.project import Project
from app.models.user import User
from app.auth.core.dependencies import get_current_active_user
from app.auth.schemas.auth import UserProfile
from app.schemas.project import ProjectCreate, ProjectOut
from app.core.pagination import PageParams, get_pagination_params, paginate
from app.core.db_optimization import optimize_for_read
from app.core.structured_logging import get_logger, log_execution_time, log_business_event
from app.core.audit import audit_action, AuditActions, ResourceTypes

logger = get_logger(__name__)

router = APIRouter()


@router.get("/", response_model=Dict[str, Any])
@optimize_for_read
async def get_all_sites(
    pagination: PageParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile = Depends(get_current_active_user),
) -> Any:
    """
    Get all sites (projects) for the current user with pagination.
    
    Args:
        pagination: Pagination parameters (page, page_size)
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Paginated list of sites/projects owned by the current user
    """
    try:
        query = select(Project).where(Project.user_id == current_user.id).order_by(Project.created_at.desc())
        
        result = await paginate(
            db=db,
            query=query,
            page_params=pagination,
            response_model=ProjectOut
        )
        
        logger.info(f"Retrieved page {pagination.page} of sites for user {current_user.id}")
        return result
        
    except Exception as e:
        logger.error(f"Error retrieving sites for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve sites"
        )


@router.get("/{site_id}", response_model=ProjectOut)
async def get_site_by_id(
    site_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile = Depends(get_current_active_user),
) -> Any:
    """
    Get a specific site by ID.
    
    Args:
        site_id: The site ID to retrieve
        
    Returns:
        The site/project data
        
    Raises:
        HTTPException: If site not found or access denied
    """
    try:
        result = await db.execute(
            select(Project).where(
                Project.id == site_id,
                Project.user_id == current_user.id
            )
        )
        project = result.scalar_one_or_none()
        
        if not project:
            logger.warning(f"Site {site_id} not found for user {current_user.id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Site not found"
            )
            
        logger.info(f"Retrieved site {site_id} for user {current_user.id}")
        return project
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving site {site_id} for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve site"
        )


@router.post("/", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def create_site(
    site_data: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile = Depends(get_current_active_user),
) -> Any:
    """
    Create a new site.
    
    Args:
        site_data: The site data to create
        
    Returns:
        The created site/project
    """
    try:
        # Validate URL format
        if not site_data.url or not site_data.url.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Site URL is required"
            )
            
        # Create new project (site)
        project = Project(
            user_id=current_user.id,
            name=site_data.name,
            url=site_data.url.strip(),
            description=site_data.description,
        )
        
        db.add(project)
        await db.commit()
        await db.refresh(project)
        
        logger.info(f"Created site {project.id} for user {current_user.id}")
        return project
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating site for user {current_user.id}: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create site"
        )


@router.put("/{site_id}", response_model=ProjectOut)
async def update_site(
    site_id: int,
    site_data: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile = Depends(get_current_active_user),
) -> Any:
    """
    Update an existing site.
    
    Args:
        site_id: The site ID to update
        site_data: The updated site data
        
    Returns:
        The updated site/project
        
    Raises:
        HTTPException: If site not found or access denied
    """
    try:
        result = await db.execute(
            select(Project).where(
                Project.id == site_id,
                Project.user_id == current_user.id
            )
        )
        project = result.scalar_one_or_none()
        
        if not project:
            logger.warning(f"Site {site_id} not found for user {current_user.id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Site not found"
            )
            
        # Validate URL format
        if not site_data.url or not site_data.url.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Site URL is required"
            )
            
        # Update project fields
        project.name = site_data.name
        project.url = site_data.url.strip()
        project.description = site_data.description
        
        await db.commit()
        await db.refresh(project)
        
        logger.info(f"Updated site {site_id} for user {current_user.id}")
        return project
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating site {site_id} for user {current_user.id}: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update site"
        )


@router.delete("/{site_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_site(
    site_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile = Depends(get_current_active_user),
) -> None:
    """
    Delete a site.
    
    Args:
        site_id: The site ID to delete
        
    Raises:
        HTTPException: If site not found or access denied
    """
    try:
        result = await db.execute(
            select(Project).where(
                Project.id == site_id,
                Project.user_id == current_user.id
            )
        )
        project = result.scalar_one_or_none()
        
        if not project:
            logger.warning(f"Site {site_id} not found for user {current_user.id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Site not found"
            )
            
        await db.delete(project)
        await db.commit()
        
        logger.info(f"Deleted site {site_id} for user {current_user.id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting site {site_id} for user {current_user.id}: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete site"
        )
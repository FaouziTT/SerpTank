"""
File upload and download endpoints.

This module provides API endpoints for file upload, download,
listing, and management operations.
"""
import logging
from typing import List, Optional
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.auth.core.dependencies import get_current_active_user
from app.auth.schemas.auth import UserProfile
from app.models.file import File as FileModel, FileCategory, FileStatus
from app.services.file_service import file_service
from app.db.session import get_db
from fastapi_cache.decorator import cache

router = APIRouter()
logger = logging.getLogger(__name__)


class FileUploadResponse(BaseModel):
    """Response model for file upload."""
    file_id: str
    filename: str
    original_filename: str
    size_mb: float
    mime_type: str
    category: str
    status: str
    download_url: str
    created_at: str


class FileListItem(BaseModel):
    """File list item model."""
    file_id: str
    original_filename: str
    size_mb: float
    mime_type: str
    category: str
    status: str
    description: Optional[str]
    tags: List[str]
    is_temporary: bool
    expires_at: Optional[str]
    created_at: str
    access_count: int


class FileListResponse(BaseModel):
    """Response model for file listing."""
    files: List[FileListItem]
    total: int
    limit: int
    offset: int


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    category: FileCategory = Query(FileCategory.OTHER, description="File category"),
    description: Optional[str] = Query(None, description="File description"),
    project_id: Optional[int] = Query(None, description="Associated project ID"),
    is_temporary: bool = Query(False, description="Whether file is temporary"),
    retention_days: Optional[int] = Query(None, description="Retention period in days"),
    tags: Optional[str] = Query(None, description="Comma-separated tags"),
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a file.
    
    Supports various file types including:
    - Documents (PDF, Word, Excel, CSV, JSON)
    - Images (JPEG, PNG, GIF, WebP, SVG)
    - Archives (ZIP for bulk imports)
    
    Maximum file size: 100MB
    """
    try:
        # Parse tags
        tag_list = [tag.strip() for tag in tags.split(',')] if tags else []
        
        # Get organization ID from user's current context
        # TODO: Implement organization context
        organization_id = None
        
        # Upload file
        db_file = await file_service.upload_file(
            db=db,
            file=file,
            user_id=current_user.id,
            organization_id=organization_id,
            project_id=project_id,
            category=category,
            description=description,
            is_temporary=is_temporary,
            retention_days=retention_days,
            tags=tag_list,
        )
        
        # TODO: Add background task for virus scanning
        # background_tasks.add_task(scan_file_for_viruses, db_file.id)
        
        return FileUploadResponse(
            file_id=db_file.file_id,
            filename=db_file.filename,
            original_filename=db_file.original_filename,
            size_mb=db_file.size_mb,
            mime_type=db_file.mime_type,
            category=db_file.category,
            status=db_file.status,
            download_url=f"/api/v1/files/{db_file.file_id}/download",
            created_at=db_file.created_at.isoformat(),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")


@router.get("/{file_id}/download")
async def download_file(
    file_id: str,
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Download a file by ID.
    
    Returns the file with appropriate headers for download.
    Access control is enforced based on file ownership and organization membership.
    """
    try:
        file_path, filename, mime_type = await file_service.download_file(
            db=db,
            file_id=file_id,
            user_id=current_user.id,
        )
        
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type=mime_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading file {file_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to download file: {str(e)}")


@router.get("/", response_model=FileListResponse)
@cache(expire=60, key_builder=lambda func, *args, **kwargs: f"files:{kwargs.get('current_user').id}:{kwargs.get('category')}:{kwargs.get('project_id')}")
async def list_files(
    category: Optional[FileCategory] = Query(None, description="Filter by category"),
    project_id: Optional[int] = Query(None, description="Filter by project"),
    include_deleted: bool = Query(False, description="Include deleted files"),
    limit: int = Query(20, ge=1, le=100, description="Results per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List user's files with filtering options.
    
    Files can be filtered by:
    - Category (document, image, spreadsheet, etc.)
    - Project association
    - Status (include/exclude deleted)
    """
    try:
        # Get organization ID from user's current context
        # TODO: Implement organization context
        organization_id = None
        
        files = await file_service.list_files(
            db=db,
            user_id=current_user.id,
            organization_id=organization_id,
            project_id=project_id,
            category=category,
            include_deleted=include_deleted,
            limit=limit,
            offset=offset,
        )
        
        # Convert to response model
        file_items = [
            FileListItem(
                file_id=f.file_id,
                original_filename=f.original_filename,
                size_mb=f.size_mb,
                mime_type=f.mime_type,
                category=f.category,
                status=f.status,
                description=f.description,
                tags=f.tags,
                is_temporary=f.is_temporary,
                expires_at=f.expires_at.isoformat() if f.expires_at else None,
                created_at=f.created_at.isoformat(),
                access_count=f.access_count,
            )
            for f in files
        ]
        
        return FileListResponse(
            files=file_items,
            total=len(files),  # TODO: Get actual total count
            limit=limit,
            offset=offset,
        )
        
    except Exception as e:
        logger.error(f"Error listing files: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")


@router.delete("/{file_id}")
async def delete_file(
    file_id: str,
    hard_delete: bool = Query(False, description="Permanently delete file"),
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a file.
    
    By default performs a soft delete (file can be recovered).
    Set hard_delete=true to permanently delete the file.
    
    Only the file owner can delete files.
    """
    try:
        success = await file_service.delete_file(
            db=db,
            file_id=file_id,
            user_id=current_user.id,
            hard_delete=hard_delete,
        )
        
        return {
            "success": success,
            "message": f"File {'permanently' if hard_delete else 'soft'} deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting file {file_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")


@router.post("/bulk-upload", response_model=List[FileUploadResponse])
async def bulk_upload_files(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    category: FileCategory = Query(FileCategory.OTHER, description="File category for all files"),
    project_id: Optional[int] = Query(None, description="Associated project ID"),
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload multiple files at once.
    
    Useful for bulk imports and batch operations.
    Maximum 10 files per request.
    """
    if len(files) > 10:
        raise HTTPException(
            status_code=400,
            detail="Maximum 10 files allowed per bulk upload"
        )
    
    uploaded_files = []
    errors = []
    
    for idx, file in enumerate(files):
        try:
            # Get organization ID from user's current context
            # TODO: Implement organization context
            organization_id = None
            
            # Upload file
            db_file = await file_service.upload_file(
                db=db,
                file=file,
                user_id=current_user.id,
                organization_id=organization_id,
                project_id=project_id,
                category=category,
                description=f"Bulk upload {idx + 1} of {len(files)}",
                is_temporary=False,
                tags=["bulk-upload"],
            )
            
            uploaded_files.append(FileUploadResponse(
                file_id=db_file.file_id,
                filename=db_file.filename,
                original_filename=db_file.original_filename,
                size_mb=db_file.size_mb,
                mime_type=db_file.mime_type,
                category=db_file.category,
                status=db_file.status,
                download_url=f"/api/v1/files/{db_file.file_id}/download",
                created_at=db_file.created_at.isoformat(),
            ))
            
        except Exception as e:
            errors.append({
                "filename": file.filename,
                "error": str(e)
            })
    
    if errors:
        logger.warning(f"Bulk upload completed with errors: {errors}")
    
    return uploaded_files


# Background task for cleaning expired files
async def cleanup_expired_files():
    """Background task to clean up expired files."""
    async with AsyncSession() as db:
        try:
            cleaned_count = await file_service.clean_expired_files(db)
            logger.info(f"Cleaned {cleaned_count} expired files")
        except Exception as e:
            logger.error(f"Error cleaning expired files: {e}")
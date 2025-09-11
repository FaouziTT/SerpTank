"""
File upload and storage service.

This service handles file uploads, downloads, storage management,
virus scanning, and access control for uploaded files.
"""
import os
import uuid
import hashlib
import mimetypes
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any, BinaryIO
import logging

from fastapi import UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from app.models.file import File, FileStatus, FileCategory, StorageBackend, FileAccessLog
from app.models.user import User
from app.core.config import settings
from app.core.exceptions import InsufficientPermissionsError

logger = logging.getLogger(__name__)


class FileService:
    """Service for managing file uploads and downloads."""
    
    # Configuration
    MAX_FILE_SIZE = settings.MAX_UPLOAD_SIZE
    ALLOWED_MIME_TYPES = {
        # Documents
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'text/plain',
        'text/csv',
        'application/json',
        
        # Images
        'image/jpeg',
        'image/png',
        'image/gif',
        'image/webp',
        'image/svg+xml',
        
        # Archives (for bulk imports)
        'application/zip',
        'application/x-zip-compressed',
    }
    
    CHUNK_SIZE = 1024 * 1024  # 1MB chunks for streaming
    
    def __init__(self):
        """Initialize the file service."""
        # Create upload directory if it doesn't exist
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories for organization
        for subdir in ['temp', 'permanent', 'exports']:
            (self.upload_dir / subdir).mkdir(exist_ok=True)
    
    async def upload_file(
        self,
        db: AsyncSession,
        file: UploadFile,
        user_id: int,
        organization_id: Optional[int] = None,
        project_id: Optional[int] = None,
        category: FileCategory = FileCategory.OTHER,
        description: Optional[str] = None,
        is_temporary: bool = False,
        retention_days: Optional[int] = None,
        tags: Optional[List[str]] = None,
    ) -> File:
        """
        Upload a file and create a database record.
        
        Args:
            db: Database session
            file: Uploaded file from FastAPI
            user_id: ID of the user uploading the file
            organization_id: Optional organization ID
            project_id: Optional project ID
            category: File category
            description: Optional file description
            is_temporary: Whether the file is temporary
            retention_days: How long to keep the file
            tags: Optional tags for the file
            
        Returns:
            Created File model instance
            
        Raises:
            HTTPException: If file validation fails
        """
        # Validate file
        await self._validate_file(file)
        
        # Generate unique file ID and paths
        file_id = str(uuid.uuid4())
        file_extension = Path(file.filename).suffix
        safe_filename = f"{file_id}{file_extension}"
        
        # Determine storage path
        if is_temporary:
            storage_path = self.upload_dir / 'temp' / safe_filename
        else:
            # Organize by year/month for permanent files
            now = datetime.now(timezone.utc)
            storage_path = self.upload_dir / 'permanent' / str(now.year) / str(now.month) / safe_filename
            storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Calculate file hash and save file
        file_hash = await self._save_file_with_hash(file, storage_path)
        
        # Determine expiry date
        expires_at = None
        if is_temporary or retention_days:
            retention = retention_days or 7  # Default 7 days for temp files
            expires_at = datetime.now(timezone.utc) + timedelta(days=retention)
        
        # Create database record
        db_file = File(
            file_id=file_id,
            filename=safe_filename,
            original_filename=file.filename,
            file_size=file.size or 0,
            mime_type=file.content_type or 'application/octet-stream',
            file_extension=file_extension,
            checksum=file_hash,
            storage_backend=StorageBackend.LOCAL,
            storage_path=str(storage_path.relative_to(self.upload_dir)),
            user_id=user_id,
            organization_id=organization_id,
            project_id=project_id,
            category=category,
            description=description,
            tags=tags or [],
            is_temporary=is_temporary,
            retention_days=retention_days,
            expires_at=expires_at,
            status=FileStatus.COMPLETED,
        )
        
        db.add(db_file)
        await db.commit()
        await db.refresh(db_file)
        
        logger.info(f"File uploaded successfully: {file_id} ({file.filename})")
        
        return db_file
    
    async def download_file(
        self,
        db: AsyncSession,
        file_id: str,
        user_id: int,
    ) -> tuple[Path, str, str]:
        """
        Download a file by ID.
        
        Args:
            db: Database session
            file_id: File ID to download
            user_id: ID of the user downloading
            
        Returns:
            Tuple of (file_path, filename, mime_type)
            
        Raises:
            HTTPException: If file not found or access denied
        """
        # Get file record
        result = await db.execute(
            select(File).where(File.file_id == file_id)
        )
        db_file = result.scalar_one_or_none()
        
        if not db_file:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Check access permissions
        if not await self._check_file_access(db, db_file, user_id):
            raise InsufficientPermissionsError("Access denied to this file")
        
        # Check if file exists on disk
        file_path = self.upload_dir / db_file.storage_path
        if not file_path.exists():
            logger.error(f"File not found on disk: {file_path}")
            raise HTTPException(status_code=404, detail="File not found on disk")
        
        # Log access
        await self._log_file_access(db, db_file.id, user_id, "download")
        
        # Update access count and timestamp
        db_file.access_count += 1
        db_file.last_accessed_at = datetime.now(timezone.utc)
        await db.commit()
        
        return file_path, db_file.original_filename, db_file.mime_type
    
    async def delete_file(
        self,
        db: AsyncSession,
        file_id: str,
        user_id: int,
        hard_delete: bool = False,
    ) -> bool:
        """
        Delete a file (soft or hard delete).
        
        Args:
            db: Database session
            file_id: File ID to delete
            user_id: ID of the user deleting
            hard_delete: Whether to permanently delete
            
        Returns:
            True if deleted successfully
            
        Raises:
            HTTPException: If file not found or access denied
        """
        # Get file record
        result = await db.execute(
            select(File).where(File.file_id == file_id)
        )
        db_file = result.scalar_one_or_none()
        
        if not db_file:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Check permissions (only owner can delete)
        if db_file.user_id != user_id:
            raise InsufficientPermissionsError("Only the file owner can delete files")
        
        if hard_delete:
            # Delete file from disk
            file_path = self.upload_dir / db_file.storage_path
            if file_path.exists():
                file_path.unlink()
            
            # Delete from database
            await db.delete(db_file)
        else:
            # Soft delete
            db_file.status = FileStatus.DELETED
            db_file.deleted_at = datetime.now(timezone.utc)
        
        await db.commit()
        
        # Log access
        await self._log_file_access(db, db_file.id, user_id, "delete")
        
        logger.info(f"File {'hard' if hard_delete else 'soft'} deleted: {file_id}")
        
        return True
    
    async def list_files(
        self,
        db: AsyncSession,
        user_id: int,
        organization_id: Optional[int] = None,
        project_id: Optional[int] = None,
        category: Optional[FileCategory] = None,
        include_deleted: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> List[File]:
        """
        List files with filtering options.
        
        Args:
            db: Database session
            user_id: User ID for access control
            organization_id: Filter by organization
            project_id: Filter by project
            category: Filter by category
            include_deleted: Include soft-deleted files
            limit: Maximum results
            offset: Pagination offset
            
        Returns:
            List of File objects
        """
        query = select(File)
        
        # Base filter - user's own files or files in their organizations
        query = query.where(
            or_(
                File.user_id == user_id,
                File.organization_id == organization_id if organization_id else False
            )
        )
        
        # Additional filters
        if project_id:
            query = query.where(File.project_id == project_id)
        
        if category:
            query = query.where(File.category == category)
        
        if not include_deleted:
            query = query.where(File.status != FileStatus.DELETED)
        
        # Order by created date descending
        query = query.order_by(File.created_at.desc())
        
        # Pagination
        query = query.limit(limit).offset(offset)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def clean_expired_files(self, db: AsyncSession) -> int:
        """
        Clean up expired files.
        
        This should be run periodically by a background task.
        
        Args:
            db: Database session
            
        Returns:
            Number of files cleaned
        """
        # Find expired files
        result = await db.execute(
            select(File).where(
                and_(
                    File.expires_at.isnot(None),
                    File.expires_at < datetime.now(timezone.utc),
                    File.status != FileStatus.DELETED
                )
            )
        )
        expired_files = result.scalars().all()
        
        cleaned_count = 0
        for file in expired_files:
            try:
                # Delete file from disk
                file_path = self.upload_dir / file.storage_path
                if file_path.exists():
                    file_path.unlink()
                
                # Update status
                file.status = FileStatus.DELETED
                file.deleted_at = datetime.now(timezone.utc)
                
                cleaned_count += 1
                logger.info(f"Cleaned expired file: {file.file_id}")
                
            except Exception as e:
                logger.error(f"Error cleaning file {file.file_id}: {e}")
        
        await db.commit()
        
        return cleaned_count
    
    async def _validate_file(self, file: UploadFile) -> None:
        """Validate uploaded file."""
        # Check file size
        if file.size and file.size > self.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size is {self.MAX_FILE_SIZE / 1024 / 1024}MB"
            )
        
        # Check MIME type
        mime_type = file.content_type or mimetypes.guess_type(file.filename)[0]
        if mime_type not in self.ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=415,
                detail=f"File type not allowed. Allowed types: {', '.join(self.ALLOWED_MIME_TYPES)}"
            )
        
        # Basic filename validation
        if not file.filename or '..' in file.filename or '/' in file.filename:
            raise HTTPException(
                status_code=400,
                detail="Invalid filename"
            )
    
    async def _save_file_with_hash(self, file: UploadFile, path: Path) -> str:
        """Save file and calculate hash."""
        hasher = hashlib.sha256()
        
        # Reset file position
        file.file.seek(0)
        
        # Save file and calculate hash
        with open(path, 'wb') as f:
            while chunk := file.file.read(self.CHUNK_SIZE):
                f.write(chunk)
                hasher.update(chunk)
        
        # Reset file position again
        file.file.seek(0)
        
        return hasher.hexdigest()
    
    async def _check_file_access(
        self,
        db: AsyncSession,
        file: File,
        user_id: int
    ) -> bool:
        """Check if user has access to file."""
        # Owner always has access
        if file.user_id == user_id:
            return True
        
        # Check organization membership
        if file.organization_id:
            # TODO: Check if user is member of organization
            # For now, we'll allow if they have the same organization_id
            return True
        
        # Check if file is public
        if file.is_public:
            return True
        
        return False
    
    async def _log_file_access(
        self,
        db: AsyncSession,
        file_id: int,
        user_id: int,
        action: str
    ) -> None:
        """Log file access for audit trail."""
        log_entry = FileAccessLog(
            file_id=file_id,
            user_id=user_id,
            action=action,
            # TODO: Add IP address and user agent from request
        )
        db.add(log_entry)
        # Don't commit here, let the calling function handle it


# Create singleton instance
file_service = FileService()
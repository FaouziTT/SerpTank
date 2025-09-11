"""
File upload and storage models.

This module defines the database models for file uploads, including
metadata tracking, access control, and storage management.
"""
from datetime import datetime
from enum import Enum
from typing import Optional
from sqlalchemy import Column, Integer, String, DateTime, BigInteger, Boolean, JSON, ForeignKey, Index, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base_class import Base


class FileStatus(str, Enum):
    """File processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DELETED = "deleted"


class FileCategory(str, Enum):
    """File categories for organization."""
    DOCUMENT = "document"
    IMAGE = "image"
    SPREADSHEET = "spreadsheet"
    REPORT = "report"
    EXPORT = "export"
    IMPORT = "import"
    BACKUP = "backup"
    OTHER = "other"


class StorageBackend(str, Enum):
    """Storage backend types."""
    LOCAL = "local"
    S3 = "s3"
    GCS = "gcs"
    AZURE = "azure"


class File(Base):
    """File upload model for tracking uploaded files."""
    __tablename__ = "files"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # File identification
    file_id = Column(String(100), unique=True, nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    
    # File metadata
    file_size = Column(BigInteger, nullable=False)  # Size in bytes
    mime_type = Column(String(100), nullable=False)
    file_extension = Column(String(50))
    checksum = Column(String(64))  # SHA-256 hash
    
    # Storage information
    storage_backend = Column(String(20), default=StorageBackend.LOCAL)
    storage_path = Column(String(500), nullable=False)
    storage_url = Column(String(1000))  # Public URL if available
    
    # Organization and access
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id"), index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), index=True)
    
    # File categorization
    category = Column(String(50), default=FileCategory.OTHER)
    tags = Column(JSON, default=list)
    description = Column(Text)
    
    # Processing status
    status = Column(String(20), default=FileStatus.PENDING)
    processing_error = Column(Text)
    
    # Security and access
    is_public = Column(Boolean, default=False)
    is_sensitive = Column(Boolean, default=False)
    access_count = Column(Integer, default=0)
    last_accessed_at = Column(DateTime(timezone=True))
    
    # Virus scanning
    virus_scanned = Column(Boolean, default=False)
    virus_scan_result = Column(String(50))
    virus_scan_date = Column(DateTime(timezone=True))
    
    # Retention and lifecycle
    retention_days = Column(Integer)  # How long to keep the file
    expires_at = Column(DateTime(timezone=True))
    is_temporary = Column(Boolean, default=False)
    
    # Additional metadata
    file_metadata = Column(JSON, default=dict)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True))  # Soft delete
    
    # Relationships
    user = relationship("User", back_populates="files")
    organization = relationship("Organization", back_populates="files")
    project = relationship("Project", back_populates="files")
    
    # Indexes for performance
    __table_args__ = (
        Index("idx_file_user_created", "user_id", "created_at"),
        Index("idx_file_org_category", "organization_id", "category"),
        Index("idx_file_project_status", "project_id", "status"),
        Index("idx_file_expires", "expires_at"),
        Index("idx_file_checksum", "checksum"),
    )
    
    def __repr__(self):
        return f"<File(id={self.id}, filename='{self.filename}', size={self.file_size})>"
    
    @property
    def size_mb(self) -> float:
        """Get file size in megabytes."""
        return self.file_size / (1024 * 1024)
    
    @property
    def is_expired(self) -> bool:
        """Check if file has expired."""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_image(self) -> bool:
        """Check if file is an image."""
        image_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/svg+xml']
        return self.mime_type in image_types
    
    @property
    def is_document(self) -> bool:
        """Check if file is a document."""
        doc_types = [
            'application/pdf', 
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'text/plain',
            'text/csv'
        ]
        return self.mime_type in doc_types


class FileAccessLog(Base):
    """Log file access for security and analytics."""
    __tablename__ = "file_access_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("files.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    action = Column(String(50), nullable=False)  # download, view, share, delete
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    file = relationship("File")
    user = relationship("User")
    
    __table_args__ = (
        Index("idx_file_access_file_user", "file_id", "user_id"),
        Index("idx_file_access_created", "created_at"),
    )
"""
Pagination utilities for API endpoints.

This module provides reusable pagination functionality for list endpoints
to improve performance and reduce memory usage.
"""
from typing import TypeVar, Generic, List, Optional, Dict, Any
from pydantic import BaseModel, Field
from fastapi import Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

T = TypeVar('T')


class PageParams(BaseModel):
    """Common pagination parameters."""
    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")
    
    @property
    def offset(self) -> int:
        """Calculate offset for database query."""
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        """Get limit for database query."""
        return self.page_size


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response model."""
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool
    
    @classmethod
    def create(
        cls,
        items: List[T],
        total: int,
        page: int,
        page_size: int
    ) -> "PaginatedResponse[T]":
        """Create a paginated response."""
        total_pages = (total + page_size - 1) // page_size  # Ceiling division
        
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1
        )


async def paginate(
    db: AsyncSession,
    query: Select,
    page_params: PageParams,
    response_model: Optional[type] = None
) -> Dict[str, Any]:
    """
    Paginate a SQLAlchemy query.
    
    Args:
        db: Database session
        query: SQLAlchemy query
        page_params: Pagination parameters
        response_model: Optional Pydantic model to serialize results
        
    Returns:
        Dictionary with paginated results
    """
    # Count total items
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Get paginated items
    paginated_query = query.offset(page_params.offset).limit(page_params.limit)
    result = await db.execute(paginated_query)
    items = result.scalars().all()
    
    # Serialize if response model provided
    if response_model:
        items = [response_model.model_validate(item) for item in items]
    
    # Calculate total pages
    total_pages = (total + page_params.page_size - 1) // page_params.page_size
    
    return {
        "items": items,
        "meta": {
            "page": page_params.page,
            "size": page_params.page_size,
            "total": total,
            "pages": total_pages
        }
    }


def create_pagination_params(
    page: int = 1,
    page_size: int = 20
) -> PageParams:
    """
    Create pagination parameters with validation.
    
    Args:
        page: Page number (1-indexed)
        page_size: Items per page
        
    Returns:
        Validated PageParams instance
    """
    return PageParams(page=page, page_size=page_size)


# Dependency for FastAPI endpoints
async def get_pagination_params(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page")
) -> PageParams:
    """
    FastAPI dependency for pagination parameters.
    
    Usage:
        @router.get("/items")
        async def list_items(
            pagination: PageParams = Depends(get_pagination_params),
            db: AsyncSession = Depends(get_db)
        ):
            ...
    """
    return PageParams(page=page, page_size=page_size)


class CursorPaginationParams(BaseModel):
    """Parameters for cursor-based pagination."""
    cursor: Optional[str] = Field(None, description="Cursor for next page")
    limit: int = Field(default=20, ge=1, le=100, description="Items per page")
    direction: str = Field(default="next", pattern="^(next|previous)$")


class CursorPaginatedResponse(BaseModel, Generic[T]):
    """Response model for cursor-based pagination."""
    items: List[T]
    next_cursor: Optional[str]
    previous_cursor: Optional[str]
    has_next: bool
    has_previous: bool


def encode_cursor(value: Any) -> str:
    """Encode a value as a cursor."""
    import base64
    import json
    
    cursor_data = {"value": str(value)}
    cursor_bytes = json.dumps(cursor_data).encode('utf-8')
    return base64.urlsafe_b64encode(cursor_bytes).decode('utf-8')


def decode_cursor(cursor: str) -> Any:
    """Decode a cursor to get the value."""
    import base64
    import json
    
    try:
        cursor_bytes = base64.urlsafe_b64decode(cursor.encode('utf-8'))
        cursor_data = json.loads(cursor_bytes.decode('utf-8'))
        return cursor_data.get("value")
    except Exception:
        return None


# Response models for common list endpoints
class PaginatedProjects(PaginatedResponse):
    """Paginated response for projects."""
    pass


class PaginatedSites(PaginatedResponse):
    """Paginated response for sites."""
    pass


class PaginatedKeywords(PaginatedResponse):
    """Paginated response for keywords."""
    pass


class PaginatedActivities(PaginatedResponse):
    """Paginated response for activities."""
    pass


class PaginatedNotifications(PaginatedResponse):
    """Paginated response for notifications."""
    pass
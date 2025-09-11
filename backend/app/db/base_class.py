"""
Base class for SQLAlchemy models.

This module defines the base class for all SQLAlchemy models in the application,
providing common functionality and configuration.
"""
from typing import Any

from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    
    id: Any
    
    # Generate __tablename__ automatically
    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()
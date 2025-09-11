from datetime import datetime, timezone
# --- Import TYPE_CHECKING and Mapped/mapped_column ---
from typing import TYPE_CHECKING
from sqlalchemy import Column, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.db.base_class import Base

# --- START: Add this type-checking block ---
if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.user import User
# --- END: Add this type-checking block ---


class ProjectTeamMember(Base):
    __tablename__ = "project_team_members"

    # Using modern mapped_column syntax for consistency
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"))
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    can_edit: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # This datetime column is already correct
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # --- FIX: Update relationships to use modern Mapped syntax ---
    project: Mapped["Project"] = relationship("Project", back_populates="team_members")
    user: Mapped["User"] = relationship("User", back_populates="project_memberships")
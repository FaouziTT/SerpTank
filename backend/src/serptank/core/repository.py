"""Tenant-scoped repository base class (application-level half of tenant isolation).

Every query issued through :class:`TenantRepository` is filtered by the organization the
repository was created for. A row belonging to another tenant is indistinguishable from
a missing row: :meth:`get` raises :class:`NotFoundError` (HTTP 404, never 403), so
callers cannot probe for the existence of other tenants' resources.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any, ClassVar

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from serptank.core.db import bound_organization_id
from serptank.core.errors import NotFoundError


class TenantRepository[ModelT: Any]:
    """Base for repositories of models using :class:`serptank.core.models.TenantMixin`."""

    model: ClassVar[type[Any]]
    not_found_message: ClassVar[str] = "Resource not found."

    def __init__(self, session: AsyncSession, organization_id: uuid.UUID) -> None:
        bound = bound_organization_id(session)
        if bound is not None and bound != organization_id:
            msg = "repository tenant differs from the tenant bound to the session"
            raise RuntimeError(msg)
        self.session = session
        self.organization_id = organization_id

    def _scoped(self) -> Select[tuple[ModelT]]:
        return select(self.model).where(self.model.organization_id == self.organization_id)

    async def get(self, entity_id: uuid.UUID) -> ModelT:
        entity = await self.find(entity_id)
        if entity is None:
            raise NotFoundError(self.not_found_message)
        return entity

    async def find(self, entity_id: uuid.UUID) -> ModelT | None:
        result = await self.session.execute(self._scoped().where(self.model.id == entity_id))
        entity: ModelT | None = result.scalar_one_or_none()
        return entity

    async def list(self, *, limit: int = 100, offset: int = 0) -> Sequence[ModelT]:
        stmt = self._scoped().order_by(self.model.id).limit(min(limit, 500)).offset(offset)
        rows: Sequence[ModelT] = (await self.session.execute(stmt)).scalars().all()
        return rows

    async def count(self) -> int:
        stmt = select(func.count()).select_from(self._scoped().subquery())
        return int((await self.session.execute(stmt)).scalar_one())

    def add(self, entity: ModelT) -> ModelT:
        # Force the tenant: callers can never create rows in another organization.
        entity.organization_id = self.organization_id
        self.session.add(entity)
        return entity

    async def delete(self, entity: ModelT) -> None:
        if entity.organization_id != self.organization_id:
            raise NotFoundError(self.not_found_message)
        await self.session.delete(entity)

"""Multi-tenancy guarantees at the database layer (plan §5.2, M2 exit criterion).

Rows are seeded as the schema owner; assertions run as a login role in
``serptank_app`` - exactly the privileges the API has in production.
"""

from __future__ import annotations

import uuid

import pytest
import sqlalchemy.exc
from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from serptank.core.audit import AuditEvent, record_audit_event
from serptank.core.db import bind_identity
from serptank.core.errors import NotFoundError
from serptank.core.models import MemberRole, SearchEngine, uuid7
from serptank.core.repository import TenantRepository
from serptank.modules.identity.models import User
from serptank.modules.projects.models import Project, ProjectMarket
from serptank.modules.tenancy.models import Membership, Organization


class ProjectRepository(TenantRepository[Project]):
    model = Project
    not_found_message = "Project not found."


class Seed:
    def __init__(self) -> None:
        self.alice = uuid7()
        self.bob = uuid7()
        self.org_a = uuid7()
        self.org_b = uuid7()
        self.project_a = uuid7()
        self.project_b = uuid7()


@pytest.fixture
async def seed(owner_session: AsyncSession) -> Seed:
    s = Seed()
    tag = uuid.uuid4().hex[:8]
    owner_session.add_all(
        [
            User(id=s.alice, email=f"alice-{tag}@example.com"),
            User(id=s.bob, email=f"bob-{tag}@example.com"),
        ]
    )
    await owner_session.flush()
    owner_session.add_all(
        [
            Organization(id=s.org_a, name="A", slug=f"a-{tag}", created_by_user_id=s.alice),
            Organization(id=s.org_b, name="B", slug=f"b-{tag}", created_by_user_id=s.bob),
        ]
    )
    await owner_session.flush()
    owner_session.add_all(
        [
            Membership(organization_id=s.org_a, user_id=s.alice, role=MemberRole.OWNER),
            Membership(organization_id=s.org_b, user_id=s.bob, role=MemberRole.OWNER),
            Project(id=s.project_a, organization_id=s.org_a, name="A", primary_domain="a.com"),
            Project(id=s.project_b, organization_id=s.org_b, name="B", primary_domain="b.com"),
        ]
    )
    await owner_session.commit()
    return s


async def _project_ids(session: AsyncSession) -> set[uuid.UUID]:
    return set((await session.execute(select(Project.id))).scalars())


async def test_no_tenant_bound_sees_nothing(app_session: AsyncSession, seed: Seed) -> None:
    assert await _project_ids(app_session) == set()


async def test_bound_tenant_sees_only_its_rows(app_session: AsyncSession, seed: Seed) -> None:
    await bind_identity(app_session, user_id=seed.alice, organization_id=seed.org_a)
    ids = await _project_ids(app_session)
    assert seed.project_a in ids
    assert seed.project_b not in ids


async def test_cannot_insert_into_other_tenant(app_session: AsyncSession, seed: Seed) -> None:
    await bind_identity(app_session, user_id=seed.alice, organization_id=seed.org_a)
    app_session.add(Project(organization_id=seed.org_b, name="x", primary_domain="evil.com"))
    with pytest.raises(sqlalchemy.exc.DBAPIError, match="row-level security"):
        await app_session.flush()


async def test_cannot_move_row_to_other_tenant(app_session: AsyncSession, seed: Seed) -> None:
    await bind_identity(app_session, user_id=seed.alice, organization_id=seed.org_a)
    with pytest.raises(sqlalchemy.exc.DBAPIError, match="row-level security"):
        await app_session.execute(
            update(Project).where(Project.id == seed.project_a).values(organization_id=seed.org_b)
        )


async def test_cannot_update_other_tenant_rows(app_session: AsyncSession, seed: Seed) -> None:
    await bind_identity(app_session, user_id=seed.alice, organization_id=seed.org_a)
    result = await app_session.execute(
        update(Project).where(Project.id == seed.project_b).values(name="pwned")
    )
    assert result.rowcount == 0  # type: ignore[attr-defined]


async def test_user_sees_own_memberships_and_orgs(app_session: AsyncSession, seed: Seed) -> None:
    await bind_identity(app_session, user_id=seed.alice)
    orgs = set((await app_session.execute(select(Organization.id))).scalars())
    assert orgs == {seed.org_a}
    memberships = (await app_session.execute(select(Membership.user_id))).scalars().all()
    assert set(memberships) == {seed.alice}


async def test_user_can_create_org_only_as_themself(app_session: AsyncSession, seed: Seed) -> None:
    await bind_identity(app_session, user_id=seed.alice)
    app_session.add(Organization(name="forged", slug=f"f-{uuid7()}", created_by_user_id=seed.bob))
    with pytest.raises(sqlalchemy.exc.DBAPIError, match="row-level security"):
        await app_session.flush()


async def test_identity_does_not_leak_across_transactions(
    app_engine: AsyncEngine, seed: Seed
) -> None:
    async with AsyncSession(app_engine) as first:
        await bind_identity(first, user_id=seed.alice, organization_id=seed.org_a)
        assert seed.project_a in await _project_ids(first)
        await first.commit()
    # Same pooled connection (pool_size=1), new session: nothing is bound.
    async with AsyncSession(app_engine) as second:
        setting = (
            await second.execute(text("SELECT current_setting('app.org_id', true)"))
        ).scalar()
        assert setting in {None, ""}
        assert await _project_ids(second) == set()


async def test_binding_survives_commit_within_session(
    app_session: AsyncSession, seed: Seed
) -> None:
    await bind_identity(app_session, user_id=seed.alice, organization_id=seed.org_a)
    await app_session.commit()
    assert seed.project_a in await _project_ids(app_session)


async def test_audit_log_is_append_only(app_session: AsyncSession, seed: Seed) -> None:
    await bind_identity(app_session, user_id=seed.alice, organization_id=seed.org_a)
    event = record_audit_event(
        app_session,
        "project.created",
        actor_user_id=seed.alice,
        organization_id=seed.org_a,
        details={"api_key": "sk-live-secret", "name": "A"},
    )
    await app_session.commit()
    assert event.details == {"api_key": "[REDACTED]", "name": "A"}
    with pytest.raises(sqlalchemy.exc.DBAPIError, match="permission denied"):
        await app_session.execute(update(AuditEvent).values(action="tampered"))
    await app_session.rollback()
    with pytest.raises(sqlalchemy.exc.DBAPIError, match="permission denied"):
        await app_session.execute(text("DELETE FROM audit_events"))


async def test_app_role_cannot_delete_users(app_session: AsyncSession, seed: Seed) -> None:
    with pytest.raises(sqlalchemy.exc.DBAPIError, match="permission denied"):
        await app_session.execute(text("DELETE FROM users"))


async def test_repository_hides_other_tenants(app_session: AsyncSession, seed: Seed) -> None:
    await bind_identity(app_session, user_id=seed.alice, organization_id=seed.org_a)
    repo = ProjectRepository(app_session, seed.org_a)
    assert (await repo.get(seed.project_a)).name == "A"
    with pytest.raises(NotFoundError, match="Project not found"):
        await repo.get(seed.project_b)
    assert await repo.count() == 1


async def test_repository_forces_its_tenant_on_add(app_session: AsyncSession, seed: Seed) -> None:
    await bind_identity(app_session, user_id=seed.alice, organization_id=seed.org_a)
    repo = ProjectRepository(app_session, seed.org_a)
    project = repo.add(Project(organization_id=seed.org_b, name="n", primary_domain="n.com"))
    await app_session.flush()
    assert project.organization_id == seed.org_a


async def test_repository_rejects_mismatched_session(app_session: AsyncSession, seed: Seed) -> None:
    await bind_identity(app_session, organization_id=seed.org_a)
    with pytest.raises(RuntimeError):
        ProjectRepository(app_session, seed.org_b)


async def test_market_constraints(app_session: AsyncSession, seed: Seed) -> None:
    await bind_identity(app_session, user_id=seed.alice, organization_id=seed.org_a)
    market = ProjectMarket(
        organization_id=seed.org_a, project_id=seed.project_a, country="US", language="en"
    )
    app_session.add(market)
    await app_session.flush()
    assert market.search_engines == [SearchEngine.GOOGLE]
    bad = ProjectMarket(
        organization_id=seed.org_a, project_id=seed.project_a, country="us", language="en"
    )
    app_session.add(bad)
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        await app_session.flush()

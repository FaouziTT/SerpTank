"""
Pytest configuration and fixtures for the Voltex DSE backend test suite.
"""

import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator, Generator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, AsyncEngine
from sqlalchemy.pool import NullPool
from httpx import AsyncClient
from fastapi.testclient import TestClient
import redis.asyncio as aioredis

from app.main import app
from app.db.session import get_db
from app.db.base_class import Base
from app.core.config import settings
from app.models.user import User
from app.models.organization import Organization, OrganizationMember, MemberRole, MemberStatus
from app.models.project import Project
from app.auth.services.auth_service import AuthService
from app.auth.schemas.auth import RegisterRequest, LoginRequest


# Test database configuration
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

@pytest_asyncio.fixture
async def async_engine() -> AsyncEngine:
    """Create async engine for testing."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
        echo=False  # Set to True for SQL debugging
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Drop all tables after tests
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture
async def async_session(async_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Create async session for testing."""
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        yield session


@pytest_asyncio.fixture
async def override_get_db(async_session: AsyncSession):
    """Override the get_db dependency for testing."""
    async def _override_get_db():
        yield async_session
    
    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def async_client(override_get_db) -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client for testing."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def sync_client(override_get_db) -> Generator[TestClient, None, None]:
    """Create sync HTTP client for testing."""
    with TestClient(app) as client:
        yield client


@pytest_asyncio.fixture
async def redis_client():
    """Create Redis client for testing."""
    redis = aioredis.from_url(
        "redis://localhost:6379/15",  # Use a different DB for tests
        encoding="utf-8",
        decode_responses=True
    )
    
    # Clear test database
    await redis.flushdb()
    yield redis
    
    # Cleanup
    await redis.flushdb()
    await redis.close()


# User and organization fixtures
@pytest_asyncio.fixture
async def test_user(async_session: AsyncSession) -> User:
    """Create a test user."""
    from app.auth.core.security import get_password_hash
    
    user = User(
        email="test@example.com",
        full_name="Test User",
        hashed_password=get_password_hash("testpassword123"),
        is_active=True,
        is_superuser=False
    )
    
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    
    return user


@pytest_asyncio.fixture
async def superuser(async_session: AsyncSession) -> User:
    """Create a test superuser."""
    from app.auth.core.security import get_password_hash
    
    user = User(
        email="admin@example.com",
        full_name="Admin User",
        hashed_password=get_password_hash("adminpassword123"),
        is_active=True,
        is_superuser=True
    )
    
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    
    return user


@pytest_asyncio.fixture
async def test_organization(async_session: AsyncSession) -> Organization:
    """Create a test organization."""
    org = Organization(
        name="Test Organization",
        slug="test-org",
        description="A test organization"
    )
    
    async_session.add(org)
    await async_session.commit()
    await async_session.refresh(org)
    
    return org


@pytest_asyncio.fixture
async def test_organization_with_member(
    async_session: AsyncSession, 
    test_user: User, 
    test_organization: Organization
) -> tuple[Organization, OrganizationMember]:
    """Create an organization with a test user as member."""
    member = OrganizationMember(
        organization_id=test_organization.id,
        user_id=test_user.id,
        role=MemberRole.OWNER,
        status=MemberStatus.ACTIVE
    )
    
    async_session.add(member)
    await async_session.commit()
    await async_session.refresh(member)
    
    return test_organization, member


@pytest_asyncio.fixture
async def test_project(
    async_session: AsyncSession,
    test_user: User,
    test_organization: Organization
) -> Project:
    """Create a test project."""
    project = Project(
        user_id=test_user.id,
        organization_id=test_organization.id,
        name="Test Project",
        url="https://example.com",
        description="A test project"
    )
    
    async_session.add(project)
    await async_session.commit()
    await async_session.refresh(project)
    
    return project


# Authentication fixtures
@pytest_asyncio.fixture
async def auth_service(async_session: AsyncSession) -> AuthService:
    """Create auth service for testing."""
    return AuthService(async_session)


@pytest_asyncio.fixture
async def authenticated_user_token(
    async_session: AsyncSession,
    test_user: User,
    auth_service: AuthService
) -> str:
    """Create an authenticated user and return access token."""
    from app.auth.core.security import create_access_token
    from datetime import timedelta
    
    access_token = create_access_token(
        subject=str(test_user.id),
        expires_delta=timedelta(minutes=15)
    )
    
    return access_token


@pytest_asyncio.fixture
async def authenticated_headers(authenticated_user_token: str) -> dict[str, str]:
    """Create headers with authentication token."""
    return {"Authorization": f"Bearer {authenticated_user_token}"}


@pytest_asyncio.fixture
async def superuser_token(
    async_session: AsyncSession,
    superuser: User
) -> str:
    """Create a superuser token."""
    from app.auth.core.security import create_access_token
    from datetime import timedelta
    
    access_token = create_access_token(
        subject=str(superuser.id),
        expires_delta=timedelta(minutes=15)
    )
    
    return access_token


@pytest_asyncio.fixture
async def superuser_headers(superuser_token: str) -> dict[str, str]:
    """Create headers with superuser token."""
    return {"Authorization": f"Bearer {superuser_token}"}


# Mock external services
@pytest.fixture
def mock_openai_service():
    """Mock OpenAI service for testing."""
    from unittest.mock import Mock
    return Mock()


@pytest.fixture
def mock_google_services():
    """Mock Google services (GSC, GA4, etc.) for testing."""
    from unittest.mock import Mock
    return {
        "search_console": Mock(),
        "analytics": Mock(),
        "oauth": Mock()
    }


@pytest.fixture
def mock_serp_api():
    """Mock SERP API service for testing."""
    from unittest.mock import Mock
    return Mock()


# Factory fixtures for creating test data
class UserFactory:
    """Factory for creating test users."""
    
    @staticmethod
    async def create_user(
        session: AsyncSession,
        email: str = "factory@example.com",
        password: str = "password123",
        is_superuser: bool = False,
        is_active: bool = True
    ) -> User:
        from app.auth.core.security import get_password_hash
        
        user = User(
            email=email,
            full_name=f"User {email.split('@')[0]}",
            hashed_password=get_password_hash(password),
            is_active=is_active,
            is_superuser=is_superuser
        )
        
        session.add(user)
        await session.commit()
        await session.refresh(user)
        
        return user


class OrganizationFactory:
    """Factory for creating test organizations."""
    
    @staticmethod
    async def create_organization(
        session: AsyncSession,
        name: str = "Factory Organization",
        slug: str = "factory-org"
    ) -> Organization:
        org = Organization(
            name=name,
            slug=slug,
            description=f"Description for {name}"
        )
        
        session.add(org)
        await session.commit()
        await session.refresh(org)
        
        return org


class ProjectFactory:
    """Factory for creating test projects."""
    
    @staticmethod
    async def create_project(
        session: AsyncSession,
        user: User,
        organization: Organization,
        name: str = "Factory Project",
        url: str = "https://factory.example.com"
    ) -> Project:
        project = Project(
            user_id=user.id,
            organization_id=organization.id,
            name=name,
            url=url,
            description=f"Description for {name}"
        )
        
        session.add(project)
        await session.commit()
        await session.refresh(project)
        
        return project


@pytest.fixture
def user_factory() -> UserFactory:
    """User factory fixture."""
    return UserFactory()


@pytest.fixture
def organization_factory() -> OrganizationFactory:
    """Organization factory fixture."""
    return OrganizationFactory()


@pytest.fixture
def project_factory() -> ProjectFactory:
    """Project factory fixture."""
    return ProjectFactory()


# Event loop fixture for async tests
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# Pytest markers
pytest_plugins = ["pytest_asyncio"]
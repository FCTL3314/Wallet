from collections.abc import AsyncGenerator
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.database import Base, get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models import (
    Currency,
    ExpenseCategory,
    IncomeSource,
    StorageAccount,
    StorageLocation,
    User,
)

TEST_DB_NAME = "wallet_test"
_base_url = settings.DATABASE_URL.rsplit("/", 1)[0]
TEST_DB_URL = f"{_base_url}/{TEST_DB_NAME}"


@pytest.fixture(scope="session")
async def setup_test_db():
    """Create the test database, run create_all, yield, then drop it."""
    admin_engine = create_async_engine(
        _base_url + "/postgres", isolation_level="AUTOCOMMIT"
    )
    async with admin_engine.connect() as conn:
        await conn.execute(text(f"DROP DATABASE IF EXISTS {TEST_DB_NAME}"))
        await conn.execute(text(f"CREATE DATABASE {TEST_DB_NAME}"))
    await admin_engine.dispose()

    engine = create_async_engine(TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()

    yield

    admin_engine = create_async_engine(
        _base_url + "/postgres", isolation_level="AUTOCOMMIT"
    )
    async with admin_engine.connect() as conn:
        await conn.execute(text(f"DROP DATABASE IF EXISTS {TEST_DB_NAME}"))
    await admin_engine.dispose()


@pytest.fixture()
async def _test_engine(setup_test_db):
    engine = create_async_engine(TEST_DB_URL)
    yield engine
    await engine.dispose()


@pytest.fixture()
async def db_session(_test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Per-test session. We use begin/rollback for isolation."""
    conn = await _test_engine.connect()
    txn = await conn.begin()
    session_factory = async_sessionmaker(
        bind=conn, class_=AsyncSession, expire_on_commit=False
    )
    session = session_factory()

    yield session

    await session.close()
    await txn.rollback()
    await conn.close()


@pytest.fixture()
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """HTTPX async client with get_db overridden to use the test session."""

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture()
async def test_user(db_session: AsyncSession) -> User:
    user = User(email="test@wallet.app", password_hash=hash_password("Test1234"))
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture()
async def auth_client(client: AsyncClient, test_user: User) -> AsyncClient:
    token = create_access_token(test_user.id)
    client.headers["Authorization"] = f"Bearer {token}"
    return client


@pytest.fixture()
async def other_user(db_session: AsyncSession) -> User:
    user = User(email="other@wallet.app", password_hash=hash_password("Other1234"))
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture()
async def other_auth_client(
    client: AsyncClient, other_user: User, db_session: AsyncSession
) -> AsyncClient:
    """A second authenticated client for multi-tenancy tests."""

    async def _override() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override
    transport = ASGITransport(app=app)
    token = create_access_token(other_user.id)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as ac:
        yield ac


@pytest.fixture()
async def ref_data(db_session: AsyncSession, test_user: User) -> dict:
    """Create a standard set of reference data for the test user."""
    currency = Currency(code="USD", symbol="$", user_id=test_user.id)
    db_session.add(currency)
    await db_session.flush()

    location = StorageLocation(name="Bank", user_id=test_user.id)
    db_session.add(location)
    await db_session.flush()

    account = StorageAccount(
        storage_location_id=location.id,
        currency_id=currency.id,
        user_id=test_user.id,
    )
    db_session.add(account)
    await db_session.flush()

    income_source = IncomeSource(name="Salary", user_id=test_user.id)
    db_session.add(income_source)
    await db_session.flush()

    expense_category = ExpenseCategory(
        name="Food",
        budgeted_amount=Decimal("500.00"),
        user_id=test_user.id,
    )
    db_session.add(expense_category)
    await db_session.flush()

    return {
        "currency": currency,
        "location": location,
        "account": account,
        "income_source": income_source,
        "expense_category": expense_category,
    }

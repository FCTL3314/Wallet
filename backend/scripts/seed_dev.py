"""
Development seed script.
Creates a realistic dataset for local development.

Credentials: admin@admin.com / admin

Run from /backend:
    uv run python scripts/seed_dev.py
Or inside Docker:
    docker exec -it dev-backend-1 uv run python scripts/seed_dev.py
"""

import asyncio
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session
from app.core.security import hash_password
from app.models.balance_snapshot import BalanceSnapshot
from app.models.currency import Currency
from app.models.currency_catalog import CurrencyCatalog
from app.models.exchange_rate import ExchangeRate
from app.models.expense_category import ExpenseCategory
from app.models.income_source import IncomeSource
from app.models.storage import StorageAccount, StorageLocation
from app.models.transaction import Transaction, TransactionType
from app.models.user import User


# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------

CATALOG_CURRENCIES = [
    {"code": "USD", "symbol": "$", "name": "US Dollar", "currency_type": "fiat"},
    {"code": "EUR", "symbol": "€", "name": "Euro", "currency_type": "fiat"},
]

# (from_code, to_code, rate, source)  — valid_date set to date.today() at runtime
EXCHANGE_RATES = [
    ("EUR", "USD", Decimal("1.085000000000"), "seed"),
    ("GBP", "USD", Decimal("1.270000000000"), "seed"),
    ("CHF", "USD", Decimal("1.130000000000"), "seed"),
    ("JPY", "USD", Decimal("0.006700000000"), "seed"),
    ("BTC", "USD", Decimal("85000.000000000000"), "seed"),
    ("ETH", "USD", Decimal("2000.000000000000"), "seed"),
]

CURRENCIES = [
    {"code": "USD", "symbol": "$"},
    {"code": "EUR", "symbol": "€"},
]

STORAGE_LOCATIONS = [
    "Chase Bank",
    "Savings Account",
    "Cash",
]

# (location_name, currency_code)
STORAGE_ACCOUNTS = [
    ("Chase Bank", "USD"),
    ("Chase Bank", "EUR"),
    ("Savings Account", "USD"),
    ("Cash", "USD"),
]

INCOME_SOURCES = [
    "Employer",
    "Freelance",
    "Investments",
]

EXPENSE_CATEGORIES = [
    ("Housing", Decimal("1500.00")),
    ("Groceries", Decimal("500.00")),
    ("Transportation", Decimal("200.00")),
    ("Entertainment", Decimal("200.00")),
    ("Healthcare", Decimal("100.00")),
    ("Utilities", Decimal("150.00")),
    ("Dining Out", Decimal("150.00")),
    ("Clothing", Decimal("100.00")),
]

# ---------------------------------------------------------------------------
# Transactions: 6 months of income (Sep 2025 – Feb 2026)
# Each entry: (date, amount, currency_code, storage_account, income_source, description)
# ---------------------------------------------------------------------------

INCOME_TRANSACTIONS = [
    # ── September 2025 ──
    (
        date(2025, 9, 5),
        Decimal("4200.00"),
        "USD",
        ("Chase Bank", "USD"),
        "Employer",
        "Salary — September",
    ),
    (
        date(2025, 9, 15),
        Decimal("250.00"),
        "USD",
        ("Savings Account", "USD"),
        "Investments",
        "Q3 dividend payout",
    ),
    # ── October 2025 ──
    (
        date(2025, 10, 5),
        Decimal("4200.00"),
        "USD",
        ("Chase Bank", "USD"),
        "Employer",
        "Salary — October",
    ),
    (
        date(2025, 10, 22),
        Decimal("980.00"),
        "USD",
        ("Chase Bank", "USD"),
        "Freelance",
        "Website redesign — client Acme",
    ),
    # ── November 2025 ──
    (
        date(2025, 11, 5),
        Decimal("4200.00"),
        "USD",
        ("Chase Bank", "USD"),
        "Employer",
        "Salary — November",
    ),
    (
        date(2025, 11, 12),
        Decimal("1200.00"),
        "USD",
        ("Chase Bank", "USD"),
        "Freelance",
        "API integration — client BrightSoft",
    ),
    (
        date(2025, 11, 28),
        Decimal("500.00"),
        "EUR",
        ("Chase Bank", "EUR"),
        "Freelance",
        "UI audit — client EuroTech (EUR)",
    ),
    # ── December 2025 ──
    (
        date(2025, 12, 5),
        Decimal("4200.00"),
        "USD",
        ("Chase Bank", "USD"),
        "Employer",
        "Salary — December",
    ),
    (
        date(2025, 12, 10),
        Decimal("310.00"),
        "USD",
        ("Savings Account", "USD"),
        "Investments",
        "Q4 dividend payout",
    ),
    (
        date(2025, 12, 20),
        Decimal("800.00"),
        "USD",
        ("Cash", "USD"),
        "Freelance",
        "Small consulting gig (cash)",
    ),
    # ── January 2026 ──
    (
        date(2026, 1, 5),
        Decimal("4500.00"),
        "USD",
        ("Chase Bank", "USD"),
        "Employer",
        "Salary — January (raise)",
    ),
    (
        date(2026, 1, 19),
        Decimal("900.00"),
        "USD",
        ("Chase Bank", "USD"),
        "Freelance",
        "Mobile app screens — client NovaDev",
    ),
    # ── February 2026 ──
    (
        date(2026, 2, 5),
        Decimal("4500.00"),
        "USD",
        ("Chase Bank", "USD"),
        "Employer",
        "Salary — February",
    ),
    (
        date(2026, 2, 14),
        Decimal("1500.00"),
        "USD",
        ("Chase Bank", "USD"),
        "Freelance",
        "Full-stack MVP — client Startup X",
    ),
    (
        date(2026, 2, 27),
        Decimal("275.00"),
        "USD",
        ("Savings Account", "USD"),
        "Investments",
        "Q1 early dividend",
    ),
]

# ---------------------------------------------------------------------------
# Balance snapshots: end-of-month balances for each account
# (date, storage_account, currency_code, amount)
# ---------------------------------------------------------------------------

BALANCE_SNAPSHOTS = [
    # ── Aug 2025 (starting baseline) ──
    (date(2025, 8, 31), ("Chase Bank", "USD"), "USD", Decimal("11500.00")),
    (date(2025, 8, 31), ("Chase Bank", "EUR"), "EUR", Decimal("320.00")),
    (date(2025, 8, 31), ("Savings Account", "USD"), "USD", Decimal("8000.00")),
    (date(2025, 8, 31), ("Cash", "USD"), "USD", Decimal("380.00")),
    # ── Sep 2025 ──
    (date(2025, 9, 30), ("Chase Bank", "USD"), "USD", Decimal("14750.00")),
    (date(2025, 9, 30), ("Chase Bank", "EUR"), "EUR", Decimal("320.00")),
    (date(2025, 9, 30), ("Savings Account", "USD"), "USD", Decimal("8250.00")),
    (date(2025, 9, 30), ("Cash", "USD"), "USD", Decimal("420.00")),
    # ── Oct 2025 ──
    (date(2025, 10, 31), ("Chase Bank", "USD"), "USD", Decimal("18300.00")),
    (date(2025, 10, 31), ("Chase Bank", "EUR"), "EUR", Decimal("320.00")),
    (date(2025, 10, 31), ("Savings Account", "USD"), "USD", Decimal("8250.00")),
    (date(2025, 10, 31), ("Cash", "USD"), "USD", Decimal("390.00")),
    # ── Nov 2025 ──
    (date(2025, 11, 30), ("Chase Bank", "USD"), "USD", Decimal("22650.00")),
    (date(2025, 11, 30), ("Chase Bank", "EUR"), "EUR", Decimal("820.00")),
    (date(2025, 11, 30), ("Savings Account", "USD"), "USD", Decimal("8250.00")),
    (date(2025, 11, 30), ("Cash", "USD"), "USD", Decimal("350.00")),
    # ── Dec 2025 ──
    (date(2025, 12, 31), ("Chase Bank", "USD"), "USD", Decimal("26100.00")),
    (date(2025, 12, 31), ("Chase Bank", "EUR"), "EUR", Decimal("820.00")),
    (date(2025, 12, 31), ("Savings Account", "USD"), "USD", Decimal("8560.00")),
    (date(2025, 12, 31), ("Cash", "USD"), "USD", Decimal("1100.00")),
    # ── Jan 2026 ──
    (date(2026, 1, 31), ("Chase Bank", "USD"), "USD", Decimal("29900.00")),
    (date(2026, 1, 31), ("Chase Bank", "EUR"), "EUR", Decimal("820.00")),
    (date(2026, 1, 31), ("Savings Account", "USD"), "USD", Decimal("8560.00")),
    (date(2026, 1, 31), ("Cash", "USD"), "USD", Decimal("950.00")),
    # ── Feb 2026 ──
    (date(2026, 2, 28), ("Chase Bank", "USD"), "USD", Decimal("34700.00")),
    (date(2026, 2, 28), ("Chase Bank", "EUR"), "EUR", Decimal("820.00")),
    (date(2026, 2, 28), ("Savings Account", "USD"), "USD", Decimal("8835.00")),
    (date(2026, 2, 28), ("Cash", "USD"), "USD", Decimal("780.00")),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def get_or_create_user(db: AsyncSession) -> User:
    result = await db.execute(select(User).where(User.email == "admin@admin.com"))
    user = result.scalar_one_or_none()
    if user:
        print("  User already exists, skipping creation.")
        return user

    user = User(email="admin@admin.com", password_hash=hash_password("admin"))
    db.add(user)
    await db.flush()
    print(f"  Created user: admin@admin.com / admin  (id={user.id})")
    return user


async def seed_currency_catalog(db: AsyncSession) -> dict[str, CurrencyCatalog]:
    catalog: dict[str, CurrencyCatalog] = {}
    for data in CATALOG_CURRENCIES:
        result = await db.execute(
            select(CurrencyCatalog).where(CurrencyCatalog.code == data["code"])
        )
        obj = result.scalar_one_or_none()
        if not obj:
            obj = CurrencyCatalog(**data)
            db.add(obj)
            await db.flush()
        catalog[obj.code] = obj
    print(f"  Currency catalog: {list(catalog)}")
    return catalog


async def seed_exchange_rates(db: AsyncSession) -> None:
    today = date.today()
    for from_code, to_code, rate, source in EXCHANGE_RATES:
        result = await db.execute(
            select(ExchangeRate).where(
                ExchangeRate.from_code == from_code,
                ExchangeRate.to_code == to_code,
                ExchangeRate.valid_date == today,
            )
        )
        if result.scalar_one_or_none() is None:
            db.add(
                ExchangeRate(
                    from_code=from_code,
                    to_code=to_code,
                    rate=rate,
                    valid_date=today,
                    source=source,
                )
            )
            await db.flush()
    print(f"  Exchange rates: {len(EXCHANGE_RATES)}")


async def seed_currencies(
    db: AsyncSession, user: User, catalog: dict[str, CurrencyCatalog]
) -> dict[str, Currency]:
    currencies: dict[str, Currency] = {}
    for data in CURRENCIES:
        result = await db.execute(
            select(Currency).where(
                Currency.user_id == user.id, Currency.code == data["code"]
            )
        )
        obj = result.scalar_one_or_none()
        if not obj:
            catalog_entry = catalog.get(data["code"])
            obj = Currency(
                user_id=user.id,
                catalog_id=catalog_entry.id if catalog_entry else None,
                name=catalog_entry.name if catalog_entry else None,
                **data,
            )
            db.add(obj)
            await db.flush()
        currencies[obj.code] = obj
    print(f"  Currencies: {list(currencies)}")
    return currencies


async def seed_storage_locations(
    db: AsyncSession, user: User
) -> dict[str, StorageLocation]:
    locations: dict[str, StorageLocation] = {}
    for name in STORAGE_LOCATIONS:
        result = await db.execute(
            select(StorageLocation).where(
                StorageLocation.user_id == user.id, StorageLocation.name == name
            )
        )
        obj = result.scalar_one_or_none()
        if not obj:
            obj = StorageLocation(user_id=user.id, name=name)
            db.add(obj)
            await db.flush()
        locations[name] = obj
    print(f"  Storage locations: {list(locations)}")
    return locations


async def seed_storage_accounts(
    db: AsyncSession,
    user: User,
    locations: dict[str, StorageLocation],
    currencies: dict[str, Currency],
) -> dict[tuple[str, str], StorageAccount]:
    accounts: dict[tuple[str, str], StorageAccount] = {}
    for loc_name, cur_code in STORAGE_ACCOUNTS:
        loc = locations[loc_name]
        cur = currencies[cur_code]
        result = await db.execute(
            select(StorageAccount).where(
                StorageAccount.user_id == user.id,
                StorageAccount.storage_location_id == loc.id,
                StorageAccount.currency_id == cur.id,
            )
        )
        obj = result.scalar_one_or_none()
        if not obj:
            obj = StorageAccount(
                user_id=user.id,
                storage_location_id=loc.id,
                currency_id=cur.id,
            )
            db.add(obj)
            await db.flush()
        accounts[(loc_name, cur_code)] = obj
    print(f"  Storage accounts: {len(accounts)}")
    return accounts


async def seed_income_sources(db: AsyncSession, user: User) -> dict[str, IncomeSource]:
    sources: dict[str, IncomeSource] = {}
    for name in INCOME_SOURCES:
        result = await db.execute(
            select(IncomeSource).where(
                IncomeSource.user_id == user.id, IncomeSource.name == name
            )
        )
        obj = result.scalar_one_or_none()
        if not obj:
            obj = IncomeSource(user_id=user.id, name=name)
            db.add(obj)
            await db.flush()
        sources[name] = obj
    print(f"  Income sources: {list(sources)}")
    return sources


async def seed_expense_categories(
    db: AsyncSession, user: User
) -> dict[str, ExpenseCategory]:
    categories: dict[str, ExpenseCategory] = {}
    for name, budget in EXPENSE_CATEGORIES:
        result = await db.execute(
            select(ExpenseCategory).where(
                ExpenseCategory.user_id == user.id, ExpenseCategory.name == name
            )
        )
        obj = result.scalar_one_or_none()
        if not obj:
            obj = ExpenseCategory(
                user_id=user.id, name=name, budgeted_amount=budget, tags=[]
            )
            db.add(obj)
            await db.flush()
        categories[name] = obj
    print(f"  Expense categories: {list(categories)}")
    return categories


async def seed_transactions(
    db: AsyncSession,
    user: User,
    currencies: dict[str, Currency],
    accounts: dict[tuple[str, str], StorageAccount],
    sources: dict[str, IncomeSource],
) -> None:
    result = await db.execute(select(Transaction).where(Transaction.user_id == user.id))
    if result.scalars().first():
        print("  Transactions already exist, skipping.")
        return

    for tx_date, amount, cur_code, acc_key, src_name, desc in INCOME_TRANSACTIONS:
        db.add(
            Transaction(
                user_id=user.id,
                type=TransactionType.income,
                date=tx_date,
                amount=amount,
                description=desc,
                currency_id=currencies[cur_code].id,
                storage_account_id=accounts[acc_key].id,
                income_source_id=sources[src_name].id,
            )
        )
    await db.flush()
    print(f"  Transactions created: {len(INCOME_TRANSACTIONS)}")


async def seed_balance_snapshots(
    db: AsyncSession,
    user: User,
    currencies: dict[str, Currency],
    accounts: dict[tuple[str, str], StorageAccount],
) -> None:
    result = await db.execute(
        select(BalanceSnapshot).where(BalanceSnapshot.user_id == user.id)
    )
    if result.scalars().first():
        print("  Balance snapshots already exist, skipping.")
        return

    for snap_date, acc_key, _cur_code, amount in BALANCE_SNAPSHOTS:
        db.add(
            BalanceSnapshot(
                user_id=user.id,
                storage_account_id=accounts[acc_key].id,
                date=snap_date,
                amount=amount,
            )
        )
    await db.flush()
    print(f"  Balance snapshots created: {len(BALANCE_SNAPSHOTS)}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


async def main() -> None:
    print("Seeding development database...")
    async with async_session() as db:
        try:
            user = await get_or_create_user(db)
            catalog = await seed_currency_catalog(db)
            await seed_exchange_rates(db)
            currencies = await seed_currencies(db, user, catalog)
            locations = await seed_storage_locations(db, user)
            accounts = await seed_storage_accounts(db, user, locations, currencies)
            sources = await seed_income_sources(db, user)
            await seed_expense_categories(db, user)
            await seed_transactions(db, user, currencies, accounts, sources)
            await seed_balance_snapshots(db, user, currencies, accounts)
            await db.commit()
            print("\nDone. Login: admin@admin.com / admin")
        except Exception:
            await db.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(main())

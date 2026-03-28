from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.db_helpers import get_or_404
from app.core.dependencies import get_current_user
from app.core.exceptions import AppException, ResourceNotFound
from app.models import Currency, User
from app.models.currency_catalog import CurrencyCatalog
from app.models.exchange_rate import ExchangeRate
from app.schemas.currency import (
    CatalogCurrencyResponse,
    CurrencyCreate,
    CurrencyResponse,
    CurrencyUpdate,
)

router = APIRouter(prefix="/currencies", tags=["currencies"])


@router.get("/catalog", response_model=list[CatalogCurrencyResponse])
async def list_catalog_currencies(
    search: str | None = Query(default=None, max_length=50),
    limit: int = Query(default=50, ge=1, le=500),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all active currencies in the catalog with their rate availability."""
    q = select(CurrencyCatalog).where(CurrencyCatalog.is_active.is_(True))
    if search:
        term = search.strip().upper()
        q = q.where(
            CurrencyCatalog.code.like(f"{term}%")
            | CurrencyCatalog.name.ilike(f"%{search.strip()}%")
        )
    q = q.order_by(CurrencyCatalog.currency_type, CurrencyCatalog.code).limit(limit)
    result = await db.execute(q)
    catalog_entries = result.scalars().all()

    # Collect all codes that have at least one exchange rate row
    codes_with_rates_result = await db.execute(
        select(ExchangeRate.from_code).distinct()
    )
    codes_with_rates: set[str] = {row for row in codes_with_rates_result.scalars()}

    return [
        CatalogCurrencyResponse(
            id=entry.id,
            code=entry.code,
            symbol=entry.symbol,
            name=entry.name,
            currency_type=entry.currency_type,
            has_rates=entry.code in codes_with_rates,
        )
        for entry in catalog_entries
    ]


@router.get("/", response_model=list[CurrencyResponse])
async def list_currencies(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Currency).where(Currency.user_id == user.id))
    return result.scalars().all()


@router.post("/", response_model=CurrencyResponse, status_code=status.HTTP_201_CREATED)
async def create_currency(
    body: CurrencyCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a currency for the authenticated user.

    Supports two modes:
    - Catalog-linked: provide ``catalog_id`` — code/symbol/name are filled from the catalog entry.
    - Custom: provide ``code``, ``symbol``, and optionally ``name`` — catalog_id stays null.
    """
    if body.catalog_id is not None:
        # Catalog-linked mode: look up the catalog entry
        result = await db.execute(
            select(CurrencyCatalog).where(CurrencyCatalog.id == body.catalog_id)
        )
        catalog_entry = result.scalar_one_or_none()
        if catalog_entry is None:
            raise ResourceNotFound("currency_catalog")

        obj = Currency(
            code=catalog_entry.code,
            symbol=catalog_entry.symbol,
            name=catalog_entry.name,
            catalog_id=catalog_entry.id,
            user_id=user.id,
        )
    else:
        # Custom mode: require code and symbol
        if not body.code or not body.symbol:
            raise AppException(
                code="validation/invalid_input",
                message="Either catalog_id or both code and symbol must be provided",
                status_code=422,
            )
        obj = Currency(
            code=body.code,
            symbol=body.symbol,
            name=body.name,
            catalog_id=None,
            user_id=user.id,
        )

    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


@router.put("/{currency_id}", response_model=CurrencyResponse)
async def update_currency(
    currency_id: int,
    body: CurrencyUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    obj = await get_or_404(db, Currency, currency_id, user.id, "currency")
    changes = body.model_dump(exclude_unset=True)
    # Changing code or symbol diverges from the catalog entry — detach automatically
    if obj.catalog_id is not None and ("code" in changes or "symbol" in changes):
        obj.catalog_id = None
    for k, v in changes.items():
        setattr(obj, k, v)
    await db.flush()
    await db.refresh(obj)
    return obj


@router.delete("/{currency_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_currency(
    currency_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    obj = await get_or_404(db, Currency, currency_id, user.id, "currency")
    await db.delete(obj)

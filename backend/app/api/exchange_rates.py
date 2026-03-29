from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.db_helpers import get_or_404
from app.core.dependencies import get_current_user
from app.core.exceptions import ResourceNotFound
from app.models import Currency, User
from app.models.exchange_rate import ExchangeRate, UserExchangeRate
from app.schemas.exchange_rate import (
    RateInfoResponse,
    UserExchangeRateCreate,
    UserExchangeRateResponse,
)
from app.services.exchange_rates import get_rate, get_rates_batch

router = APIRouter(tags=["exchange-rates"])


@router.get("/currencies/rates/all", response_model=dict[int, RateInfoResponse])
async def get_all_currency_rates(
    to_code: str = Query(default="USD"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current exchange rates for all user currencies (to USD) in one call."""
    result = await db.execute(select(Currency).where(Currency.user_id == user.id))
    currencies = result.scalars().all()
    if not currencies:
        return {}

    codes = [c.code for c in currencies]
    rate_map = await get_rates_batch(db, codes, to_code=to_code, user_id=user.id)

    return {
        c.id: RateInfoResponse(
            status=rate_map[c.code].status,
            valid_date=rate_map[c.code].valid_date,
            source=rate_map[c.code].source,
            rate=rate_map[c.code].rate,
        )
        for c in currencies
        if c.code in rate_map
    }


@router.get(
    "/currencies/{currency_id}/rates",
    response_model=RateInfoResponse,
)
async def get_currency_rate(
    currency_id: int,
    at_date: date | None = Query(default=None),
    to_code: str = Query(default="USD"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current exchange rate for a user currency (to USD)."""
    currency = await get_or_404(db, Currency, currency_id, user.id, "currency")
    result = await get_rate(
        db,
        from_code=currency.code,
        to_code=to_code,
        at_date=at_date,
        user_id=user.id,
    )
    return RateInfoResponse(
        status=result.status,
        valid_date=result.valid_date,
        source=result.source,
        rate=result.rate,
    )


@router.get(
    "/currencies/{currency_id}/rates/history",
    response_model=list[RateInfoResponse],
)
async def get_currency_rate_history(
    currency_id: int,
    days: int = Query(default=30, ge=1, le=365),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get exchange rate history for a user currency (system rates only, to USD)."""
    currency = await get_or_404(db, Currency, currency_id, user.id, "currency")

    result = await db.execute(
        select(ExchangeRate)
        .where(ExchangeRate.from_code == currency.code, ExchangeRate.to_code == "USD")
        .order_by(ExchangeRate.valid_date.desc())
        .limit(days)
    )
    rows = result.scalars().all()

    return [
        RateInfoResponse(
            status="ok",
            valid_date=row.valid_date,
            source=row.source,
            rate=row.rate,
        )
        for row in rows
    ]


@router.post(
    "/currencies/{currency_id}/manual-rate",
    response_model=UserExchangeRateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_manual_rate(
    currency_id: int,
    body: UserExchangeRateCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a manual exchange rate for a user currency."""
    currency = await get_or_404(db, Currency, currency_id, user.id, "currency")

    obj = UserExchangeRate(
        user_id=user.id,
        from_code=currency.code,
        to_code=body.to_code,
        rate=body.rate,
        valid_from=body.valid_from,
        valid_to=body.valid_to,
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.get(
    "/currencies/{currency_id}/manual-rates",
    response_model=list[UserExchangeRateResponse],
)
async def list_manual_rates(
    currency_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List user manual exchange rates for a currency."""
    currency = await get_or_404(db, Currency, currency_id, user.id, "currency")

    result = await db.execute(
        select(UserExchangeRate)
        .where(
            UserExchangeRate.user_id == user.id,
            UserExchangeRate.from_code == currency.code,
        )
        .order_by(UserExchangeRate.valid_from.desc())
    )
    return result.scalars().all()


@router.delete(
    "/currencies/{currency_id}/manual-rates/{rate_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_manual_rate(
    currency_id: int,
    rate_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a user manual exchange rate."""
    currency = await get_or_404(db, Currency, currency_id, user.id, "currency")

    result = await db.execute(
        select(UserExchangeRate).where(
            UserExchangeRate.id == rate_id,
            UserExchangeRate.user_id == user.id,
            UserExchangeRate.from_code == currency.code,
        )
    )
    obj = result.scalar_one_or_none()
    if obj is None:
        raise ResourceNotFound("exchange_rate")
    await db.delete(obj)
    await db.commit()

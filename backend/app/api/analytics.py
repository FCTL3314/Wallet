from datetime import date

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import AppException
from app.models import Currency, User
from app.services.analytics import (
    GroupBy,
    explain_period,
    get_summary,
    get_income_by_source,
    get_balance_by_storage,
    get_expense_template,
    get_balance_breakdown,
    get_date_range,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


async def _resolve_convert_to(
    db: AsyncSession, user: User, convert_to: str | None, currency_id: int | None
) -> str | None:
    """Validate ``convert_to``, falling back to the user's base currency.

    Without a target currency a multi-currency user would get balances in
    different currencies added together into one meaningless number, so that
    combination is rejected rather than answered.
    """
    if currency_id is not None:
        return None

    codes_result = await db.execute(
        select(Currency.code).where(Currency.user_id == user.id)
    )
    valid_codes = set(codes_result.scalars())

    if convert_to is not None:
        if convert_to not in valid_codes:
            raise AppException(
                code="validation/invalid_input",
                message=f"Currency '{convert_to}' is not in your currencies",
                status_code=422,
            )
        return convert_to

    if user.base_currency_code in valid_codes:
        return user.base_currency_code

    if len(valid_codes) > 1:
        raise AppException(
            code="analytics/currency_required",
            message=(
                "Amounts are held in several currencies. Pass convert_to or "
                "currency_id, or set a base currency in your preferences."
            ),
            status_code=422,
        )

    return next(iter(valid_codes), None)


class BalanceBreakdownItem(BaseModel):
    account_id: int
    account_label: str
    currency: str
    latest_snapshot_date: date
    latest_snapshot_amount: float


@router.get("/summary")
async def summary(
    date_from: date = Query(...),
    date_to: date = Query(...),
    group_by: GroupBy = Query(default=GroupBy.month),
    currency_id: int | None = Query(default=None),
    convert_to: str | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    convert_to = await _resolve_convert_to(db, user, convert_to, currency_id)
    return await get_summary(
        db, user.id, date_from, date_to, group_by, currency_id, convert_to
    )


@router.get("/summary/explain")
async def summary_explain(
    period: date = Query(..., description="Start date of the period to explain"),
    group_by: GroupBy = Query(default=GroupBy.month),
    currency_id: int | None = Query(default=None),
    convert_to: str | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Break a single summary row down into the snapshots and transactions behind it."""
    convert_to = await _resolve_convert_to(db, user, convert_to, currency_id)
    return await explain_period(db, user.id, period, group_by, currency_id, convert_to)


@router.get("/income-by-source")
async def income_by_source(
    date_from: date = Query(...),
    date_to: date = Query(...),
    group_by: GroupBy = Query(default=GroupBy.month),
    currency_id: int | None = Query(default=None),
    convert_to: str | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    convert_to = await _resolve_convert_to(db, user, convert_to, currency_id)
    return await get_income_by_source(
        db, user.id, date_from, date_to, group_by, currency_id, convert_to
    )


@router.get("/balance-by-storage")
async def balance_by_storage(
    date_from: date = Query(...),
    date_to: date = Query(...),
    group_by: GroupBy = Query(default=GroupBy.month),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_balance_by_storage(db, user.id, date_from, date_to, group_by)


@router.get("/expense-template")
async def expense_template(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_expense_template(db, user.id)


@router.get("/balance-breakdown", response_model=list[BalanceBreakdownItem])
async def balance_breakdown(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the latest balance snapshot per storage account for the authenticated user."""
    return await get_balance_breakdown(db, user.id)


@router.get("/date-range")
async def date_range(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the earliest and latest dates across the user's transactions and balance snapshots."""
    return await get_date_range(db, user.id)

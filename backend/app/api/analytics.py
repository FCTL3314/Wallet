from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models import User
from app.services.analytics import (
    GroupBy,
    get_summary,
    get_income_by_source,
    get_balance_by_storage,
    get_expense_template,
    get_expense_vs_budget,
    get_balance_breakdown,
    get_date_range,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


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
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_summary(db, user.id, date_from, date_to, group_by, currency_id)


@router.get("/income-by-source")
async def income_by_source(
    date_from: date = Query(...),
    date_to: date = Query(...),
    group_by: GroupBy = Query(default=GroupBy.month),
    currency_id: int | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_income_by_source(db, user.id, date_from, date_to, group_by, currency_id)


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


@router.get("/expense-vs-budget")
async def expense_vs_budget(
    year: int | None = Query(default=None),
    month: int | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    return await get_expense_vs_budget(
        db,
        user.id,
        year if year is not None else now.year,
        month if month is not None else now.month,
    )


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

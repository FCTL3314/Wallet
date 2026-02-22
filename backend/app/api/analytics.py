from datetime import date

from fastapi import APIRouter, Depends, Query
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
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary")
async def summary(
    date_from: date = Query(...),
    date_to: date = Query(...),
    group_by: GroupBy = Query(default=GroupBy.month),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_summary(db, user.id, date_from, date_to, group_by)


@router.get("/income-by-source")
async def income_by_source(
    date_from: date = Query(...),
    date_to: date = Query(...),
    group_by: GroupBy = Query(default=GroupBy.month),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_income_by_source(db, user.id, date_from, date_to, group_by)


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

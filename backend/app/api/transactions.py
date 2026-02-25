from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.db_helpers import get_or_404
from app.core.dependencies import get_current_user
from app.core.exceptions import ResourceNotFound
from app.models import ExpenseCategory, IncomeSource, Transaction, User
from app.models.transaction import TransactionType
from app.schemas.transaction import (
    TransactionCreate,
    TransactionResponse,
    TransactionUpdate,
)

router = APIRouter(prefix="/transactions", tags=["transactions"])


async def _validate_fk_ownership(
    db: AsyncSession,
    user_id: int,
    income_source_id: int | None,
    expense_category_id: int | None,
) -> None:
    if income_source_id is not None:
        result = await db.execute(
            select(IncomeSource).where(
                IncomeSource.id == income_source_id, IncomeSource.user_id == user_id
            )
        )
        if not result.scalar_one_or_none():
            raise ResourceNotFound("income_source")
    if expense_category_id is not None:
        result = await db.execute(
            select(ExpenseCategory).where(
                ExpenseCategory.id == expense_category_id,
                ExpenseCategory.user_id == user_id,
            )
        )
        if not result.scalar_one_or_none():
            raise ResourceNotFound("expense_category")


@router.get("/", response_model=list[TransactionResponse])
async def list_transactions(
    tx_type: TransactionType | None = Query(default=None, alias="type"),
    date_from: date | None = None,
    date_to: date | None = None,
    income_source_id: int | None = None,
    expense_category_id: int | None = None,
    storage_account_id: int | None = None,
    limit: int = Query(default=100, le=1000),
    offset: int = 0,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = (
        select(Transaction)
        .where(Transaction.user_id == user.id)
        .order_by(Transaction.date.desc())
    )
    if tx_type:
        q = q.where(Transaction.type == tx_type)
    if date_from:
        q = q.where(Transaction.date >= date_from)
    if date_to:
        q = q.where(Transaction.date <= date_to)
    if income_source_id:
        q = q.where(Transaction.income_source_id == income_source_id)
    if expense_category_id:
        q = q.where(Transaction.expense_category_id == expense_category_id)
    if storage_account_id:
        q = q.where(Transaction.storage_account_id == storage_account_id)
    q = q.offset(offset).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


@router.post(
    "/", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED
)
async def create_transaction(
    body: TransactionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _validate_fk_ownership(
        db, user.id, body.income_source_id, body.expense_category_id
    )
    obj = Transaction(**body.model_dump(), user_id=user.id)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


@router.put("/{tx_id}", response_model=TransactionResponse)
async def update_transaction(
    tx_id: int,
    body: TransactionUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    obj = await get_or_404(db, Transaction, tx_id, user.id, "transaction")
    data = body.model_dump(exclude_unset=True)
    await _validate_fk_ownership(
        db, user.id, data.get("income_source_id"), data.get("expense_category_id")
    )
    for k, v in data.items():
        setattr(obj, k, v)
    await db.flush()
    await db.refresh(obj)
    return obj


@router.delete("/{tx_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    tx_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    obj = await get_or_404(db, Transaction, tx_id, user.id, "transaction")
    await db.delete(obj)

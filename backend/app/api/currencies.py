from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import ResourceNotFound
from app.models import User, Currency
from app.schemas.currency import CurrencyCreate, CurrencyUpdate, CurrencyResponse

router = APIRouter(prefix="/currencies", tags=["currencies"])


@router.get("/", response_model=list[CurrencyResponse])
async def list_currencies(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Currency).where(Currency.user_id == user.id))
    return result.scalars().all()


@router.post("/", response_model=CurrencyResponse, status_code=status.HTTP_201_CREATED)
async def create_currency(
    body: CurrencyCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    obj = Currency(**body.model_dump(), user_id=user.id)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


@router.put("/{currency_id}", response_model=CurrencyResponse)
async def update_currency(
    currency_id: int, body: CurrencyUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Currency).where(Currency.id == currency_id, Currency.user_id == user.id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise ResourceNotFound("currency")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await db.flush()
    await db.refresh(obj)
    return obj


@router.delete("/{currency_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_currency(
    currency_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Currency).where(Currency.id == currency_id, Currency.user_id == user.id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise ResourceNotFound("currency")
    await db.delete(obj)

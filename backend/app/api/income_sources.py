from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.db_helpers import get_or_404
from app.core.dependencies import get_current_user
from app.models import User, IncomeSource
from app.schemas.income_source import IncomeSourceCreate, IncomeSourceUpdate, IncomeSourceResponse

router = APIRouter(prefix="/income-sources", tags=["income-sources"])


@router.get("/", response_model=list[IncomeSourceResponse])
async def list_sources(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(IncomeSource).where(IncomeSource.user_id == user.id))
    return result.scalars().all()


@router.post("/", response_model=IncomeSourceResponse, status_code=status.HTTP_201_CREATED)
async def create_source(
    body: IncomeSourceCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    obj = IncomeSource(**body.model_dump(), user_id=user.id)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


@router.put("/{source_id}", response_model=IncomeSourceResponse)
async def update_source(
    source_id: int, body: IncomeSourceUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    obj = await get_or_404(db, IncomeSource, source_id, user.id, "income_source")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await db.flush()
    await db.refresh(obj)
    return obj


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_source(
    source_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    obj = await get_or_404(db, IncomeSource, source_id, user.id, "income_source")
    await db.delete(obj)

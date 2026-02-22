from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models import User, BalanceSnapshot
from app.schemas.balance_snapshot import BalanceSnapshotCreate, BalanceSnapshotUpdate, BalanceSnapshotResponse

router = APIRouter(prefix="/balance-snapshots", tags=["balance-snapshots"])


@router.get("/", response_model=list[BalanceSnapshotResponse])
async def list_snapshots(
    storage_account_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = Query(default=100, le=1000),
    offset: int = 0,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(BalanceSnapshot).where(BalanceSnapshot.user_id == user.id).order_by(BalanceSnapshot.date.desc())
    if storage_account_id:
        q = q.where(BalanceSnapshot.storage_account_id == storage_account_id)
    if date_from:
        q = q.where(BalanceSnapshot.date >= date_from)
    if date_to:
        q = q.where(BalanceSnapshot.date <= date_to)
    q = q.offset(offset).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


@router.post("/", response_model=BalanceSnapshotResponse, status_code=status.HTTP_201_CREATED)
async def create_snapshot(
    body: BalanceSnapshotCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    obj = BalanceSnapshot(**body.model_dump(), user_id=user.id)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


@router.put("/{snap_id}", response_model=BalanceSnapshotResponse)
async def update_snapshot(
    snap_id: int, body: BalanceSnapshotUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(BalanceSnapshot).where(BalanceSnapshot.id == snap_id, BalanceSnapshot.user_id == user.id)
    )
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Balance snapshot not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await db.flush()
    await db.refresh(obj)
    return obj


@router.delete("/{snap_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_snapshot(
    snap_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(BalanceSnapshot).where(BalanceSnapshot.id == snap_id, BalanceSnapshot.user_id == user.id)
    )
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Balance snapshot not found")
    await db.delete(obj)

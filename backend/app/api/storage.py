from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import ResourceNotFound
from app.models import User, StorageLocation, StorageAccount
from app.schemas.storage import (
    StorageLocationCreate,
    StorageLocationUpdate,
    StorageLocationResponse,
    StorageAccountCreate,
    StorageAccountResponse,
)

router = APIRouter(tags=["storage"])


# --- Storage Locations ---

@router.get("/storage-locations/", response_model=list[StorageLocationResponse])
async def list_locations(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(StorageLocation).where(StorageLocation.user_id == user.id))
    return result.scalars().all()


@router.post("/storage-locations/", response_model=StorageLocationResponse, status_code=status.HTTP_201_CREATED)
async def create_location(
    body: StorageLocationCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    obj = StorageLocation(**body.model_dump(), user_id=user.id)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


@router.put("/storage-locations/{loc_id}", response_model=StorageLocationResponse)
async def update_location(
    loc_id: int, body: StorageLocationUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(StorageLocation).where(StorageLocation.id == loc_id, StorageLocation.user_id == user.id)
    )
    obj = result.scalar_one_or_none()
    if not obj:
        raise ResourceNotFound("storage_location")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await db.flush()
    await db.refresh(obj)
    return obj


@router.delete("/storage-locations/{loc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_location(
    loc_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(StorageLocation).where(StorageLocation.id == loc_id, StorageLocation.user_id == user.id)
    )
    obj = result.scalar_one_or_none()
    if not obj:
        raise ResourceNotFound("storage_location")
    await db.delete(obj)


# --- Storage Accounts ---

@router.get("/storage-accounts/", response_model=list[StorageAccountResponse])
async def list_accounts(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(StorageAccount)
        .where(StorageAccount.user_id == user.id)
        .options(selectinload(StorageAccount.storage_location), selectinload(StorageAccount.currency))
    )
    return result.scalars().all()


@router.post("/storage-accounts/", response_model=StorageAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    body: StorageAccountCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    obj = StorageAccount(**body.model_dump(), user_id=user.id)
    db.add(obj)
    await db.flush()
    await db.refresh(obj, attribute_names=["storage_location", "currency"])
    return obj


@router.delete("/storage-accounts/{acc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    acc_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(StorageAccount).where(StorageAccount.id == acc_id, StorageAccount.user_id == user.id)
    )
    obj = result.scalar_one_or_none()
    if not obj:
        raise ResourceNotFound("storage_account")
    await db.delete(obj)

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.db_helpers import get_or_404
from app.core.dependencies import get_current_user
from app.models import User, ExpenseCategory
from app.schemas.expense_category import ExpenseCategoryCreate, ExpenseCategoryUpdate, ExpenseCategoryResponse

router = APIRouter(prefix="/expense-categories", tags=["expense-categories"])


@router.get("/", response_model=list[ExpenseCategoryResponse])
async def list_categories(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ExpenseCategory).where(ExpenseCategory.user_id == user.id))
    return result.scalars().all()


@router.post("/", response_model=ExpenseCategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    body: ExpenseCategoryCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    obj = ExpenseCategory(**body.model_dump(), user_id=user.id)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


@router.put("/{cat_id}", response_model=ExpenseCategoryResponse)
async def update_category(
    cat_id: int, body: ExpenseCategoryUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    obj = await get_or_404(db, ExpenseCategory, cat_id, user.id, "expense_category")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await db.flush()
    await db.refresh(obj)
    return obj


@router.delete("/{cat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    cat_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    obj = await get_or_404(db, ExpenseCategory, cat_id, user.id, "expense_category")
    await db.delete(obj)

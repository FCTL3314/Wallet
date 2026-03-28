from app.api._crud import build_crud_router
from app.models import ExpenseCategory
from app.schemas.expense_category import (
    ExpenseCategoryCreate,
    ExpenseCategoryResponse,
    ExpenseCategoryUpdate,
)

router = build_crud_router(
    model=ExpenseCategory,
    create_schema=ExpenseCategoryCreate,
    update_schema=ExpenseCategoryUpdate,
    response_schema=ExpenseCategoryResponse,
    prefix="/expense-categories",
    tags=["expense-categories"],
    resource_name="expense_category",
    id_param="category_id",
)

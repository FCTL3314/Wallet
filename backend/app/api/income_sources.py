from app.api._crud import build_crud_router
from app.models import IncomeSource
from app.schemas.income_source import (
    IncomeSourceCreate,
    IncomeSourceResponse,
    IncomeSourceUpdate,
)

router = build_crud_router(
    model=IncomeSource,
    create_schema=IncomeSourceCreate,
    update_schema=IncomeSourceUpdate,
    response_schema=IncomeSourceResponse,
    prefix="/income-sources",
    tags=["income-sources"],
    resource_name="income_source",
    id_param="income_source_id",
)

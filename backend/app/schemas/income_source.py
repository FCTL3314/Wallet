from pydantic import BaseModel


class IncomeSourceCreate(BaseModel):
    name: str


class IncomeSourceUpdate(BaseModel):
    name: str | None = None


class IncomeSourceResponse(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}

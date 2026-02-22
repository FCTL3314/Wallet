from pydantic import BaseModel


class CurrencyCreate(BaseModel):
    code: str
    symbol: str


class CurrencyUpdate(BaseModel):
    code: str | None = None
    symbol: str | None = None


class CurrencyResponse(BaseModel):
    id: int
    code: str
    symbol: str

    model_config = {"from_attributes": True}

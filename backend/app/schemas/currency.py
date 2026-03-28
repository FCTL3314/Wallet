from pydantic import BaseModel, field_validator


class CurrencyCreate(BaseModel):
    # Option 1: link to catalog entry (code/symbol/name filled automatically)
    catalog_id: int | None = None
    # Option 2: custom currency (catalog_id stays null)
    code: str | None = None
    symbol: str | None = None
    name: str | None = None

    @field_validator("code", mode="before")
    @classmethod
    def normalize_code(cls, v: str | None) -> str | None:
        return v.strip().upper() if v else v


class CurrencyUpdate(BaseModel):
    code: str | None = None
    symbol: str | None = None
    name: str | None = None

    @field_validator("code", mode="before")
    @classmethod
    def normalize_code(cls, v: str | None) -> str | None:
        return v.strip().upper() if v else v


class CurrencyResponse(BaseModel):
    id: int
    code: str
    symbol: str
    name: str | None
    catalog_id: int | None
    is_custom: bool

    model_config = {"from_attributes": True}


class CatalogCurrencyResponse(BaseModel):
    id: int
    code: str
    symbol: str
    name: str
    currency_type: str  # "fiat" | "crypto"
    has_rates: bool

    model_config = {"from_attributes": True}

from pydantic import BaseModel


class StorageLocationCreate(BaseModel):
    name: str


class StorageLocationUpdate(BaseModel):
    name: str | None = None


class StorageLocationResponse(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class StorageAccountCreate(BaseModel):
    storage_location_id: int
    currency_id: int


class StorageAccountUpdate(BaseModel):
    storage_location_id: int | None = None


class StorageAccountResponse(BaseModel):
    id: int
    storage_location_id: int
    currency_id: int
    storage_location: StorageLocationResponse | None = None
    currency: "CurrencyResponse | None" = None

    model_config = {"from_attributes": True}


from app.schemas.currency import CurrencyResponse  # noqa: E402

StorageAccountResponse.model_rebuild()

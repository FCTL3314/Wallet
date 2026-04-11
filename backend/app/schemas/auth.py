from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, computed_field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    created_at: datetime
    onboarding_completed_at: datetime | None = Field(None, exclude=True)
    base_currency_code: str | None = None

    model_config = {"from_attributes": True}

    @computed_field
    @property
    def onboarding_completed(self) -> bool:
        return self.onboarding_completed_at is not None


class UpdatePreferencesRequest(BaseModel):
    base_currency_code: str | None = None


class ChangeEmailRequest(BaseModel):
    current_password: str
    new_email: EmailStr


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

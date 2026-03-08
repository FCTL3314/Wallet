from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, computed_field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: int
    email: str
    created_at: datetime
    onboarding_completed_at: datetime | None = Field(None, exclude=True)

    model_config = {"from_attributes": True}

    @computed_field
    @property
    def onboarding_completed(self) -> bool:
        return self.onboarding_completed_at is not None


class ChangeEmailRequest(BaseModel):
    current_password: str
    new_email: EmailStr


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

from typing import Optional
from pydantic import BaseModel


class ErrorResponse(BaseModel):
    code: str
    message: str
    detail: Optional[str] = None


class AppException(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        detail: Optional[str] = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.detail = detail
        super().__init__(message)


class AuthInvalidCredentials(AppException):
    def __init__(self, detail: Optional[str] = None):
        super().__init__(
            code="auth/invalid_credentials",
            message="Invalid email or password",
            status_code=401,
            detail=detail,
        )


class AuthInvalidToken(AppException):
    def __init__(self, detail: Optional[str] = None):
        super().__init__(
            code="auth/invalid_token",
            message="Your session has expired. Please log in again",
            status_code=401,
            detail=detail,
        )


class AuthUserNotFound(AppException):
    def __init__(self, detail: Optional[str] = None):
        super().__init__(
            code="auth/user_not_found",
            message="Account not found",
            status_code=401,
            detail=detail,
        )


class AuthInvalidRefreshToken(AppException):
    def __init__(self, detail: Optional[str] = None):
        super().__init__(
            code="auth/invalid_refresh_token",
            message="Invalid or expired refresh token",
            status_code=401,
            detail=detail,
        )


class AuthEmailTaken(AppException):
    def __init__(self, detail: Optional[str] = None):
        super().__init__(
            code="auth/email_taken",
            message="This email is already registered",
            status_code=400,
            detail=detail,
        )


class ResourceNotFound(AppException):
    def __init__(self, resource_type: str = "item", detail: Optional[str] = None):
        friendly_name = resource_type.replace("_", " ").capitalize()
        super().__init__(
            code=f"resource/{resource_type}_not_found",
            message=f"{friendly_name} not found",
            status_code=404,
            detail=detail,
        )

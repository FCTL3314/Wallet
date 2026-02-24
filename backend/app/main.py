from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.api import auth, currencies, storage, income_sources, expense_categories, transactions, balance_snapshots, analytics
from app.core.config import settings
from app.core.exceptions import AppException, ErrorResponse

app = FastAPI(title=settings.PROJECT_NAME)

if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            code=exc.code,
            message=exc.message,
            detail=exc.detail,
        ).model_dump(exclude_none=True),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    first_error = errors[0] if errors else {}
    field = ".".join(str(loc) for loc in first_error.get("loc", [])[1:])

    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            code="validation/invalid_input",
            message=f"Invalid value for '{field}'" if field else "Please check your input",
        ).model_dump(exclude_none=True),
    )


for router in [
    auth.router,
    currencies.router,
    storage.router,
    income_sources.router,
    expense_categories.router,
    transactions.router,
    balance_snapshots.router,
    analytics.router,
]:
    app.include_router(router, prefix=settings.API_PREFIX)


@app.get("/api/health")
async def health():
    return {"status": "ok"}

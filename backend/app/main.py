import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin import setup_admin
from app.api import (
    analytics,
    auth,
    balance_snapshots,
    currencies,
    exchange_rates,
    expense_categories,
    income_sources,
    oauth,
    reports,
    storage,
    transactions,
)
from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import AppException, ErrorResponse
from app.core.redis import close_redis, init_redis
from app.kafka import consumers  # noqa: F401 — registers @broker.subscriber handlers
from app.kafka.broker import broker

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_redis()
    await broker.start()
    yield
    await broker.close()
    await close_redis()


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.exception_handler(AppException)
async def app_exception_handler(_: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            code=exc.code,
            message=exc.message,
            detail=exc.detail,
        ).model_dump(exclude_none=True),
    )


@app.exception_handler(IntegrityError)
async def integrity_error_handler(_: Request, exc: IntegrityError):
    return JSONResponse(
        status_code=409,
        content=ErrorResponse(
            code="resource/conflict",
            message="A resource with these details already exists",
        ).model_dump(exclude_none=True),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError):
    errors = exc.errors()
    first_error = errors[0] if errors else {}
    field = ".".join(str(loc) for loc in first_error.get("loc", [])[1:])

    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            code="validation/invalid_input",
            message=f"Invalid value for '{field}'"
            if field
            else "Please check your input",
        ).model_dump(exclude_none=True),
    )


for router in [
    auth.router,
    oauth.router,
    currencies.router,
    exchange_rates.router,
    storage.router,
    income_sources.router,
    expense_categories.router,
    transactions.router,
    balance_snapshots.router,
    analytics.router,
    reports.router,
]:
    app.include_router(router, prefix=settings.API_PREFIX)


@app.get("/api/health")
async def health(db: AsyncSession = Depends(get_db)):
    await db.execute(text("SELECT 1"))
    return {"status": "ok"}


setup_admin(app)

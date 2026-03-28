import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import (
    analytics,
    auth,
    balance_snapshots,
    currencies,
    exchange_rates,
    expense_categories,
    income_sources,
    oauth,
    storage,
    transactions,
)
from app.celery_app import celery_app
from app.core.config import settings
from app.core.database import async_session, get_db
from app.core.exceptions import AppException, ErrorResponse
from app.models.app_state import AppState
from app.models.currency_catalog import CurrencyCatalog

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """On first startup after migration, queue catalog and rate sync tasks.
    Self-healing: if catalog is empty (tasks failed previously), re-queues on restart.
    """
    async with async_session() as db:
        state = await AppState.load(db)
        catalog_count = await db.scalar(select(func.count(CurrencyCatalog.id))) or 0
        if not state.catalog_initial_sync_done or catalog_count == 0:
            celery_app.send_task("app.tasks.catalog_sync.sync_fiat_catalog")
            celery_app.send_task(
                "app.tasks.catalog_sync.sync_crypto_catalog", countdown=10
            )
            celery_app.send_task("app.tasks.rate_sync.refresh_fiat_rates", countdown=90)
            celery_app.send_task(
                "app.tasks.rate_sync.refresh_crypto_rates", countdown=120
            )
            celery_app.send_task(
                "app.tasks.rate_sync.backfill_fiat_rates", countdown=150
            )
            state.catalog_initial_sync_done = True
            await db.commit()
            logger.info(
                "Initial catalog and rate sync tasks queued (catalog_count=%d)",
                catalog_count,
            )
    yield


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
]:
    app.include_router(router, prefix=settings.API_PREFIX)


@app.get("/api/health")
async def health(db: AsyncSession = Depends(get_db)):
    await db.execute(text("SELECT 1"))
    return {"status": "ok"}

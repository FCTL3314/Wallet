from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, currencies, storage, income_sources, expense_categories, transactions, balance_snapshots, analytics
from app.core.config import settings

app = FastAPI(title=settings.PROJECT_NAME)

if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
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

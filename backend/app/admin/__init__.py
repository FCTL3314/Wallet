from fastapi import FastAPI
from sqladmin import Admin

from app.admin.auth import AdminAuth
from app.admin.views import (
    BalanceSnapshotAdmin,
    CatalogSyncHistoryAdmin,
    CurrencyAdmin,
    CurrencyCatalogAdmin,
    ExchangeRateAdmin,
    ExpenseCategoryAdmin,
    IncomeSourceAdmin,
    RefreshTokenAdmin,
    StorageAccountAdmin,
    StorageLocationAdmin,
    TransactionAdmin,
    UserAdmin,
    UserExchangeRateAdmin,
)
from app.core.config import settings
from app.core.database import engine


def setup_admin(app: FastAPI) -> None:
    authentication_backend = AdminAuth(secret_key=settings.ADMIN_SECRET_KEY)
    admin = Admin(
        app,
        engine,
        authentication_backend=authentication_backend,
        title="Wallet Admin",
        base_url="/admin",
    )
    for view in [
        UserAdmin,
        TransactionAdmin,
        ExpenseCategoryAdmin,
        IncomeSourceAdmin,
        CurrencyAdmin,
        StorageLocationAdmin,
        StorageAccountAdmin,
        BalanceSnapshotAdmin,
        RefreshTokenAdmin,
        CurrencyCatalogAdmin,
        CatalogSyncHistoryAdmin,
        ExchangeRateAdmin,
        UserExchangeRateAdmin,
    ]:
        admin.add_view(view)

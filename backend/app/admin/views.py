from sqladmin import ModelView

from app.models.balance_snapshot import BalanceSnapshot
from app.models.currency import Currency
from app.models.currency_catalog import CatalogSyncHistory, CurrencyCatalog
from app.models.exchange_rate import ExchangeRate, UserExchangeRate
from app.models.expense_category import ExpenseCategory
from app.models.income_source import IncomeSource
from app.models.refresh_token import RefreshToken
from app.models.storage import StorageAccount, StorageLocation
from app.models.transaction import Transaction
from app.models.user import User


class UserAdmin(ModelView, model=User):
    name = "User"
    name_plural = "Users"
    icon = "fa-solid fa-user"

    can_create = True
    can_edit = True
    can_delete = True

    column_list = [
        User.id,
        User.email,
        User.github_id,
        User.google_sub,
        User.base_currency_code,
        User.created_at,
        User.onboarding_completed_at,
    ]
    form_columns = [
        User.email,
        User.github_id,
        User.google_sub,
        User.base_currency_code,
        User.onboarding_completed_at,
    ]


class TransactionAdmin(ModelView, model=Transaction):
    name = "Transaction"
    name_plural = "Transactions"
    icon = "fa-solid fa-arrow-right-arrow-left"

    can_create = False
    can_edit = True
    can_delete = True

    column_list = [
        Transaction.id,
        Transaction.user_id,
        Transaction.type,
        Transaction.date,
        Transaction.amount,
        Transaction.description,
        Transaction.currency_id,
        Transaction.storage_account_id,
        Transaction.income_source_id,
        Transaction.expense_category_id,
    ]
    form_columns = [
        Transaction.date,
        Transaction.amount,
        Transaction.description,
        Transaction.currency_id,
        Transaction.storage_account_id,
        Transaction.income_source_id,
        Transaction.expense_category_id,
    ]


class ExpenseCategoryAdmin(ModelView, model=ExpenseCategory):
    name = "Expense Category"
    name_plural = "Expense Categories"
    icon = "fa-solid fa-tags"

    can_create = True
    can_edit = True
    can_delete = True

    column_list = [
        ExpenseCategory.id,
        ExpenseCategory.name,
        ExpenseCategory.budgeted_amount,
        ExpenseCategory.tags,
        ExpenseCategory.user_id,
    ]
    form_columns = [
        ExpenseCategory.name,
        ExpenseCategory.budgeted_amount,
        ExpenseCategory.tags,
        ExpenseCategory.user_id,
    ]


class IncomeSourceAdmin(ModelView, model=IncomeSource):
    name = "Income Source"
    name_plural = "Income Sources"
    icon = "fa-solid fa-sack-dollar"

    can_create = True
    can_edit = True
    can_delete = True

    column_list = [
        IncomeSource.id,
        IncomeSource.name,
        IncomeSource.user_id,
    ]
    form_columns = [
        IncomeSource.name,
        IncomeSource.user_id,
    ]


class CurrencyAdmin(ModelView, model=Currency):
    name = "Currency"
    name_plural = "Currencies"
    icon = "fa-solid fa-coins"

    can_create = True
    can_edit = True
    can_delete = True

    column_list = [
        Currency.id,
        Currency.code,
        Currency.symbol,
        Currency.name,
        Currency.catalog_id,
        Currency.user_id,
    ]
    form_columns = [
        Currency.code,
        Currency.symbol,
        Currency.name,
        Currency.catalog_id,
        Currency.user_id,
    ]


class StorageLocationAdmin(ModelView, model=StorageLocation):
    name = "Storage Location"
    name_plural = "Storage Locations"
    icon = "fa-solid fa-building-columns"

    can_create = True
    can_edit = True
    can_delete = True

    column_list = [
        StorageLocation.id,
        StorageLocation.name,
        StorageLocation.user_id,
    ]
    form_columns = [
        StorageLocation.name,
        StorageLocation.user_id,
    ]


class StorageAccountAdmin(ModelView, model=StorageAccount):
    name = "Storage Account"
    name_plural = "Storage Accounts"
    icon = "fa-solid fa-wallet"

    can_create = False
    can_edit = True
    can_delete = True

    column_list = [
        StorageAccount.id,
        StorageAccount.storage_location_id,
        StorageAccount.currency_id,
        StorageAccount.user_id,
    ]
    form_columns = [
        StorageAccount.storage_location_id,
        StorageAccount.user_id,
    ]


class BalanceSnapshotAdmin(ModelView, model=BalanceSnapshot):
    name = "Balance Snapshot"
    name_plural = "Balance Snapshots"
    icon = "fa-solid fa-camera"

    can_create = True
    can_edit = True
    can_delete = True

    column_list = [
        BalanceSnapshot.id,
        BalanceSnapshot.user_id,
        BalanceSnapshot.storage_account_id,
        BalanceSnapshot.date,
        BalanceSnapshot.amount,
    ]
    form_columns = [
        BalanceSnapshot.user_id,
        BalanceSnapshot.storage_account_id,
        BalanceSnapshot.date,
        BalanceSnapshot.amount,
    ]


class RefreshTokenAdmin(ModelView, model=RefreshToken):
    name = "Refresh Token"
    name_plural = "Refresh Tokens"
    icon = "fa-solid fa-key"

    can_create = False
    can_edit = False
    can_delete = False

    column_list = [
        RefreshToken.id,
        RefreshToken.user_id,
        RefreshToken.token_hash,
        RefreshToken.expires_at,
        RefreshToken.revoked,
        RefreshToken.created_at,
    ]


class CurrencyCatalogAdmin(ModelView, model=CurrencyCatalog):
    name = "Currency Catalog"
    name_plural = "Currency Catalog"
    icon = "fa-solid fa-book"

    can_create = True
    can_edit = True
    can_delete = False

    column_list = [
        CurrencyCatalog.id,
        CurrencyCatalog.code,
        CurrencyCatalog.symbol,
        CurrencyCatalog.name,
        CurrencyCatalog.currency_type,
        CurrencyCatalog.coingecko_id,
        CurrencyCatalog.is_active,
        CurrencyCatalog.created_at,
        CurrencyCatalog.updated_at,
    ]
    form_columns = [
        CurrencyCatalog.symbol,
        CurrencyCatalog.name,
        CurrencyCatalog.currency_type,
        CurrencyCatalog.coingecko_id,
        CurrencyCatalog.is_active,
    ]


class CatalogSyncHistoryAdmin(ModelView, model=CatalogSyncHistory):
    name = "Catalog Sync History"
    name_plural = "Catalog Sync History"
    icon = "fa-solid fa-rotate"

    can_create = False
    can_edit = False
    can_delete = False

    column_list = [
        CatalogSyncHistory.id,
        CatalogSyncHistory.source,
        CatalogSyncHistory.synced_at,
        CatalogSyncHistory.entries_upserted,
        CatalogSyncHistory.success,
        CatalogSyncHistory.error,
    ]


class ExchangeRateAdmin(ModelView, model=ExchangeRate):
    name = "Exchange Rate"
    name_plural = "Exchange Rates"
    icon = "fa-solid fa-chart-line"

    can_create = False
    can_edit = False
    can_delete = False

    column_list = [
        ExchangeRate.id,
        ExchangeRate.from_code,
        ExchangeRate.to_code,
        ExchangeRate.rate,
        ExchangeRate.valid_date,
        ExchangeRate.source,
        ExchangeRate.fetched_at,
    ]


class UserExchangeRateAdmin(ModelView, model=UserExchangeRate):
    name = "User Exchange Rate"
    name_plural = "User Exchange Rates"
    icon = "fa-solid fa-sliders"

    can_create = True
    can_edit = True
    can_delete = True

    column_list = [
        UserExchangeRate.id,
        UserExchangeRate.user_id,
        UserExchangeRate.from_code,
        UserExchangeRate.to_code,
        UserExchangeRate.rate,
        UserExchangeRate.valid_from,
        UserExchangeRate.valid_to,
    ]
    form_columns = [
        UserExchangeRate.user_id,
        UserExchangeRate.from_code,
        UserExchangeRate.to_code,
        UserExchangeRate.rate,
        UserExchangeRate.valid_from,
        UserExchangeRate.valid_to,
    ]

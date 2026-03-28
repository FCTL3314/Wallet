import asyncio
import json
import logging
import math
from datetime import datetime, timezone

import httpx
from babel.numbers import get_currency_symbol
from celery import shared_task
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.currency_catalog import CatalogSyncHistory, CurrencyCatalog
from app.tasks._engine import get_engine
from app.tasks._http import NonRetryableHTTPError, RateLimitError, check_response

logger = logging.getLogger(__name__)

_COINGECKO_MAX_PER_PAGE = 250


async def _link_currencies_to_catalog(db: AsyncSession) -> int:
    """Match existing user currencies to catalog entries by code and set catalog_id.

    Runs within the caller's transaction — no commit here.
    Returns the number of rows updated.
    """
    result = await db.execute(
        text("""
            UPDATE currencies
            SET catalog_id = cc.id,
                code       = cc.code,
                name       = COALESCE(currencies.name, cc.name)
            FROM currency_catalog cc
            WHERE UPPER(currencies.code) = cc.code
              AND currencies.catalog_id IS NULL
        """)
    )
    return result.rowcount


async def _log_sync(
    db: AsyncSession,
    source: str,
    entries_upserted: int,
    success: bool,
    error: str | None = None,
) -> None:
    """Add a sync history entry to the session. Caller is responsible for commit."""
    entry = CatalogSyncHistory(
        source=source,
        synced_at=datetime.now(timezone.utc),
        entries_upserted=entries_upserted,
        success=success,
        error=error,
    )
    db.add(entry)


async def _try_log_failure(source: str, error: str) -> None:
    """Best-effort failure log — never raises."""
    try:
        engine = get_engine()
        async with AsyncSession(engine) as db:
            await _log_sync(db, source, 0, False, error[:500])
            await db.commit()
    except Exception:
        logger.error("Could not write sync failure log for %s", source)


@shared_task(
    bind=True,
    autoretry_for=(httpx.TransportError, httpx.HTTPStatusError),
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=120,
    queue="catalog",
    name="app.tasks.catalog_sync.sync_fiat_catalog",
)
def sync_fiat_catalog(self):
    try:
        asyncio.run(_async_sync_fiat_catalog())
    except RateLimitError as exc:
        logger.warning(
            "Fiat catalog sync rate limited; retrying in %ds", exc.retry_after
        )
        raise self.retry(countdown=exc.retry_after, exc=exc)
    except NonRetryableHTTPError as exc:
        logger.error("Fiat catalog sync non-retryable HTTP error: %s", exc)
    except httpx.TransportError:
        raise  # autoretry_for handles connection-level errors
    except Exception:
        logger.exception("Unexpected error in fiat catalog sync")


async def _async_sync_fiat_catalog() -> None:
    source = "exchangerate-api"
    if not settings.EXCHANGERATE_API_KEY:
        await _try_log_failure(source, "EXCHANGERATE_API_KEY not configured")
        raise RuntimeError(
            "EXCHANGERATE_API_KEY not configured — set this env var to enable fiat sync"
        )
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"https://v6.exchangerate-api.com/v6/{settings.EXCHANGERATE_API_KEY}/codes"
        )
        check_response(resp)
        try:
            data = resp.json()
        except (ValueError, json.JSONDecodeError):
            raise RuntimeError(
                f"ExchangeRate-API returned non-JSON response: {resp.text[:200]}"
            )

    if data.get("result") != "success":
        raise RuntimeError(
            f"ExchangeRate-API error: {data.get('error-type', 'unknown')}"
        )

    currencies = data.get("supported_codes")
    if not isinstance(currencies, list):
        raise RuntimeError(
            "ExchangeRate-API: unexpected response shape, missing supported_codes"
        )

    rows = []
    for entry in currencies:
        if not isinstance(entry, (list, tuple)) or len(entry) < 2:
            continue
        code, name = entry[0], entry[1]
        if not code or not isinstance(code, str):
            continue
        name = name or code
        try:
            symbol = get_currency_symbol(code, locale="en_US")
        except Exception:
            symbol = code
        rows.append(
            {
                "code": code,
                "symbol": symbol,
                "name": name,
                "currency_type": "fiat",
                "coingecko_id": None,
                "is_active": True,
            }
        )

    if not rows:
        logger.warning(
            "Fiat catalog sync: API returned 0 valid currencies, skipping DB write"
        )
        return

    engine = get_engine()
    async with AsyncSession(engine) as db:
        try:
            stmt = pg_insert(CurrencyCatalog).values(rows)
            stmt = stmt.on_conflict_do_update(
                index_elements=["code"],
                set_={
                    "symbol": stmt.excluded.symbol,
                    "name": stmt.excluded.name,
                    "is_active": True,
                    "updated_at": text("now()"),
                },
            )
            await db.execute(stmt)
            linked = await _link_currencies_to_catalog(db)
            await _log_sync(db, source, len(rows), True)
            await db.commit()
            logger.info(
                "Fiat catalog sync: upserted %d currencies, linked %d user currencies",
                len(rows),
                linked,
            )
        except Exception as exc:
            await db.rollback()
            await _try_log_failure(source, str(exc))
            raise


@shared_task(
    bind=True,
    autoretry_for=(httpx.TransportError, httpx.HTTPStatusError),
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=120,
    queue="catalog",
    name="app.tasks.catalog_sync.sync_crypto_catalog",
)
def sync_crypto_catalog(self):
    try:
        asyncio.run(_async_sync_crypto_catalog())
    except RateLimitError as exc:
        logger.warning(
            "Crypto catalog sync rate limited; retrying in %ds", exc.retry_after
        )
        raise self.retry(countdown=exc.retry_after, exc=exc)
    except NonRetryableHTTPError as exc:
        logger.error("Crypto catalog sync non-retryable HTTP error: %s", exc)
    except httpx.TransportError:
        raise  # autoretry_for handles connection-level errors
    except Exception:
        logger.exception("Unexpected error in crypto catalog sync")


async def _async_sync_crypto_catalog() -> None:
    source = "coingecko"
    headers: dict[str, str] = {}
    if settings.COINGECKO_API_KEY:
        headers["x-cg-demo-api-key"] = settings.COINGECKO_API_KEY

    total_pages = math.ceil(settings.CRYPTO_CATALOG_SIZE / _COINGECKO_MAX_PER_PAGE)
    # Sleep between pages: free tier ~5-15 req/min; demo tier ~30 req/min
    inter_page_sleep = 5 if settings.COINGECKO_API_KEY else 15

    coins: list[dict] = []
    async with httpx.AsyncClient(timeout=30, headers=headers) as client:
        for page in range(1, total_pages + 1):
            if page > 1:
                await asyncio.sleep(inter_page_sleep)
            resp = await client.get(
                "https://api.coingecko.com/api/v3/coins/markets",
                params={
                    "vs_currency": "usd",
                    "order": "market_cap_desc",
                    "per_page": _COINGECKO_MAX_PER_PAGE,
                    "page": page,
                    "sparkline": "false",
                },
            )
            check_response(resp)
            try:
                page_coins = resp.json()
            except (ValueError, json.JSONDecodeError):
                logger.warning(
                    "CoinGecko page %d returned non-JSON, stopping pagination", page
                )
                break
            if not isinstance(page_coins, list):
                logger.warning(
                    "CoinGecko page %d unexpected response shape, stopping", page
                )
                break
            coins.extend(page_coins)
            if len(page_coins) < _COINGECKO_MAX_PER_PAGE:
                break

    seen: set[str] = set()
    rows = []
    for coin in coins:
        if not isinstance(coin, dict):
            continue
        symbol = coin.get("symbol")
        name = coin.get("name")
        coingecko_id = coin.get("id")
        if not symbol or not name or not coingecko_id:
            continue
        code = symbol.upper()
        if not code or code in seen:
            continue
        seen.add(code)
        rows.append(
            {
                "code": code,
                "symbol": code,
                "name": name,
                "currency_type": "crypto",
                "coingecko_id": coingecko_id,
                "is_active": True,
            }
        )

    if not rows:
        logger.warning(
            "Crypto catalog sync: 0 valid coins after parsing, skipping DB write"
        )
        return

    engine = get_engine()
    async with AsyncSession(engine) as db:
        try:
            stmt = pg_insert(CurrencyCatalog).values(rows)
            stmt = stmt.on_conflict_do_update(
                index_elements=["code"],
                set_={
                    "symbol": stmt.excluded.symbol,
                    "name": stmt.excluded.name,
                    "currency_type": stmt.excluded.currency_type,
                    "coingecko_id": stmt.excluded.coingecko_id,
                    "is_active": True,
                    "updated_at": text("now()"),
                },
                # Never overwrite a fiat entry with crypto data — fiat takes precedence
                where=CurrencyCatalog.currency_type == "crypto",
            )
            await db.execute(stmt)
            linked = await _link_currencies_to_catalog(db)
            await _log_sync(db, source, len(rows), True)
            await db.commit()
            logger.info(
                "Crypto catalog sync: upserted %d coins, linked %d user currencies",
                len(rows),
                linked,
            )
        except Exception as exc:
            await db.rollback()
            await _try_log_failure(source, str(exc))
            raise

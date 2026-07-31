import asyncio
import json
import logging
import math
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

import httpx
from celery import shared_task
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.exchange_rate import ExchangeRate
from app.tasks._engine import get_engine
from app.tasks._http import NonRetryableHTTPError, RateLimitError, check_response

logger = logging.getLogger(__name__)

_COINGECKO_MAX_PER_PAGE = 250

# Matches the scale of ExchangeRate.rate — Numeric(28, 12).
_RATE_QUANTUM = Decimal("1E-12")


@shared_task(
    bind=True,
    autoretry_for=(httpx.TransportError, httpx.HTTPStatusError),
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=120,
    queue="rates",
    name="app.tasks.rate_sync.refresh_fiat_rates",
)
def refresh_fiat_rates(self):
    try:
        asyncio.run(_async_refresh_fiat_rates())
    except RateLimitError as exc:
        logger.warning("Fiat rate sync rate limited; retrying in %ds", exc.retry_after)
        raise self.retry(countdown=exc.retry_after, exc=exc)
    except NonRetryableHTTPError as exc:
        logger.error("Fiat rate sync non-retryable HTTP error: %s", exc)
    except httpx.TransportError:
        raise  # autoretry_for handles connection-level errors
    except Exception:
        logger.exception("Unexpected error in fiat rate sync")


async def _async_refresh_fiat_rates() -> None:
    if not settings.EXCHANGERATE_API_KEY:
        raise RuntimeError(
            "EXCHANGERATE_API_KEY not configured — set this env var to enable fiat rate sync"
        )

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"https://v6.exchangerate-api.com/v6/{settings.EXCHANGERATE_API_KEY}/latest/USD"
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

    rates = data.get("conversion_rates")
    if not isinstance(rates, dict):
        raise RuntimeError(
            "ExchangeRate-API: unexpected response shape, missing conversion_rates"
        )

    today = datetime.now(timezone.utc).date()
    source = "exchangerate-api"

    rows = []
    for code, rate_value in rates.items():
        if not code or code == "USD":
            continue
        if not isinstance(rate_value, (int, float)) or rate_value <= 0:
            logger.debug("Skipping invalid rate for %s: %r", code, rate_value)
            continue
        # Invert with Decimal: the API gives USD->code and we store code->USD.
        # A binary float reciprocal would bake in rounding error that then
        # compounds when two stored rates are divided to form a cross-rate.
        try:
            inverted = Decimal("1") / Decimal(str(rate_value))
        except (InvalidOperation, ZeroDivisionError):
            logger.debug("Skipping uninvertible rate for %s: %r", code, rate_value)
            continue
        # The rate column is Numeric(28, 12); anything smaller would be stored
        # as 0 and later divided by when building cross-rates.
        if inverted.quantize(_RATE_QUANTUM) == 0:
            logger.warning(
                "Skipping rate for %s: 1/%r underflows the stored precision",
                code,
                rate_value,
            )
            continue
        rows.append(
            {
                "from_code": code,
                "to_code": "USD",
                "rate": str(inverted),
                "valid_date": today,
                "source": source,
                "fetched_at": datetime.now(timezone.utc),
            }
        )

    if not rows:
        logger.warning("Fiat rate sync: 0 valid rates parsed, skipping DB write")
        return

    engine = get_engine()
    async with AsyncSession(engine) as db:
        try:
            stmt = pg_insert(ExchangeRate).values(rows)
            stmt = stmt.on_conflict_do_update(
                index_elements=["from_code", "to_code", "valid_date"],
                set_={
                    "rate": stmt.excluded.rate,
                    "source": stmt.excluded.source,
                    "fetched_at": stmt.excluded.fetched_at,
                },
            )
            await db.execute(stmt)
            await db.commit()
            logger.info("Fiat rates sync: upserted %d rates for %s", len(rows), today)
        except Exception:
            await db.rollback()
            logger.exception("Fiat rate sync: DB write failed")
            raise


@shared_task(
    bind=True,
    autoretry_for=(httpx.TransportError, httpx.HTTPStatusError),
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=120,
    queue="rates",
    name="app.tasks.rate_sync.refresh_crypto_rates",
)
def refresh_crypto_rates(self):
    try:
        asyncio.run(_async_refresh_crypto_rates())
    except RateLimitError as exc:
        logger.warning(
            "Crypto rate sync rate limited; retrying in %ds", exc.retry_after
        )
        raise self.retry(countdown=exc.retry_after, exc=exc)
    except NonRetryableHTTPError as exc:
        logger.error("Crypto rate sync non-retryable HTTP error: %s", exc)
    except httpx.TransportError:
        raise  # autoretry_for handles connection-level errors
    except Exception:
        logger.exception("Unexpected error in crypto rate sync")


async def _async_refresh_crypto_rates() -> None:
    headers: dict[str, str] = {}
    if settings.COINGECKO_API_KEY:
        headers["x-cg-demo-api-key"] = settings.COINGECKO_API_KEY

    total_pages = math.ceil(settings.CRYPTO_CATALOG_SIZE / _COINGECKO_MAX_PER_PAGE)
    # Sleep between pages: free tier ~5-15 req/min; demo tier ~30 req/min
    inter_page_sleep = 5 if settings.COINGECKO_API_KEY else 15

    today = datetime.now(timezone.utc).date()
    source = "coingecko"

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
        if not symbol:
            continue
        code = symbol.upper()
        if not code or code in seen:
            continue
        price_usd = coin.get("current_price")
        if not isinstance(price_usd, (int, float)) or price_usd <= 0:
            continue
        # Sub-picodollar tokens would be stored as 0 by Numeric(28, 12) and then
        # divided by when building cross-rates.
        try:
            price = Decimal(str(price_usd))
        except InvalidOperation:
            continue
        if price.quantize(_RATE_QUANTUM) == 0:
            logger.debug(
                "Skipping %s: price %r underflows the stored precision", code, price_usd
            )
            continue
        seen.add(code)
        rows.append(
            {
                "from_code": code,
                "to_code": "USD",
                "rate": str(price),
                "valid_date": today,
                "source": source,
                "fetched_at": datetime.now(timezone.utc),
            }
        )

    if not rows:
        logger.warning("Crypto rate sync: 0 valid rates parsed, skipping DB write")
        return

    engine = get_engine()
    async with AsyncSession(engine) as db:
        try:
            stmt = pg_insert(ExchangeRate).values(rows)
            stmt = stmt.on_conflict_do_update(
                index_elements=["from_code", "to_code", "valid_date"],
                set_={
                    "rate": stmt.excluded.rate,
                    "source": stmt.excluded.source,
                    "fetched_at": stmt.excluded.fetched_at,
                },
            )
            await db.execute(stmt)
            await db.commit()
            logger.info("Crypto rates sync: upserted %d rates for %s", len(rows), today)
        except Exception:
            await db.rollback()
            logger.exception("Crypto rate sync: DB write failed")
            raise


@shared_task(
    queue="rates",
    name="app.tasks.rate_sync.prune_exchange_rates",
)
def prune_exchange_rates():
    """Downsample exchange rates older than the retention window."""
    return asyncio.run(_async_prune_exchange_rates())


async def _async_prune_exchange_rates() -> int:
    """Keep one row per (from_code, to_code) per month beyond the retention window.

    The table grows by ~160 fiat + up to CRYPTO_CATALOG_SIZE crypto rows every day
    and nothing ever removed them. Rates cannot simply be deleted by age, because
    historical conversion looks up the newest rate at or before each period end.
    Keeping the last row of each calendar month preserves that lookup exactly —
    every period end is a month end — while bounding the table's growth.
    """
    cutoff = datetime.now(timezone.utc).date() - timedelta(
        days=settings.EXCHANGE_RATE_RETENTION_DAYS
    )

    ranked = (
        select(
            ExchangeRate.id.label("id"),
            func.row_number()
            .over(
                partition_by=(
                    ExchangeRate.from_code,
                    ExchangeRate.to_code,
                    func.date_trunc("month", ExchangeRate.valid_date),
                ),
                order_by=(ExchangeRate.valid_date.desc(), ExchangeRate.id.desc()),
            )
            .label("rn"),
        )
        .where(ExchangeRate.valid_date < cutoff)
        .subquery()
    )
    doomed = select(ranked.c.id).where(ranked.c.rn > 1)

    engine = get_engine()
    async with AsyncSession(engine) as db:
        try:
            result = await db.execute(
                delete(ExchangeRate).where(ExchangeRate.id.in_(doomed))
            )
            await db.commit()
            deleted = result.rowcount or 0
            logger.info(
                "Exchange rate pruning: deleted %d rows older than %s", deleted, cutoff
            )
            return deleted
        except Exception:
            await db.rollback()
            logger.exception("Exchange rate pruning: DB write failed")
            raise

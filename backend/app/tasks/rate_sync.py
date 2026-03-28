import asyncio
import calendar
import json
import logging
import math
from datetime import date, datetime, timezone

import httpx
from celery import shared_task
from sqlalchemy import func, literal_column, select, union_all
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import BalanceSnapshot, Transaction
from app.models.app_state import AppState
from app.models.exchange_rate import ExchangeRate
from app.tasks._engine import get_engine
from app.tasks._http import NonRetryableHTTPError, RateLimitError, check_response

logger = logging.getLogger(__name__)

_COINGECKO_MAX_PER_PAGE = 250


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
        rows.append(
            {
                "from_code": code,
                "to_code": "USD",
                "rate": str(1.0 / rate_value),
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
        seen.add(code)
        rows.append(
            {
                "from_code": code,
                "to_code": "USD",
                "rate": str(price_usd),
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
    bind=True,
    autoretry_for=(httpx.TransportError, httpx.HTTPStatusError),
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=120,
    queue="rates",
    name="app.tasks.rate_sync.backfill_fiat_rates",
)
def backfill_fiat_rates(self):
    try:
        asyncio.run(_async_backfill_fiat_rates())
    except RateLimitError as exc:
        logger.warning("Fiat backfill rate limited; retrying in %ds", exc.retry_after)
        raise self.retry(countdown=exc.retry_after, exc=exc)
    except NonRetryableHTTPError as exc:
        logger.error("Fiat backfill non-retryable HTTP error: %s", exc)
    except httpx.TransportError:
        raise
    except Exception:
        logger.exception("Unexpected error in fiat rate backfill")


async def _async_backfill_fiat_rates() -> None:
    if not settings.EXCHANGERATE_API_KEY:
        raise RuntimeError(
            "EXCHANGERATE_API_KEY not configured — set this env var to enable fiat backfill"
        )

    engine = get_engine()
    async with AsyncSession(engine) as db:
        state = await AppState.load(db)
        if state.rates_backfill_done:
            logger.info("Fiat rate backfill already done, skipping")
            return

        min_tx = select(func.min(Transaction.date).label("min_date"))
        min_snap = select(func.min(BalanceSnapshot.date).label("min_date"))
        min_date_result = await db.execute(
            select(func.min(literal_column("min_date"))).select_from(
                union_all(min_tx, min_snap).subquery()
            )
        )
        min_date = min_date_result.scalar_one_or_none()

    if min_date is None:
        logger.info("No transactions or snapshots found, skipping rate backfill")
        async with AsyncSession(engine) as db:
            state = await AppState.load(db)
            state.rates_backfill_done = True
            await db.commit()
        return

    today = datetime.now(timezone.utc).date()
    months_to_fetch: list[date] = []
    cur = date(min_date.year, min_date.month, 1)
    while cur <= today:
        last_day = calendar.monthrange(cur.year, cur.month)[1]
        eom = date(
            cur.year,
            cur.month,
            min(
                last_day,
                today.day
                if cur.year == today.year and cur.month == today.month
                else last_day,
            ),
        )
        months_to_fetch.append(eom)
        if cur.month == 12:
            cur = date(cur.year + 1, 1, 1)
        else:
            cur = date(cur.year, cur.month + 1, 1)

    source = "exchangerate-api"
    total_upserted = 0

    async with httpx.AsyncClient(timeout=30) as client:
        for target_date in months_to_fetch:
            async with AsyncSession(engine) as db:
                existing = await db.scalar(
                    select(func.count(ExchangeRate.id)).where(
                        ExchangeRate.valid_date == target_date,
                        ExchangeRate.source == source,
                    )
                )
            if existing and existing > 0:
                logger.debug("Rates for %s already exist, skipping", target_date)
                continue

            url = (
                f"https://v6.exchangerate-api.com/v6/{settings.EXCHANGERATE_API_KEY}"
                f"/history/USD/{target_date.year}/{target_date.month}/{target_date.day}"
            )
            resp = await client.get(url)
            check_response(resp)
            try:
                data = resp.json()
            except (ValueError, json.JSONDecodeError):
                logger.warning(
                    "ExchangeRate-API non-JSON response for %s, skipping", target_date
                )
                continue

            if data.get("result") != "success":
                logger.warning(
                    "ExchangeRate-API error for %s: %s",
                    target_date,
                    data.get("error-type"),
                )
                continue

            rates = data.get("conversion_rates")
            if not isinstance(rates, dict):
                continue

            rows = []
            for code, rate_value in rates.items():
                if not code or code == "USD":
                    continue
                if not isinstance(rate_value, (int, float)) or rate_value <= 0:
                    continue
                rows.append(
                    {
                        "from_code": code,
                        "to_code": "USD",
                        "rate": str(1.0 / rate_value),
                        "valid_date": target_date,
                        "source": source,
                        "fetched_at": datetime.now(timezone.utc),
                    }
                )

            if rows:
                async with AsyncSession(engine) as db:
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
                    total_upserted += len(rows)
                    logger.info("Backfilled %d rates for %s", len(rows), target_date)

            await asyncio.sleep(1.5)  # rate limit: ~40 req/min on free tier

    async with AsyncSession(engine) as db:
        state = await AppState.load(db)
        state.rates_backfill_done = True
        await db.commit()

    logger.info(
        "Fiat rate backfill complete: %d total rates upserted across %d months",
        total_upserted,
        len(months_to_fetch),
    )

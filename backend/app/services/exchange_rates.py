from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.models.exchange_rate import ExchangeRate, UserExchangeRate


@dataclass
class RateResult:
    rate: Decimal | None
    source: (
        str  # "user_manual" | "exchangerate-api" | "coingecko" | "identity" | "none"
    )
    valid_date: date | None
    status: str  # "ok" | "stale" | "missing"


async def get_rate(
    db: AsyncSession,
    from_code: str,
    to_code: str = "USD",
    at_date: date | None = None,
    user_id: int | None = None,
) -> RateResult:
    """Resolve a single exchange rate, checking user manual rates first."""
    if at_date is None:
        at_date = date.today()

    if from_code == to_code:
        return RateResult(
            rate=Decimal("1"), source="identity", valid_date=at_date, status="ok"
        )

    # Check user manual rates first
    if user_id is not None:
        stmt = (
            select(UserExchangeRate)
            .where(
                UserExchangeRate.user_id == user_id,
                UserExchangeRate.from_code == from_code,
                UserExchangeRate.to_code == to_code,
                UserExchangeRate.valid_from <= at_date,
                (UserExchangeRate.valid_to >= at_date)
                | (UserExchangeRate.valid_to.is_(None)),
            )
            .order_by(UserExchangeRate.valid_from.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        user_rate = result.scalar_one_or_none()
        if user_rate is not None:
            return RateResult(
                rate=user_rate.rate,
                source="user_manual",
                valid_date=user_rate.valid_from,
                status="ok",
            )

    # Check system exchange rates
    stmt = (
        select(ExchangeRate)
        .where(
            ExchangeRate.from_code == from_code,
            ExchangeRate.to_code == to_code,
            ExchangeRate.valid_date <= at_date,
        )
        .order_by(ExchangeRate.valid_date.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    sys_rate = result.scalar_one_or_none()

    if sys_rate is None:
        # Cross-rate fallback via USD: A → B = (A → USD) / (B → USD)
        if to_code != "USD":
            stmt_from = (
                select(ExchangeRate)
                .where(
                    ExchangeRate.from_code == from_code,
                    ExchangeRate.to_code == "USD",
                    ExchangeRate.valid_date <= at_date,
                )
                .order_by(ExchangeRate.valid_date.desc())
                .limit(1)
            )
            result_from = await db.execute(stmt_from)
            from_usd = result_from.scalar_one_or_none()

            stmt_base = (
                select(ExchangeRate)
                .where(
                    ExchangeRate.from_code == to_code,
                    ExchangeRate.to_code == "USD",
                    ExchangeRate.valid_date <= at_date,
                )
                .order_by(ExchangeRate.valid_date.desc())
                .limit(1)
            )
            result_base = await db.execute(stmt_base)
            base_usd = result_base.scalar_one_or_none()

            if from_usd is not None and base_usd is not None:
                cross_valid_date = min(from_usd.valid_date, base_usd.valid_date)
                stale_threshold = at_date - timedelta(
                    days=settings.EXCHANGE_RATE_STALENESS_DAYS
                )
                cross_status = "ok" if cross_valid_date >= stale_threshold else "stale"
                return RateResult(
                    rate=from_usd.rate / base_usd.rate,
                    source=from_usd.source,
                    valid_date=cross_valid_date,
                    status=cross_status,
                )

        return RateResult(rate=None, source="none", valid_date=None, status="missing")

    stale_threshold = at_date - timedelta(days=settings.EXCHANGE_RATE_STALENESS_DAYS)
    status = "ok" if sys_rate.valid_date >= stale_threshold else "stale"
    return RateResult(
        rate=sys_rate.rate,
        source=sys_rate.source,
        valid_date=sys_rate.valid_date,
        status=status,
    )


async def get_rates_batch(
    db: AsyncSession,
    codes: list[str],
    to_code: str = "USD",
    at_date: date | None = None,
    user_id: int | None = None,
) -> dict[str, RateResult]:
    """Resolve exchange rates for multiple currency codes in a single batch."""
    if at_date is None:
        at_date = date.today()

    results: dict[str, RateResult] = {}
    remaining_codes: list[str] = []

    for code in codes:
        if code == to_code:
            results[code] = RateResult(
                rate=Decimal("1"), source="identity", valid_date=at_date, status="ok"
            )
        else:
            remaining_codes.append(code)

    if not remaining_codes:
        return results

    # Batch fetch user manual rates
    user_rate_map: dict[str, UserExchangeRate] = {}
    if user_id is not None:
        stmt = (
            select(UserExchangeRate)
            .where(
                UserExchangeRate.user_id == user_id,
                UserExchangeRate.from_code.in_(remaining_codes),
                UserExchangeRate.to_code == to_code,
                UserExchangeRate.valid_from <= at_date,
                (UserExchangeRate.valid_to >= at_date)
                | (UserExchangeRate.valid_to.is_(None)),
            )
            .order_by(UserExchangeRate.from_code, UserExchangeRate.valid_from.desc())
        )
        result = await db.execute(stmt)
        for row in result.scalars():
            if row.from_code not in user_rate_map:
                user_rate_map[row.from_code] = row

    # Batch fetch system rates (latest per code) for codes not covered by user rates
    sys_rate_map: dict[str, dict] = {}
    not_in_user = [c for c in remaining_codes if c not in user_rate_map]
    if not_in_user:
        stmt = text("""
            SELECT DISTINCT ON (from_code) *
            FROM exchange_rates
            WHERE from_code = ANY(:codes)
              AND to_code = :to_code
              AND valid_date <= :at_date
            ORDER BY from_code, valid_date DESC
        """)
        result = await db.execute(
            stmt, {"codes": not_in_user, "to_code": to_code, "at_date": at_date}
        )
        for row in result.mappings():
            sys_rate_map[row["from_code"]] = dict(row)

    stale_threshold = at_date - timedelta(days=settings.EXCHANGE_RATE_STALENESS_DAYS)

    # Identify codes still missing after user + system rate lookups
    cross_needed = [
        c for c in remaining_codes if c not in user_rate_map and c not in sys_rate_map
    ]

    # Cross-rate fallback via USD when to_code != "USD"
    cross_usd_map: dict[str, dict] = {}
    base_usd_row: dict | None = None
    if cross_needed and to_code != "USD":
        # Fetch from_code → USD for all still-missing codes
        stmt = text("""
            SELECT DISTINCT ON (from_code) *
            FROM exchange_rates
            WHERE from_code = ANY(:codes)
              AND to_code = 'USD'
              AND valid_date <= :at_date
            ORDER BY from_code, valid_date DESC
        """)
        result = await db.execute(stmt, {"codes": cross_needed, "at_date": at_date})
        for row in result.mappings():
            cross_usd_map[row["from_code"]] = dict(row)

        # Fetch to_code → USD (the base conversion rate)
        stmt = text("""
            SELECT *
            FROM exchange_rates
            WHERE from_code = :to_code
              AND to_code = 'USD'
              AND valid_date <= :at_date
            ORDER BY valid_date DESC
            LIMIT 1
        """)
        result = await db.execute(stmt, {"to_code": to_code, "at_date": at_date})
        row = result.mappings().first()
        if row is not None:
            base_usd_row = dict(row)

    for code in remaining_codes:
        if code in user_rate_map:
            ur = user_rate_map[code]
            results[code] = RateResult(
                rate=ur.rate,
                source="user_manual",
                valid_date=ur.valid_from,
                status="ok",
            )
        elif code in sys_rate_map:
            sr = sys_rate_map[code]
            valid_date = sr["valid_date"]
            status = "ok" if valid_date >= stale_threshold else "stale"
            results[code] = RateResult(
                rate=sr["rate"],
                source=sr["source"],
                valid_date=valid_date,
                status=status,
            )
        elif code in cross_usd_map and base_usd_row is not None:
            from_usd = cross_usd_map[code]
            cross_valid_date = min(from_usd["valid_date"], base_usd_row["valid_date"])
            cross_status = "ok" if cross_valid_date >= stale_threshold else "stale"
            results[code] = RateResult(
                rate=Decimal(str(from_usd["rate"]))
                / Decimal(str(base_usd_row["rate"])),
                source=from_usd["source"],
                valid_date=cross_valid_date,
                status=cross_status,
            )
        else:
            results[code] = RateResult(
                rate=None, source="none", valid_date=None, status="missing"
            )

    return results


async def get_rates_for_periods(
    db: AsyncSession,
    codes: list[str],
    period_ends: list[date],
    to_code: str = "USD",
    user_id: int | None = None,
) -> dict[date, dict[str, RateResult]]:
    """Fetch exchange rates for multiple period-end dates in 2 queries instead of N.

    Returns {period_end: {code: RateResult}}.
    """
    if not codes or not period_ends:
        return {}

    max_date = max(period_ends)
    non_base = [c for c in codes if c != to_code]

    # User manual rates — single query covering all periods
    user_rate_map: dict[str, list[UserExchangeRate]] = {}
    if user_id is not None and non_base:
        stmt = (
            select(UserExchangeRate)
            .where(
                UserExchangeRate.user_id == user_id,
                UserExchangeRate.from_code.in_(non_base),
                UserExchangeRate.to_code == to_code,
                UserExchangeRate.valid_from <= max_date,
            )
            .order_by(UserExchangeRate.from_code, UserExchangeRate.valid_from.desc())
        )
        result = await db.execute(stmt)
        for row in result.scalars():
            user_rate_map.setdefault(row.from_code, []).append(row)

    # System rates — single query, all rows up to max_date, sorted newest first
    sys_rate_map: dict[str, list[dict]] = {}
    if non_base:
        stmt = text("""
            SELECT from_code, rate, valid_date, source
            FROM exchange_rates
            WHERE from_code = ANY(:codes)
              AND to_code = :to_code
              AND valid_date <= :max_date
            ORDER BY from_code, valid_date DESC
        """)
        result = await db.execute(
            stmt, {"codes": non_base, "to_code": to_code, "max_date": max_date}
        )
        for row in result.mappings():
            sys_rate_map.setdefault(row["from_code"], []).append(dict(row))

    # Cross-rate data via USD for codes not covered by user or system rates
    # sys_usd_map: from_code → [rows sorted newest-first] for the → USD leg
    # base_usd_list: rows for to_code → USD sorted newest-first
    sys_usd_map: dict[str, list[dict]] = {}
    base_usd_list: list[dict] = []
    if to_code != "USD" and non_base:
        cross_needed_periods = [
            c for c in non_base if c not in user_rate_map and c not in sys_rate_map
        ]
        if cross_needed_periods:
            stmt = text("""
                SELECT from_code, rate, valid_date, source
                FROM exchange_rates
                WHERE from_code = ANY(:codes)
                  AND to_code = 'USD'
                  AND valid_date <= :max_date
                ORDER BY from_code, valid_date DESC
            """)
            result = await db.execute(
                stmt, {"codes": cross_needed_periods, "max_date": max_date}
            )
            for row in result.mappings():
                sys_usd_map.setdefault(row["from_code"], []).append(dict(row))

        if sys_usd_map:
            stmt = text("""
                SELECT rate, valid_date, source
                FROM exchange_rates
                WHERE from_code = :to_code
                  AND to_code = 'USD'
                  AND valid_date <= :max_date
                ORDER BY valid_date DESC
            """)
            result = await db.execute(stmt, {"to_code": to_code, "max_date": max_date})
            for row in result.mappings():
                base_usd_list.append(dict(row))

    # Resolve per period_end in Python
    output: dict[date, dict[str, RateResult]] = {}
    for period_end in period_ends:
        stale_threshold = period_end - timedelta(
            days=settings.EXCHANGE_RATE_STALENESS_DAYS
        )
        period_result: dict[str, RateResult] = {}
        # Identity entries use the actual period_end date
        for c in codes:
            if c == to_code:
                period_result[c] = RateResult(
                    rate=Decimal("1"),
                    source="identity",
                    valid_date=period_end,
                    status="ok",
                )
        for code in non_base:
            # User manual rates take priority
            if code in user_rate_map:
                for ur in user_rate_map[code]:
                    if ur.valid_from <= period_end and (
                        ur.valid_to is None or ur.valid_to >= period_end
                    ):
                        period_result[code] = RateResult(
                            rate=ur.rate,
                            source="user_manual",
                            valid_date=ur.valid_from,
                            status="ok",
                        )
                        break
                else:
                    period_result[code] = RateResult(
                        rate=None, source="none", valid_date=None, status="missing"
                    )
                continue
            # Fall back to system rates (already sorted newest first)
            resolved = False
            if code in sys_rate_map:
                for sr in sys_rate_map[code]:
                    if sr["valid_date"] <= period_end:
                        status = (
                            "ok" if sr["valid_date"] >= stale_threshold else "stale"
                        )
                        period_result[code] = RateResult(
                            rate=sr["rate"],
                            source=sr["source"],
                            valid_date=sr["valid_date"],
                            status=status,
                        )
                        resolved = True
                        break

            if not resolved:
                # Cross-rate fallback: A → to_code = (A → USD) / (to_code → USD)
                from_usd_row: dict | None = None
                if code in sys_usd_map:
                    for row in sys_usd_map[code]:
                        if row["valid_date"] <= period_end:
                            from_usd_row = row
                            break
                base_usd_row_period: dict | None = None
                for row in base_usd_list:
                    if row["valid_date"] <= period_end:
                        base_usd_row_period = row
                        break

                if from_usd_row is not None and base_usd_row_period is not None:
                    cross_valid_date = min(
                        from_usd_row["valid_date"], base_usd_row_period["valid_date"]
                    )
                    cross_status = (
                        "ok" if cross_valid_date >= stale_threshold else "stale"
                    )
                    period_result[code] = RateResult(
                        rate=Decimal(str(from_usd_row["rate"]))
                        / Decimal(str(base_usd_row_period["rate"])),
                        source=from_usd_row["source"],
                        valid_date=cross_valid_date,
                        status=cross_status,
                    )
                else:
                    period_result[code] = RateResult(
                        rate=None, source="none", valid_date=None, status="missing"
                    )
        output[period_end] = period_result
    return output


def convert_amount(
    per_currency: dict[str, Decimal],
    rate_map: dict[str, RateResult],
    to_code: str,
) -> Decimal:
    """Convert per-currency amounts to a single target currency using rate_map."""
    total = Decimal("0")
    for code, amount in per_currency.items():
        if code == to_code:
            total += amount
        else:
            rr = rate_map.get(code)
            if rr and rr.rate:
                total += amount * rr.rate
    return total

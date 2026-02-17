from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, UTC
from zoneinfo import ZoneInfo
from collections import defaultdict
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import OrderDB, OrderItemDB, ProductDB


DEFAULT_FORECAST_STATUSES = ["PAID", "PACKED", "SHIPPED", "DELIVERED"]


@dataclass
class DemandForecastResult:
    date: str
    weeks: int
    order_statuses: list[str]
    items: list[dict]


def _parse_statuses(requested: Iterable[str] | None, allowed: set[str]) -> list[str]:
    if requested:
        raw: list[str] = []
        for s in requested:
            raw.extend([part.strip().upper() for part in s.split(",") if part.strip()])
        statuses = [s for s in raw if s in allowed]
        return statuses
    return [s for s in DEFAULT_FORECAST_STATUSES if s in allowed]


def _matching_dates(target_date: date, weeks: int) -> list[date]:
    # last N matching weekdays (excluding target_date)
    dates = [target_date - timedelta(days=7 * i) for i in range(1, weeks + 1)]
    dates.sort(reverse=True)  # newest -> oldest
    return dates


def compute_demand_forecast(
    db: Session,
    target_date: date,
    weeks: int,
    statuses: list[str],
    tz_name: str = "Europe/Warsaw",
    include_zero_samples: bool = False,
) -> DemandForecastResult:
    tz = ZoneInfo(tz_name)
    matching = _matching_dates(target_date, weeks)

    # If no matching dates, return empty items
    if not matching:
        return DemandForecastResult(
            date=target_date.isoformat(),
            weeks=weeks,
            order_statuses=statuses,
            items=[],
        )

    earliest = datetime.combine(matching[-1], time.min, tzinfo=tz).astimezone(UTC)
    latest = datetime.combine(matching[0] + timedelta(days=1), time.min, tzinfo=tz).astimezone(UTC)

    rows = db.execute(
        select(OrderDB.created_at, OrderItemDB.product_id, OrderItemDB.qty)
        .join(OrderItemDB, OrderItemDB.order_id == OrderDB.id)
        .where(OrderDB.status.in_(statuses))
        .where(OrderDB.created_at >= earliest)
        .where(OrderDB.created_at < latest)
    ).all()

    matching_set = set(matching)
    qty_by_date_product: dict[tuple[date, int], int] = defaultdict(int)
    dates_with_orders: set[date] = set()

    for created_at, product_id, qty in rows:
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        local_date = created_at.astimezone(tz).date()
        if local_date not in matching_set:
            continue
        dates_with_orders.add(local_date)
        qty_by_date_product[(local_date, product_id)] += int(qty or 0)

    sample_dates = matching if include_zero_samples else [d for d in matching if d in dates_with_orders]

    products = db.execute(
        select(ProductDB.id, ProductDB.name, ProductDB.stock_qty)
    ).all()

    items: list[dict] = []
    for product_id, name, stock_qty in products:
        stock = int(stock_qty or 0)
        qty_list = [qty_by_date_product.get((d, product_id), 0) for d in sample_dates]
        samples = len(sample_dates)
        avg = (sum(qty_list) / samples) if samples else 0.0
        forecast_ceil = int(math.ceil(avg)) if samples else 0

        if forecast_ceil > stock:
            risk = "HIGH"
        elif forecast_ceil > 0.7 * stock:
            risk = "MED"
        else:
            risk = "LOW"

        items.append({
            "product_id": product_id,
            "name": name,
            "stock_qty": stock,
            "forecast_qty": avg,
            "forecast_qty_ceil": forecast_ceil,
            "samples": samples,
            "avg_qty_per_matching_day": avg,
            "last_matching_days_qty": qty_list,
            "risk": risk,
        })

    risk_rank = {"HIGH": 0, "MED": 1, "LOW": 2}
    items.sort(key=lambda it: (risk_rank.get(it["risk"], 3), -it["forecast_qty"]))

    return DemandForecastResult(
        date=target_date.isoformat(),
        weeks=weeks,
        order_statuses=statuses,
        items=items,
    )

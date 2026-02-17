from pydantic import BaseModel
from typing import List, Optional


class DemandForecastItem(BaseModel):
    product_id: int
    name: str
    stock_qty: int
    forecast_qty: float
    forecast_qty_ceil: int
    samples: int
    avg_qty_per_matching_day: float
    last_matching_days_qty: List[int]
    risk: str


class DemandForecastResponse(BaseModel):
    date: str
    weeks: int
    order_statuses: List[str]
    items: List[DemandForecastItem]


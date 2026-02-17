from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.deps import get_db
from app.db.models import OrderStatus
from app.schemas.forecast import DemandForecastResponse
from app.core.forecast import compute_demand_forecast, _parse_statuses


router = APIRouter(prefix="/admin/forecast", tags=["admin-forecast"])


@router.get("/demand", response_model=DemandForecastResponse)
def forecast_demand(
    date_param: str | None = Query(default=None, alias="date"),
    weeks: int = Query(default=8, ge=4, le=26),
    statuses: list[str] | None = Query(default=None),
    include_zeros: bool = Query(default=False, alias="include_zeros"),
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    tz = ZoneInfo("Europe/Warsaw")
    if date_param:
        try:
            target_date = date.fromisoformat(date_param)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format, expected YYYY-MM-DD")
    else:
        target_date = (datetime.now(tz).date() + timedelta(days=1))

    allowed_statuses = {s.value for s in OrderStatus}
    parsed_statuses = _parse_statuses(statuses, allowed_statuses)
    if not parsed_statuses:
        raise HTTPException(status_code=400, detail="No valid statuses provided")

    result = compute_demand_forecast(
        db=db,
        target_date=target_date,
        weeks=weeks,
        statuses=parsed_statuses,
        tz_name="Europe/Warsaw",
        include_zero_samples=include_zeros,
    )
    return DemandForecastResponse(**result.__dict__)

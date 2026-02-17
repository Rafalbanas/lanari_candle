from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select, desc

from app.db.deps import get_db
from app.api.deps import require_admin
from app.db.models import ProductDB, OrderDB, OrderStatus
from app.schemas.admin import ProductCreate, ProductUpdate, OrderStatusUpdate, AdminOrderOut
from app.schemas.product import Product as ProductOut
from app.schemas.order import OrderOut
from app.api.orders import _order_out
from app.schemas.forecast import DemandForecastResponse
from app.core.forecast import compute_demand_forecast, _parse_statuses
from datetime import date, datetime, timedelta
from fastapi import Query
from zoneinfo import ZoneInfo

router = APIRouter(prefix="/admin/api", tags=["admin"])

# --- PRODUCTS ---

@router.get("/products", response_model=list[ProductOut])
def list_products(db: Session = Depends(get_db), _=Depends(require_admin)):
    # Admin widzi wszystkie produkty, nawet nieaktywne
    stmt = select(ProductDB).order_by(ProductDB.id.desc())
    return db.execute(stmt).scalars().all()

@router.post("/products", response_model=ProductOut)
def create_product(payload: ProductCreate, db: Session = Depends(get_db), _=Depends(require_admin)):
    p = ProductDB(**payload.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return p

@router.patch("/products/{product_id}", response_model=ProductOut)
def update_product(product_id: int, payload: ProductUpdate, db: Session = Depends(get_db), _=Depends(require_admin)):
    p = db.get(ProductDB, product_id)
    if not p:
        raise HTTPException(404, "Product not found")

    update_data = payload.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(p, k, v)

    db.commit()
    db.refresh(p)
    return p

@router.delete("/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    p = db.get(ProductDB, product_id)
    if not p:
        raise HTTPException(404, "Product not found")
    
    # Soft delete (dezaktywacja) jest bezpieczniejsza, ale tutaj robimy hard delete zgodnie z prośbą
    # Uwaga: jeśli produkt jest w zamówieniach, to może naruszyć FK (chyba że masz cascade)
    # Lepiej: p.is_active = False
    db.delete(p)
    db.commit()
    return {"ok": True}

# --- ORDERS ---

@router.get("/orders", response_model=list[AdminOrderOut])
def list_orders(db: Session = Depends(get_db), _=Depends(require_admin)):
    stmt = (
        select(OrderDB)
        .options(selectinload(OrderDB.items))
        .order_by(desc(OrderDB.created_at))
        .limit(100)
    )
    orders = db.execute(stmt).scalars().all()
    return orders

@router.get("/orders/{order_id}", response_model=OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    stmt = select(OrderDB).where(OrderDB.id == order_id).options(selectinload(OrderDB.items))
    order = db.execute(stmt).scalar_one_or_none()
    if not order:
        raise HTTPException(404, "Order not found")
    return _order_out(order)

@router.patch("/orders/{order_id}/status")
def update_order_status(
    order_id: int, 
    payload: OrderStatusUpdate, 
    db: Session = Depends(get_db), 
    _=Depends(require_admin)
):
    # Walidacja statusu
    try:
        new_status = OrderStatus(payload.status)
    except ValueError:
        raise HTTPException(400, f"Invalid status. Allowed: {[s.value for s in OrderStatus]}")

    order = db.get(OrderDB, order_id)
    if not order:
        raise HTTPException(404, "Order not found")

    order.status = new_status
    db.commit()
    return {"ok": True, "id": order.id, "status": order.status}


# --- FORECAST ---

@router.get("/forecast/demand", response_model=DemandForecastResponse)
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

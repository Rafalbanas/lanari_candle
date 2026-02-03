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

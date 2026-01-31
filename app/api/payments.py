from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, delete

from app.db.deps import get_db
from app.db.models import OrderDB, OrderStatus, PaymentAttemptDB, PaymentStatus, CartItemDB

router = APIRouter(prefix="/payments/mock", tags=["payments"])

@router.post("/confirm")
def confirm_mock(payload: dict, db: Session = Depends(get_db)):
    # payload: {"order_id": 1}
    order_id = payload.get("order_id")
    if not order_id:
        raise HTTPException(400, "Missing order_id")

    pay = db.execute(select(PaymentAttemptDB).where(PaymentAttemptDB.order_id == order_id, PaymentAttemptDB.provider == "mock")).scalar_one_or_none()
    if not pay:
        raise HTTPException(404, "Payment attempt not found")

    order = db.get(OrderDB, order_id)
    if not order:
        raise HTTPException(404, "Order not found")

    if pay.status == PaymentStatus.SUCCEEDED and order.status == OrderStatus.PAID:
        return {"ok": True, "order_id": order.id, "status": order.status}

    # Symulacja sukcesu
    pay.status = PaymentStatus.SUCCEEDED
    order.status = OrderStatus.PAID

    # Koszyk został już wyczyszczony przy tworzeniu zamówienia w Twoim obecnym flow (app/api/orders.py),
    # więc tutaj tylko aktualizujemy statusy.

    db.commit()
    return {"ok": True, "order_id": order.id, "status": order.status}
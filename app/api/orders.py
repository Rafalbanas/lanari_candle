from fastapi import APIRouter, Depends, HTTPException, Header, Request, Response
from sqlalchemy.orm import Session, selectinload, joinedload
from sqlalchemy import select, delete

from app.db.deps import get_db
from app.api.deps import get_current_user
from app.db.models import CartDB, CartItemDB, OrderDB, OrderItemDB, OrderStatus, UserDB, PaymentAttemptDB, PaymentStatus
from app.schemas.order import OrderCreate, OrderOut, OrderItemOut, CheckoutRequest
from app.db.cart_service import get_or_create_cart

router = APIRouter(prefix="/orders", tags=["orders"])
checkout_router = APIRouter(prefix="/checkout", tags=["checkout"])


@checkout_router.post("", response_model=OrderOut, status_code=201)
def checkout(
    request: Request,
    response: Response,
    payload: CheckoutRequest,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    # 1. Idempotency check (sprawdzamy czy już jest płatność/zamówienie z tym kluczem)
    if idempotency_key:
        existing_payment = db.execute(
            select(PaymentAttemptDB)
            .where(PaymentAttemptDB.idempotency_key == idempotency_key)
        ).scalar_one_or_none()
        
        if existing_payment:
            existing_order = db.get(OrderDB, existing_payment.order_id)
            if existing_order:
                return _order_out(existing_order)

    # 2. Check if cart already has an order (double-click prevention)
    # (Tutaj musimy najpierw pobrać koszyk, żeby znać jego ID)
    cart = get_or_create_cart(db, request, response)
    
    existing_for_cart = db.execute(
        select(OrderDB)
        .where(OrderDB.cart_id == cart.id)
        .options(selectinload(OrderDB.items))
    ).scalar_one_or_none()
    if existing_for_cart:
        return _order_out(existing_for_cart)

    if not cart.items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    # 4. Prepare order items (snapshot)
    total_pln = 0
    order_items_db = []

    for it in cart.items:
        line_total = it.qty * it.unit_price_pln
        total_pln += line_total
        
        # Snapshot name from product
        product_name = it.product.name if it.product else f"Product {it.product_id}"
        
        order_items_db.append(
            OrderItemDB(
                product_id=it.product_id,
                name=product_name,
                qty=it.qty,
                unit_price_pln=it.unit_price_pln,
                line_total_pln=line_total
            )
        )

    # 5. Transaction: Create Order + Clear Cart
    try:
        order = OrderDB(
            cart_id=cart.id,
            email=current_user.email,  # Używamy emaila z tokena (bezpieczniej)
            full_name=current_user.full_name or payload.full_name,  # Preferujemy imię z konta
            total_pln=total_pln,
            status=OrderStatus.NEW,
            idempotency_key=idempotency_key, # Zostawiamy w OrderDB dla spójności, ale główna kontrola w PaymentAttempt
            items=order_items_db
        )
        db.add(order)
        
        # Mark cart as checked out
        cart.is_checked_out = True
        db.add(cart)

        # Create Payment Attempt if idempotency key provided (or generate one)
        if idempotency_key:
            payment = PaymentAttemptDB(
                order_id=order.id, # Będzie dostępne po flush, ale SQLAlchemy ogarnie to w sesji
                provider="mock",
                status=PaymentStatus.PENDING,
                idempotency_key=idempotency_key
            )
            db.add(payment)

        # Clear cart items
        db.execute(delete(CartItemDB).where(CartItemDB.cart_id == cart.id))
        
        db.commit()
        db.refresh(order)
    except Exception:
        db.rollback()
        raise

    return _order_out(order)


@router.post("", response_model=OrderOut, status_code=201)
def create_order(
    request: Request,
    response: Response,
    payload: OrderCreate,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    # Legacy wrapper using the new logic
    req = CheckoutRequest(cart_id=payload.cart_id, email=payload.email, full_name=payload.full_name)
    return checkout(request, response, req, db=db, current_user=current_user, idempotency_key=None)


@router.get("", response_model=list[OrderOut])
def list_my_orders(
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    stmt = (
        select(OrderDB)
        .where(OrderDB.email == current_user.email)
        .options(selectinload(OrderDB.items))
        .order_by(OrderDB.created_at.desc())
    )
    orders = db.execute(stmt).scalars().all()
    return [_order_out(o) for o in orders]


@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = db.get(OrderDB, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return _order_out(order)


def _order_out(order: OrderDB) -> OrderOut:
    out_items = []
    for it in order.items:
        out_items.append(
            OrderItemOut(
                id=it.id,
                product_id=it.product_id,
                name=it.name,
                qty=it.qty,
                unit_price_pln=it.unit_price_pln,
                line_total_pln=it.line_total_pln,
            )
        )

    return OrderOut(
        id=order.id,
        cart_id=order.cart_id,
        status=order.status,
        email=order.email,
        full_name=order.full_name,
        items=out_items,
        total_pln=order.total_pln,
    )
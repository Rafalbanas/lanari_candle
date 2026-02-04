from datetime import datetime, UTC
from fastapi import APIRouter, Depends, HTTPException, Header, Request, Response
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select, delete

from app.db.deps import get_db
from app.api.deps import get_current_user
from app.db.models import (
    CartDB,
    CartItemDB,
    OrderDB,
    OrderItemDB,
    OrderStatus,
    UserDB,
    PaymentAttemptDB,
    PaymentStatus,
    ProductDB,
    ShippingMethod,
    CustomerProfileDB,
)
from app.core.shipping import calculate_shipping
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
    if payload.cart_id:
        cart = db.get(CartDB, payload.cart_id)
        if not cart:
            raise HTTPException(status_code=404, detail="Cart not found")
    else:
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

    if payload.country != "PL":
        raise HTTPException(status_code=400, detail="Shipping only available in PL")

    # 4. Prepare order items (snapshot)
    total_grosze = 0
    order_items_db = []

    # Stock validation and collection of touched products for decrement
    touched_products = []

    for it in cart.items:
        # refresh product from DB to ensure current stock
        product = db.get(ProductDB, it.product_id)
        if not product or not product.is_active:
            raise HTTPException(status_code=400, detail=f"Product {it.product_id} unavailable")
        if it.qty > product.stock_qty:
            raise HTTPException(status_code=400, detail=f"Not enough stock for {product.name}")

        line_total = it.qty * it.unit_price_pln
        total_grosze += line_total
        
        # Snapshot name from product
        product_name = product.name
        
        order_items_db.append(
            OrderItemDB(
                product_id=it.product_id,
                name=product_name,
                qty=it.qty,
                unit_price_pln=it.unit_price_pln,
                line_total_pln=line_total
            )
        )
        touched_products.append((product, it.qty))

    # 5. Shipping selection: allow inline selection, otherwise require previously set
    if cart.shipping_method is None:
        if payload.shipping_method is None:
            raise HTTPException(status_code=400, detail="Shipping method required")
        try:
            method = ShippingMethod(payload.shipping_method)
        except ValueError:
            raise HTTPException(status_code=400, detail="Unknown shipping method")
        try:
            shipping_cost = calculate_shipping(total_grosze, method)
        except ValueError:
            raise HTTPException(status_code=400, detail="Unknown shipping method")
        cart.shipping_method = method
        cart.shipping_cost_pln = shipping_cost
        db.add(cart)
        db.flush()
    else:
        try:
            shipping_cost = calculate_shipping(total_grosze, cart.shipping_method)
        except ValueError:
            raise HTTPException(status_code=400, detail="Unknown shipping method")

    cart.shipping_cost_pln = shipping_cost
    total_with_shipping = total_grosze + shipping_cost

    try:
        buyer_full_name = f"{payload.first_name} {payload.last_name}".strip()
        order = OrderDB(
            cart_id=cart.id,
            email=current_user.email,  # Używamy emaila z tokena (bezpieczniej)
            full_name=buyer_full_name,
            buyer_first_name=payload.first_name,
            buyer_last_name=payload.last_name,
            buyer_phone=payload.phone,
            buyer_email=current_user.email,
            shipping_address_line1=payload.address_line1,
            shipping_address_line2=payload.address_line2,
            shipping_city=payload.city,
            shipping_postal_code=payload.postal_code,
            total_pln=total_with_shipping,
            status=OrderStatus.NEW,
            idempotency_key=idempotency_key, # Zostawiamy w OrderDB dla spójności, ale główna kontrola w PaymentAttempt
            items=order_items_db,
            shipping_method=cart.shipping_method,
            shipping_cost_pln=shipping_cost,
            shipping_country=payload.country,
        )
        db.add(order)
        db.flush()  # ensure order.id is assigned before payment attempt

        # Upsert customer profile
        profile = db.execute(
            select(CustomerProfileDB).where(CustomerProfileDB.user_id == current_user.id)
        ).scalar_one_or_none()
        now = datetime.now(UTC)
        if profile:
            profile.first_name = payload.first_name
            profile.last_name = payload.last_name
            profile.phone = payload.phone
            profile.address_line1 = payload.address_line1
            profile.address_line2 = payload.address_line2
            profile.city = payload.city
            profile.postal_code = payload.postal_code
            profile.country = payload.country
            profile.updated_at = now
            db.add(profile)
        else:
            db.add(
                CustomerProfileDB(
                    user_id=current_user.id,
                    first_name=payload.first_name,
                    last_name=payload.last_name,
                    phone=payload.phone,
                    address_line1=payload.address_line1,
                    address_line2=payload.address_line2,
                    city=payload.city,
                    postal_code=payload.postal_code,
                    country=payload.country,
                    updated_at=now,
                )
            )

        # Mark cart as checked out
        cart.is_checked_out = True
        db.add(cart)

        # Create Payment Attempt if idempotency key provided (or generate one)
        if idempotency_key:
            payment = PaymentAttemptDB(
                order_id=order.id,
                provider="mock",
                status=PaymentStatus.PENDING,
                idempotency_key=idempotency_key
            )
            db.add(payment)

        # Decrement stock
        for product, qty in touched_products:
            product.stock_qty -= qty
            if product.stock_qty < 0:
                raise HTTPException(status_code=400, detail=f"Oversell detected for {product.name}")
            db.add(product)

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
    req = CheckoutRequest(
        cart_id=payload.cart_id,
        first_name=payload.first_name,
        last_name=payload.last_name,
        phone=payload.phone,
        address_line1=payload.address_line1,
        address_line2=payload.address_line2,
        city=payload.city,
        postal_code=payload.postal_code,
        country=payload.country,
        shipping_method=payload.shipping_method,
    )
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
        buyer_first_name=order.buyer_first_name,
        buyer_last_name=order.buyer_last_name,
        buyer_phone=order.buyer_phone,
        buyer_email=order.buyer_email,
        shipping_address_line1=order.shipping_address_line1,
        shipping_address_line2=order.shipping_address_line2,
        shipping_city=order.shipping_city,
        shipping_postal_code=order.shipping_postal_code,
        items=out_items,
        total_pln=order.total_pln,
        shipping_method=order.shipping_method,
        shipping_cost_pln=order.shipping_cost_pln,
        shipping_country=order.shipping_country,
    )

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.db.models import CartDB, ShippingMethod
from app.core.shipping import (
    SHIPPING_PRICES,
    FREE_SHIPPING_THRESHOLD_PLN,
    get_cart_subtotal,
    calculate_shipping,
)
from app.schemas.shipping import (
    ShippingMethodsResponse,
    ShippingMethodCost,
    SetShippingRequest,
    CartShippingSummary,
)

router = APIRouter(tags=["shipping"])


@router.get("/shipping/methods", response_model=ShippingMethodsResponse)
def list_shipping_methods(cart_id: int = Query(...), db: Session = Depends(get_db)):
    cart = db.get(CartDB, cart_id)
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")

    subtotal = get_cart_subtotal(cart)

    methods: list[ShippingMethodCost] = []
    for method, base_cost in SHIPPING_PRICES.items():
        cost = calculate_shipping(subtotal, method)
        methods.append(
            ShippingMethodCost(
                method=method,
                cost_pln=cost,
                is_free=cost == 0,
            )
        )

    selected = None
    if cart.shipping_method:
        selected_cost = calculate_shipping(subtotal, cart.shipping_method)
        selected = ShippingMethodCost(
            method=cart.shipping_method,
            cost_pln=selected_cost,
            is_free=selected_cost == 0,
        )

    return ShippingMethodsResponse(
        cart_id=cart.id,
        subtotal_pln=subtotal,
        free_shipping_threshold_pln=FREE_SHIPPING_THRESHOLD_PLN,
        methods=methods,
        selected=selected,
    )


@router.post("/cart/shipping", response_model=CartShippingSummary)
def set_cart_shipping(payload: SetShippingRequest, cart_id: int = Query(...), db: Session = Depends(get_db)):
    cart = db.get(CartDB, cart_id)
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")

    try:
        method = ShippingMethod(payload.shipping_method)
    except ValueError:
        raise HTTPException(status_code=400, detail="Unknown shipping method")

    # Polska only (placeholder, as no address yet)
    shipping_country = "PL"
    if shipping_country != "PL":
        raise HTTPException(status_code=400, detail="Shipping only available in PL")

    subtotal = get_cart_subtotal(cart)
    shipping_cost = calculate_shipping(subtotal, method)

    cart.shipping_method = method
    cart.shipping_cost_pln = shipping_cost

    db.add(cart)
    db.commit()
    db.refresh(cart)

    return CartShippingSummary(
        cart_id=cart.id,
        subtotal_pln=subtotal,
        shipping_method=method,
        shipping_cost_pln=shipping_cost,
        total_pln=subtotal + shipping_cost,
    )

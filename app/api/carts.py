from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.deps import get_db
from app.db.models import CartDB, CartItemDB, ProductDB, ShippingMethod
from app.schemas.cart import CartItemAdd, CartOut, CartItemOut, CartItemUpdate
from app.core.shipping import calculate_shipping
from app.db.cart_service import get_or_create_cart

router = APIRouter(prefix="/cart", tags=["cart"])


@router.get("", response_model=CartOut)
def get_cart(request: Request, response: Response, db: Session = Depends(get_db)):
    cart = get_or_create_cart(db, request, response)
    return _cart_out(cart, db)


@router.post("/items", response_model=CartOut, status_code=201)
def add_item(payload: CartItemAdd, request: Request, response: Response, db: Session = Depends(get_db)):
    cart = get_or_create_cart(db, request, response)

    product = db.get(ProductDB, payload.product_id)
    if not product or not product.is_active:
        raise HTTPException(status_code=404, detail="Product not found")
    if product.stock_qty < payload.qty:
        raise HTTPException(status_code=400, detail="Not enough stock")

    # jeśli produkt już jest w koszyku -> zwiększ qty
    stmt = select(CartItemDB).where(
        CartItemDB.cart_id == cart.id,
        CartItemDB.product_id == payload.product_id,
    )
    item = db.execute(stmt).scalars().first()

    if item:
        if item.qty + payload.qty > product.stock_qty:
            raise HTTPException(status_code=400, detail="Not enough stock")
        item.qty += payload.qty
    else:
        item = CartItemDB(
            cart_id=cart.id,
            product_id=payload.product_id,
            qty=payload.qty,
            unit_price_pln=product.price_pln,
        )
        db.add(item)

    db.commit()
    return _cart_out(cart, db)


@router.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: int, request: Request, response: Response, db: Session = Depends(get_db)):
    cart = get_or_create_cart(db, request, response)
    item = db.get(CartItemDB, item_id)
    if not item or item.cart_id != cart.id:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(item)
    db.commit()
    return


@router.patch("/items/{item_id}", response_model=CartOut)
def update_item(item_id: int, payload: CartItemUpdate, request: Request, response: Response, db: Session = Depends(get_db)):
    cart = get_or_create_cart(db, request, response)
    item = db.get(CartItemDB, item_id)
    if not item or item.cart_id != cart.id:
        raise HTTPException(status_code=404, detail="Item not found")

    if payload.qty == 0:
        db.delete(item)
        db.commit()
        return _cart_out(cart, db)

    product = db.get(ProductDB, item.product_id)
    if not product or not product.is_active:
        raise HTTPException(status_code=404, detail="Product not found")
    if payload.qty > product.stock_qty:
        raise HTTPException(status_code=400, detail="Not enough stock")

    item.qty = payload.qty
    db.add(item)
    db.commit()
    return _cart_out(cart, db)


def _cart_out(cart: CartDB, db: Session) -> CartOut:
    # Przeładowujemy itemy, żeby mieć pewność co do stanu
    db.refresh(cart, attribute_names=["items"])
    items = cart.items

    out_items: list[CartItemOut] = []
    subtotal = 0

    for it in items:
        line_total = it.qty * it.unit_price_pln
        subtotal += line_total
        out_items.append(
            CartItemOut(
                id=it.id,
                product_id=it.product_id,
                name=it.product.name if it.product else f"Product {it.product_id}",
                qty=it.qty,
                unit_price_pln=it.unit_price_pln,
                line_total_pln=line_total,
            )
        )

    shipping_cost = 0
    if cart.shipping_method:
        try:
            shipping_cost = calculate_shipping(subtotal, cart.shipping_method)
        except ValueError:
            shipping_cost = cart.shipping_cost_pln or 0
        else:
            if shipping_cost != cart.shipping_cost_pln:
                cart.shipping_cost_pln = shipping_cost
                db.add(cart)
                db.flush()

    return CartOut(
        id=cart.id,
        items=out_items,
        subtotal_pln=subtotal,
        shipping_method=cart.shipping_method,
        shipping_cost_pln=shipping_cost,
        total_pln=subtotal + shipping_cost,
    )

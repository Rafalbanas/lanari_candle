from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.deps import get_db
from app.db.models import CartDB, CartItemDB, ProductDB
from app.schemas.cart import CartItemAdd, CartOut, CartItemOut, CartItemUpdate

router = APIRouter(prefix="/carts", tags=["carts"])


@router.post("", response_model=CartOut, status_code=201)
def create_cart(db: Session = Depends(get_db)):
    cart = CartDB()
    db.add(cart)
    db.commit()
    db.refresh(cart)
    return CartOut(id=cart.id, items=[], total_pln=0)


@router.post("/{cart_id}/items", response_model=CartOut, status_code=201)
def add_item(cart_id: int, payload: CartItemAdd, db: Session = Depends(get_db)):
    cart = db.get(CartDB, cart_id)
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")

    if cart.is_checked_out:
        raise HTTPException(status_code=400, detail="Cart already checked out")

    product = db.get(ProductDB, payload.product_id)
    if not product or not product.is_active:
        raise HTTPException(status_code=404, detail="Product not found")

    # jeśli produkt już jest w koszyku -> zwiększ qty
    stmt = select(CartItemDB).where(
        CartItemDB.cart_id == cart_id,
        CartItemDB.product_id == payload.product_id,
    )
    item = db.execute(stmt).scalars().first()

    if item:
        item.qty += payload.qty
    else:
        item = CartItemDB(
            cart_id=cart_id,
            product_id=payload.product_id,
            qty=payload.qty,
            unit_price_pln=product.price_pln,
        )
        db.add(item)

    db.commit()
    return _cart_out(cart_id, db)


@router.get("/{cart_id}", response_model=CartOut)
def get_cart(cart_id: int, db: Session = Depends(get_db)):
    cart = db.get(CartDB, cart_id)
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    return _cart_out(cart_id, db)


@router.delete("/{cart_id}/items/{item_id}", status_code=204)
def delete_item(cart_id: int, item_id: int, db: Session = Depends(get_db)):
    item = db.get(CartItemDB, item_id)
    if not item or item.cart_id != cart_id:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(item)
    db.commit()
    return


@router.patch("/{cart_id}/items/{item_id}", response_model=CartOut)
def update_item(cart_id: int, item_id: int, payload: CartItemUpdate, db: Session = Depends(get_db)):
    item = db.get(CartItemDB, item_id)
    if not item or item.cart_id != cart_id:
        raise HTTPException(status_code=404, detail="Item not found")

    if payload.qty == 0:
        db.delete(item)
        db.commit()
        return _cart_out(cart_id, db)

    item.qty = payload.qty
    db.add(item)
    db.commit()
    return _cart_out(cart_id, db)


def _cart_out(cart_id: int, db: Session) -> CartOut:
    stmt = select(CartItemDB).where(CartItemDB.cart_id == cart_id)
    items = db.execute(stmt).scalars().all()

    out_items: list[CartItemOut] = []
    total = 0

    for it in items:
        line_total = it.qty * it.unit_price_pln
        total += line_total
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

    return CartOut(id=cart_id, items=out_items, total_pln=total)
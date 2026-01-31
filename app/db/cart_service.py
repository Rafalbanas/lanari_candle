import secrets
from fastapi import Request, Response
from sqlalchemy.orm import Session
from app.db.models import CartDB

COOKIE_NAME = "cart_token"

def get_or_create_cart(db: Session, request: Request, response: Response) -> CartDB:
    token = request.cookies.get(COOKIE_NAME)
    if token:
        cart = db.query(CartDB).filter(CartDB.token == token).first()
        if cart and not cart.is_checked_out:
            return cart

    # Tworzymy nowy koszyk
    token = secrets.token_hex(32)
    cart = CartDB(token=token)
    db.add(cart)
    db.commit()
    db.refresh(cart)

    # Ustawiamy ciasteczko
    response.set_cookie(COOKIE_NAME, token, httponly=True, samesite="lax")
    return cart
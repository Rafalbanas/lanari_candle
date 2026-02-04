from typing import List, Literal
from pydantic import BaseModel, Field, EmailStr, constr

from app.db.models import ShippingMethod


class OrderCreate(BaseModel):
    cart_id: int
    first_name: str = Field(min_length=2, max_length=60)
    last_name: str = Field(min_length=2, max_length=80)
    phone: constr(pattern=r"^\+?\d{9,15}$") = Field(min_length=9, max_length=15)
    address_line1: str = Field(min_length=5, max_length=120)
    address_line2: str | None = Field(default=None, max_length=120)
    city: str = Field(min_length=2, max_length=80)
    postal_code: constr(pattern=r"^\d{2}-\d{3}$")
    country: Literal["PL"] = "PL"
    shipping_method: ShippingMethod | None = None


class CheckoutRequest(BaseModel):
    cart_id: int | None = None  # Opcjonalne, bo bierzemy z cookie
    first_name: str = Field(min_length=2, max_length=60)
    last_name: str = Field(min_length=2, max_length=80)
    phone: constr(pattern=r"^\+?\d{9,15}$") = Field(min_length=9, max_length=15)
    address_line1: str = Field(min_length=5, max_length=120)
    address_line2: str | None = Field(default=None, max_length=120)
    city: str = Field(min_length=2, max_length=80)
    postal_code: constr(pattern=r"^\d{2}-\d{3}$")
    country: Literal["PL"] = "PL"
    shipping_method: ShippingMethod | None = None


class OrderItemOut(BaseModel):
    id: int
    product_id: int
    name: str
    qty: int
    unit_price_pln: int
    line_total_pln: int


class OrderOut(BaseModel):
    id: int
    status: str
    cart_id: int
    email: EmailStr
    full_name: str
    buyer_first_name: str
    buyer_last_name: str
    buyer_phone: str
    buyer_email: EmailStr
    shipping_address_line1: str
    shipping_address_line2: str | None
    shipping_city: str
    shipping_postal_code: str
    items: List[OrderItemOut]
    total_pln: int
    shipping_method: ShippingMethod
    shipping_cost_pln: int
    shipping_country: str

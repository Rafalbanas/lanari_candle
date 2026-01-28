from pydantic import BaseModel, Field
from typing import List, Optional


class CartItemAdd(BaseModel):
    product_id: int
    qty: int = Field(ge=1, le=100)


class CartItemUpdate(BaseModel):
    qty: int = Field(ge=0, le=100)  # 0 = usuń pozycję


class CartItemOut(BaseModel):
    id: int
    product_id: int
    name: str
    qty: int
    unit_price_pln: int
    line_total_pln: int


class CartOut(BaseModel):
    id: int
    items: List[CartItemOut]
    total_pln: int
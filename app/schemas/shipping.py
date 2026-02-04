from pydantic import BaseModel, Field
from typing import Optional, List

from app.db.models import ShippingMethod


class ShippingMethodCost(BaseModel):
    method: ShippingMethod
    cost_pln: int
    is_free: bool


class ShippingMethodsResponse(BaseModel):
    cart_id: int
    currency: str = "PLN"
    subtotal_pln: int
    free_shipping_threshold_pln: int
    methods: List[ShippingMethodCost]
    selected: Optional[ShippingMethodCost] = None


class SetShippingRequest(BaseModel):
    shipping_method: str = Field(..., description="Selected shipping method")


class CartShippingSummary(BaseModel):
    cart_id: int
    subtotal_pln: int
    shipping_method: ShippingMethod
    shipping_cost_pln: int
    total_pln: int

from typing import Literal
from pydantic import BaseModel, Field, constr


class CheckoutProfileOut(BaseModel):
    first_name: str = Field(min_length=2, max_length=60)
    last_name: str = Field(min_length=2, max_length=80)
    phone: constr(pattern=r"^\+?\d{9,15}$") = Field(min_length=9, max_length=15)
    address_line1: str = Field(min_length=5, max_length=120)
    address_line2: str | None = Field(default=None, max_length=120)
    city: str = Field(min_length=2, max_length=80)
    postal_code: constr(pattern=r"^\d{2}-\d{3}$")
    country: Literal["PL"] = "PL"

from pydantic import BaseModel, Field
from typing import Optional


class ProductBase(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: Optional[str] = Field(default=None, max_length=2000)
    price_pln: int = Field(ge=1, le=1_000_000, description="Price in grosze (PLN * 100)")
    is_active: bool = True
    image_url: Optional[str] = Field(default=None, max_length=512)
    stock_qty: int = Field(ge=0, le=1_000_000, default=0)


class ProductCreate(ProductBase):
    pass


class Product(ProductBase):
    id: int


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    description: Optional[str] = Field(default=None, max_length=2000)
    price_pln: Optional[int] = Field(default=None, ge=1, le=1_000_000)
    is_active: Optional[bool] = None
    image_url: Optional[str] = Field(default=None, max_length=512)
    stock_qty: Optional[int] = Field(default=None, ge=0, le=1_000_000)

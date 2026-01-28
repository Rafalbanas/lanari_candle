from fastapi import APIRouter, HTTPException, Depends
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.schemas.product import Product, ProductCreate, ProductUpdate
from app.db.deps import get_db
from app.db.models import ProductDB

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=List[Product])
def list_products(active_only: bool = True, db: Session = Depends(get_db)):
    stmt = select(ProductDB)
    if active_only:
        stmt = stmt.where(ProductDB.is_active == True)  # noqa: E712
    rows = db.execute(stmt).scalars().all()
    return [
        Product(
            id=r.id,
            name=r.name,
            description=r.description,
            price_pln=r.price_pln,
            is_active=r.is_active,
        )
        for r in rows
    ]


@router.get("/{product_id}", response_model=Product)
def get_product(product_id: int, db: Session = Depends(get_db)):
    row = db.get(ProductDB, product_id)
    if not row:
        raise HTTPException(status_code=404, detail="Product not found")
    return Product(
        id=row.id,
        name=row.name,
        description=row.description,
        price_pln=row.price_pln,
        is_active=row.is_active,
    )


@router.patch("/{product_id}", response_model=Product)
def update_product(product_id: int, payload: ProductUpdate, db: Session = Depends(get_db)):
    row = db.get(ProductDB, product_id)
    if not row:
        raise HTTPException(status_code=404, detail="Product not found")

    data = payload.model_dump(exclude_unset=True)

    # mała walidacja biznesowa (opcjonalnie, ale przydatne)
    if "name" in data and data["name"] is not None and not data["name"].strip():
        raise HTTPException(status_code=422, detail="Name cannot be empty")
    if "price_pln" in data and data["price_pln"] is not None and data["price_pln"] < 1:
        raise HTTPException(status_code=422, detail="price_pln must be >= 1")

    for k, v in data.items():
        setattr(row, k, v)

    db.add(row)
    db.commit()
    db.refresh(row)

    return Product(
        id=row.id,
        name=row.name,
        description=row.description,
        price_pln=row.price_pln,
        is_active=row.is_active,
    )


@router.delete("/{product_id}", status_code=204)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    row = db.get(ProductDB, product_id)
    if not row:
        raise HTTPException(status_code=404, detail="Product not found")

    row.is_active = False
    db.add(row)
    db.commit()
    return


@router.post("", response_model=Product, status_code=201)
def create_product(payload: ProductCreate, db: Session = Depends(get_db)):
    row = ProductDB(
        name=payload.name,
        description=payload.description,
        price_pln=payload.price_pln,
        is_active=payload.is_active,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return Product(
        id=row.id,
        name=row.name,
        description=row.description,
        price_pln=row.price_pln,
        is_active=row.is_active,
    )
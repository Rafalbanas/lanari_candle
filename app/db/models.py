from enum import StrEnum
from datetime import datetime, UTC
from sqlalchemy import Integer, String, Boolean, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class OrderStatus(StrEnum):
    NEW = "NEW"
    PAID = "PAID"
    SHIPPED = "SHIPPED"
    CANCELED = "CANCELED"

class ProductDB(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price_pln: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    

class CartDB(Base):
    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    is_checked_out: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    items: Mapped[list["CartItemDB"]] = relationship(
        back_populates="cart",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class CartItemDB(Base):
    __tablename__ = "cart_items"
    __table_args__ = (
        UniqueConstraint("cart_id", "product_id", name="uq_cart_product"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    cart_id: Mapped[int] = mapped_column(ForeignKey("carts.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)

    qty: Mapped[int] = mapped_column(nullable=False, default=1)
    unit_price_pln: Mapped[int] = mapped_column(nullable=False)  # snapshot ceny w groszach

    cart: Mapped["CartDB"] = relationship(back_populates="items")
    product: Mapped["ProductDB"] = relationship(lazy="joined")


class OrderDB(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    cart_id: Mapped[int] = mapped_column(ForeignKey("carts.id"), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=OrderStatus.NEW, nullable=False)

    # idempotency: jeśli klient kliknie 2x, po tym kluczu zwrócimy to samo zamówienie
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True)

    # minimalne dane klienta (na start)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)

    total_pln: Mapped[int] = mapped_column(Integer, nullable=False)

    items: Mapped[list["OrderItemDB"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint("cart_id", name="uq_orders_cart_id"),
    )


class OrderItemDB(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)

    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)  # snapshot nazwy
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price_pln: Mapped[int] = mapped_column(Integer, nullable=False)
    line_total_pln: Mapped[int] = mapped_column(Integer, nullable=False)

    order: Mapped["OrderDB"] = relationship(back_populates="items")
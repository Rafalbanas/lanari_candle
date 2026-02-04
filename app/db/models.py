from enum import StrEnum
from datetime import datetime, UTC
from sqlalchemy import Integer, String, Boolean, Text, DateTime, ForeignKey, UniqueConstraint, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class OrderStatus(StrEnum):
    NEW = "NEW"
    IN_PREPARATION = "IN_PREPARATION"
    PAID = "PAID"
    SHIPPED = "SHIPPED"
    CANCELED = "CANCELED"

class PaymentStatus(StrEnum):
    PENDING = "PENDING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class ShippingMethod(StrEnum):
    INPOST_LOCKER = "INPOST_LOCKER"
    COURIER = "COURIER"
    PICKUP = "PICKUP"


class UserDB(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    profile: Mapped["CustomerProfileDB"] = relationship(back_populates="user", uselist=False)


class CustomerProfileDB(Base):
    __tablename__ = "customer_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)

    first_name: Mapped[str] = mapped_column(String(60), nullable=False)
    last_name: Mapped[str] = mapped_column(String(80), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    address_line1: Mapped[str] = mapped_column(String(120), nullable=False)
    address_line2: Mapped[str | None] = mapped_column(String(120), nullable=True)
    city: Mapped[str] = mapped_column(String(80), nullable=False)
    postal_code: Mapped[str] = mapped_column(String(10), nullable=False)
    country: Mapped[str] = mapped_column(String(2), nullable=False, default="PL")

    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    user: Mapped["UserDB"] = relationship(back_populates="profile")

class ProductDB(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price_pln: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    stock_qty: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    

class CartDB(Base):
    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    is_checked_out: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    token: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, nullable=True)

    shipping_method: Mapped[ShippingMethod | None] = mapped_column(Enum(ShippingMethod, name="shippingmethod"), nullable=True)
    shipping_cost_pln: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

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

    buyer_first_name: Mapped[str] = mapped_column(String(60), nullable=False)
    buyer_last_name: Mapped[str] = mapped_column(String(80), nullable=False)
    buyer_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    buyer_email: Mapped[str] = mapped_column(String(255), nullable=False)

    shipping_address_line1: Mapped[str] = mapped_column(String(120), nullable=False)
    shipping_address_line2: Mapped[str | None] = mapped_column(String(120), nullable=True)
    shipping_city: Mapped[str] = mapped_column(String(80), nullable=False)
    shipping_postal_code: Mapped[str] = mapped_column(String(10), nullable=False)
    total_pln: Mapped[int] = mapped_column(Integer, nullable=False)

    shipping_method: Mapped[ShippingMethod] = mapped_column(Enum(ShippingMethod, name="shippingmethod"), nullable=False)
    shipping_cost_pln: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    shipping_country: Mapped[str] = mapped_column(String(2), nullable=False, default="PL")

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


class MediaDB(Base):
    __tablename__ = "media"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(512), nullable=False)
    caption: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class PaymentAttemptDB(Base):
    __tablename__ = "payment_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, default="mock")
    status: Mapped[str] = mapped_column(String(32), default=PaymentStatus.PENDING, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

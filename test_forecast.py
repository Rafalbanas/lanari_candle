import pytest
from datetime import datetime, date, timedelta, UTC
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app as fastapi_app
from app.db.database import Base
from app.db.deps import get_db
from app.api.deps import require_admin
from app.db.models import (
    UserDB,
    CartDB,
    OrderDB,
    OrderItemDB,
    ProductDB,
    OrderStatus,
    ShippingMethod,
)


@pytest.fixture()
def client_db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    admin_user = UserDB(id=1, email="admin@test.com", full_name="Admin", is_active=True, is_admin=True)
    fastapi_app.dependency_overrides[get_db] = override_get_db
    fastapi_app.dependency_overrides[require_admin] = lambda: admin_user

    with TestClient(fastapi_app) as c:
        db = TestingSessionLocal()
        try:
            yield c, db
        finally:
            db.close()

    fastapi_app.dependency_overrides.clear()
    engine.dispose()


def _add_order(db, product: ProductDB, qty: int, created_at: datetime, status: str):
    cart = CartDB()
    db.add(cart)
    db.flush()
    order = OrderDB(
        cart_id=cart.id,
        created_at=created_at,
        status=status,
        email="test@example.com",
        full_name="Test User",
        buyer_first_name="Test",
        buyer_last_name="User",
        buyer_phone="+48500100200",
        buyer_email="test@example.com",
        shipping_address_line1="Kwiatowa 1",
        shipping_address_line2=None,
        shipping_city="Warszawa",
        shipping_postal_code="00-001",
        total_pln=qty * 1000,
        shipping_method=ShippingMethod.PICKUP,
        shipping_cost_pln=0,
        shipping_country="PL",
    )
    db.add(order)
    db.flush()
    item = OrderItemDB(
        order_id=order.id,
        product_id=product.id,
        name=product.name,
        qty=qty,
        unit_price_pln=1000,
        line_total_pln=qty * 1000,
    )
    db.add(item)
    db.commit()


def test_forecast_matches_dow_and_risk(client_db):
    client, db = client_db

    # Products
    p1 = ProductDB(name="P1", description="", price_pln=1000, is_active=True, stock_qty=2)
    p2 = ProductDB(name="P2", description="", price_pln=1000, is_active=True, stock_qty=6)
    db.add_all([p1, p2])
    db.commit()
    db.refresh(p1)
    db.refresh(p2)

    # Target date (Thu)
    target = date(2026, 2, 5)
    th1 = datetime(2026, 1, 29, 12, 0, tzinfo=UTC)  # Thu
    th2 = datetime(2026, 1, 22, 12, 0, tzinfo=UTC)  # Thu
    wed = datetime(2026, 1, 28, 12, 0, tzinfo=UTC)  # Wed (ignore)

    _add_order(db, p1, 2, th1, OrderStatus.PAID)
    _add_order(db, p1, 4, th2, OrderStatus.PAID)
    _add_order(db, p1, 10, wed, OrderStatus.PAID)

    _add_order(db, p2, 5, th1, OrderStatus.PAID)
    _add_order(db, p2, 4, th2, OrderStatus.PAID)

    r = client.get(f"/admin/api/forecast/demand?date={target.isoformat()}&weeks=3&statuses=PAID")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["date"] == target.isoformat()
    items = {i["product_id"]: i for i in data["items"]}

    # P1: only Thurs (2 + 4) / 2 = 3
    p1_out = items[p1.id]
    assert p1_out["samples"] == 2
    assert p1_out["forecast_qty_ceil"] == 3
    assert p1_out["risk"] == "HIGH"  # 3 > stock(2)

    # P2: (5 + 4) / 2 = 4.5 -> ceil 5, stock=6 => MED (5 > 4.2)
    p2_out = items[p2.id]
    assert p2_out["samples"] == 2
    assert p2_out["forecast_qty_ceil"] == 5
    assert p2_out["risk"] == "MED"

    # include zeros -> samples == weeks (3)
    r2 = client.get(f"/admin/api/forecast/demand?date={target.isoformat()}&weeks=3&statuses=PAID&include_zeros=true")
    assert r2.status_code == 200, r2.text
    data2 = r2.json()
    items2 = {i["product_id"]: i for i in data2["items"]}

    p1_out2 = items2[p1.id]
    assert p1_out2["samples"] == 3
    assert p1_out2["forecast_qty_ceil"] == 2  # (2+4+0)/3 = 2.0

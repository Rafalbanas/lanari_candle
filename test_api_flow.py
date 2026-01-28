import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app as fastapi_app
from app.db.database import Base
from app.db.deps import get_db


@pytest.fixture()
def client():
    # Jedna wspólna baza SQLite in-memory dla całego testu (to samo połączenie)
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Tworzymy tabele z modeli na tej testowej bazie
    Base.metadata.create_all(bind=engine)

    # Override dependency get_db -> testowa sesja
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    fastapi_app.dependency_overrides[get_db] = override_get_db

    with TestClient(fastapi_app) as c:
        yield c

    fastapi_app.dependency_overrides.clear()
    engine.dispose()


def test_products_crud_basic(client: TestClient):
    # lista na start pusta
    r = client.get("/api/products")
    assert r.status_code == 200
    assert r.json() == []

    # create product
    payload = {
        "name": "Swieca sojowa - Wanilia",
        "description": "Cieply, slodki zapach.",
        "price_pln": 4990,
        "is_active": True,
    }
    r = client.post("/api/products", json=payload)
    assert r.status_code == 201
    p1 = r.json()
    assert p1["id"] == 1
    assert p1["name"] == payload["name"]

    # get product
    r = client.get("/api/products/1")
    assert r.status_code == 200
    assert r.json()["id"] == 1

    # patch product
    r = client.patch("/api/products/1", json={"price_pln": 5990})
    assert r.status_code == 200
    assert r.json()["price_pln"] == 5990

    # soft-delete
    r = client.delete("/api/products/1")
    assert r.status_code == 204

    # domyślnie active_only=True -> pusto
    r = client.get("/api/products")
    assert r.status_code == 200
    assert r.json() == []

    # active_only=false -> widzimy, ale is_active=false
    r = client.get("/api/products?active_only=false")
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["is_active"] is False


def test_cart_add_update_delete_flow(client: TestClient):
    # Dodaj produkt
    r = client.post(
        "/api/products",
        json={
            "name": "Swieca - Las",
            "description": "Lesne nuty.",
            "price_pln": 5990,
            "is_active": True,
        },
    )
    assert r.status_code == 201
    product_id = r.json()["id"]

    # Utwórz koszyk
    r = client.post("/api/carts")
    assert r.status_code == 201
    cart_id = r.json()["id"]

    # Dodaj do koszyka qty=2
    r = client.post(f"/api/carts/{cart_id}/items", json={"product_id": product_id, "qty": 2})
    assert r.status_code == 201
    cart = r.json()
    assert cart["id"] == cart_id
    assert len(cart["items"]) == 1
    assert cart["items"][0]["qty"] == 2
    assert cart["total_pln"] == 2 * 5990

    item_id = cart["items"][0]["id"]

    # PATCH qty=5
    r = client.patch(f"/api/carts/{cart_id}/items/{item_id}", json={"qty": 5})
    assert r.status_code == 200
    cart = r.json()
    assert cart["items"][0]["qty"] == 5
    assert cart["total_pln"] == 5 * 5990

    # DELETE item
    r = client.delete(f"/api/carts/{cart_id}/items/{item_id}")
    assert r.status_code == 204

    # koszyk pusty
    r = client.get(f"/api/carts/{cart_id}")
    assert r.status_code == 200
    cart = r.json()
    assert cart["items"] == []
    assert cart["total_pln"] == 0


def test_order_creates_and_clears_cart(client: TestClient):
    # Produkt
    r = client.post(
        "/api/products",
        json={
            "name": "Swieca - Bergamotka",
            "description": "Cytrusowa.",
            "price_pln": 6990,
            "is_active": True,
        },
    )
    assert r.status_code == 201
    product_id = r.json()["id"]

    # Koszyk
    r = client.post("/api/carts")
    assert r.status_code == 201
    cart_id = r.json()["id"]

    # Item
    r = client.post(f"/api/carts/{cart_id}/items", json={"product_id": product_id, "qty": 3})
    assert r.status_code == 201
    assert r.json()["total_pln"] == 3 * 6990

    # Zamówienie
    r = client.post(
        "/api/orders",
        json={"cart_id": cart_id, "email": "test@example.com", "full_name": "Rafal Banas"},
    )
    assert r.status_code == 201
    order = r.json()
    assert order["status"] == "NEW"
    assert order["total_pln"] == 3 * 6990
    assert len(order["items"]) == 1
    assert order["items"][0]["qty"] == 3
    assert order["items"][0]["unit_price_pln"] == 6990

    # Koszyk po złożeniu zamówienia powinien być pusty
    r = client.get(f"/api/carts/{cart_id}")
    assert r.status_code == 200
    cart = r.json()
    assert cart["items"] == []
    assert cart["total_pln"] == 0


def test_checkout_idempotency(client: TestClient):
    # produkt
    r = client.post(
        "/api/products",
        json={"name": "Produkt X", "description": "Opis Y", "price_pln": 1000, "is_active": True},
    )
    assert r.status_code == 201, r.text
    pid = r.json()["id"]

    # cart
    r = client.post("/api/carts")
    assert r.status_code == 201, r.text
    cid = r.json()["id"]
    client.post(f"/api/carts/{cid}/items", json={"product_id": pid, "qty": 2})

    payload = {"cart_id": cid, "email":"test@idempotency.com", "full_name":"Test Idempotency"}
    headers = {"Idempotency-Key": "abc-123-unique-key"}

    # First call
    r1 = client.post("/api/checkout", json=payload, headers=headers)
    assert r1.status_code == 201, r1.text
    order_id_1 = r1.json()["id"]

    # Second call (retry) - should return same order
    r2 = client.post("/api/checkout", json=payload, headers=headers)
    assert r2.status_code in (200, 201), r2.text
    assert r2.json()["id"] == order_id_1


def test_cart_add_same_product_increments_qty(client: TestClient):
    # Tworzymy produkt (name > 2 znaki)
    r = client.post("/api/products", json={"name": "Product A", "description": "Desc B", "price_pln": 1000, "is_active": True})
    assert r.status_code == 201, r.text
    pid = r.json()["id"]

    r = client.post("/api/carts")
    assert r.status_code == 201, r.text
    cid = r.json()["id"]

    # Pierwsze dodanie (qty=2)
    r = client.post(f"/api/carts/{cid}/items", json={"product_id": pid, "qty": 2})
    assert r.status_code == 201, r.text
    assert len(r.json()["items"]) == 1
    assert r.json()["items"][0]["qty"] == 2

    # Drugie dodanie tego samego produktu (qty=3) -> powinno zsumować do 5
    r = client.post(f"/api/carts/{cid}/items", json={"product_id": pid, "qty": 3})
    assert r.status_code == 201, r.text
    cart = r.json()
    assert len(cart["items"]) == 1
    assert cart["items"][0]["qty"] == 5
    assert cart["total_pln"] == 5 * 1000
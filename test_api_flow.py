import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app as fastapi_app
from app.db.database import Base
from app.db.deps import get_db
from app.api.deps import get_current_user
from app.db.models import UserDB


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
    r = client.get("/api/cart")
    assert r.status_code == 200
    cart_id = r.json()["id"]

    # Dodaj do koszyka qty=2
    r = client.post("/api/cart/items", json={"product_id": product_id, "qty": 2})
    assert r.status_code == 201
    cart = r.json()
    assert cart["id"] == cart_id
    assert len(cart["items"]) == 1
    assert cart["items"][0]["qty"] == 2
    assert cart["subtotal_pln"] == 2 * 5990
    assert cart["shipping_cost_pln"] == 0

    item_id = cart["items"][0]["id"]

    # PATCH qty=5
    r = client.patch(f"/api/cart/items/{item_id}", json={"qty": 5})
    assert r.status_code == 200
    cart = r.json()
    assert cart["items"][0]["qty"] == 5
    assert cart["subtotal_pln"] == 5 * 5990

    # DELETE item
    r = client.delete(f"/api/cart/items/{item_id}")
    assert r.status_code == 204

    # koszyk pusty
    r = client.get("/api/cart")
    assert r.status_code == 200
    cart = r.json()
    assert cart["items"] == []
    assert cart["subtotal_pln"] == 0


def test_order_creates_and_clears_cart(client: TestClient):
    # Mock auth user
    mock_user = UserDB(id=1, email="test@example.com", full_name="Test User", is_active=True)
    fastapi_app.dependency_overrides[get_current_user] = lambda: mock_user

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
    r = client.get("/api/cart")
    assert r.status_code == 200
    cart_id = r.json()["id"]

    # Item
    r = client.post("/api/cart/items", json={"product_id": product_id, "qty": 3})
    assert r.status_code == 201
    assert r.json()["subtotal_pln"] == 3 * 6990

    # Shipping (pickup free)
    r = client.post(f"/api/cart/shipping?cart_id={cart_id}", json={"shipping_method": "PICKUP"})
    assert r.status_code == 200
    assert r.json()["shipping_cost_pln"] == 0

    # Zamówienie
    r = client.post(
        "/api/orders",
        json={
            "cart_id": cart_id,
            "first_name": "Rafal",
            "last_name": "Banas",
            "phone": "+48500100200",
            "address_line1": "Kwiatowa 1",
            "address_line2": None,
            "city": "Warszawa",
            "postal_code": "00-001",
            "country": "PL",
        },
    )
    assert r.status_code == 201
    order = r.json()
    assert order["status"] == "NEW"
    assert order["total_pln"] == 3 * 6990  # pickup free
    assert len(order["items"]) == 1
    assert order["items"][0]["qty"] == 3
    assert order["items"][0]["unit_price_pln"] == 6990

    # Koszyk po złożeniu zamówienia powinien być pusty
    r = client.get("/api/cart")
    assert r.status_code == 200
    cart = r.json()
    assert cart["items"] == []
    assert cart["subtotal_pln"] == 0
    
    del fastapi_app.dependency_overrides[get_current_user]


def test_checkout_idempotency(client: TestClient):
    # Mock auth user
    mock_user = UserDB(id=1, email="test@idempotency.com", full_name="Test Idempotency", is_active=True)
    fastapi_app.dependency_overrides[get_current_user] = lambda: mock_user

    # produkt
    r = client.post(
        "/api/products",
        json={"name": "Produkt X", "description": "Opis Y", "price_pln": 1000, "is_active": True},
    )
    assert r.status_code == 201, r.text
    pid = r.json()["id"]

    # cart
    r = client.get("/api/cart")
    assert r.status_code == 200, r.text
    cid = r.json()["id"]
    client.post("/api/cart/items", json={"product_id": pid, "qty": 2})

    # set shipping
    client.post(f"/api/cart/shipping?cart_id={cid}", json={"shipping_method": "PICKUP"})

    payload = {
        "cart_id": cid,
        "first_name": "Test",
        "last_name": "Idempotency",
        "phone": "+48555111222",
        "address_line1": "Testowa 2",
        "address_line2": None,
        "city": "Gdansk",
        "postal_code": "80-001",
        "country": "PL",
    }
    headers = {"Idempotency-Key": "abc-123-unique-key"}

    # First call
    r1 = client.post("/api/checkout", json=payload, headers=headers)
    assert r1.status_code == 201, r1.text
    order_id_1 = r1.json()["id"]

    # Second call (retry) - should return same order
    r2 = client.post("/api/checkout", json=payload, headers=headers)
    assert r2.status_code in (200, 201), r2.text
    assert r2.json()["id"] == order_id_1

    del fastapi_app.dependency_overrides[get_current_user]


def test_cart_add_same_product_increments_qty(client: TestClient):
    # Tworzymy produkt (name > 2 znaki)
    r = client.post("/api/products", json={"name": "Product A", "description": "Desc B", "price_pln": 1000, "is_active": True})
    assert r.status_code == 201, r.text
    pid = r.json()["id"]

    r = client.get("/api/cart")
    assert r.status_code == 200, r.text
    cid = r.json()["id"]

    # Pierwsze dodanie (qty=2)
    r = client.post("/api/cart/items", json={"product_id": pid, "qty": 2})
    assert r.status_code == 201, r.text
    assert len(r.json()["items"]) == 1
    assert r.json()["items"][0]["qty"] == 2

    # Drugie dodanie tego samego produktu (qty=3) -> powinno zsumować do 5
    r = client.post("/api/cart/items", json={"product_id": pid, "qty": 3})
    assert r.status_code == 201, r.text
    cart = r.json()
    assert len(cart["items"]) == 1
    assert cart["items"][0]["qty"] == 5
    assert cart["subtotal_pln"] == 5 * 1000


def test_postal_code_validation(client: TestClient):
    mock_user = UserDB(id=1, email="test@validation.com", full_name="Validator", is_active=True)
    fastapi_app.dependency_overrides[get_current_user] = lambda: mock_user

    payload = {
        "first_name": "Jan",
        "last_name": "Kowalski",
        "phone": "+48555111222",
        "address_line1": "Testowa 1",
        "address_line2": None,
        "city": "Warszawa",
        "postal_code": "00123",  # invalid format
        "country": "PL",
        "shipping_method": "PICKUP",
    }

    r = client.post("/api/checkout", json=payload)
    assert r.status_code == 422
    assert "postal_code" in r.text

    del fastapi_app.dependency_overrides[get_current_user]


def test_country_must_be_pl(client: TestClient):
    mock_user = UserDB(id=1, email="test@country.com", full_name="Country Tester", is_active=True)
    fastapi_app.dependency_overrides[get_current_user] = lambda: mock_user

    payload = {
        "first_name": "Jan",
        "last_name": "Kowalski",
        "phone": "+48555111222",
        "address_line1": "Testowa 1",
        "address_line2": None,
        "city": "Warszawa",
        "postal_code": "00-123",
        "country": "DE",  # invalid
        "shipping_method": "PICKUP",
    }

    r = client.post("/api/checkout", json=payload)
    assert r.status_code in (400, 422)

    del fastapi_app.dependency_overrides[get_current_user]


def test_profile_created_and_updated_via_checkout(client: TestClient):
    mock_user = UserDB(id=1, email="profile@test.com", full_name="Profile User", is_active=True)
    fastapi_app.dependency_overrides[get_current_user] = lambda: mock_user

    # product and cart
    r = client.post("/api/products", json={"name": "Profile Prod", "description": "Desc", "price_pln": 1500, "is_active": True})
    assert r.status_code == 201
    pid = r.json()["id"]

    r = client.get("/api/cart")
    cart_id = r.json()["id"]
    client.post("/api/cart/items", json={"product_id": pid, "qty": 1})

    # first checkout -> creates profile
    first_payload = {
        "cart_id": cart_id,
        "first_name": "Jan",
        "last_name": "Kowalski",
        "phone": "+48500100200",
        "address_line1": "Kwiatowa 1",
        "address_line2": None,
        "city": "Warszawa",
        "postal_code": "00-001",
        "country": "PL",
        "shipping_method": "PICKUP",
    }
    r = client.post("/api/checkout", json=first_payload)
    assert r.status_code == 201, r.text

    profile = client.get("/api/me/checkout-profile").json()
    assert profile["first_name"] == "Jan"
    assert profile["postal_code"] == "00-001"

    # Second checkout with updated data -> updates profile
    r = client.post("/api/products", json={"name": "Profile Prod 2", "description": "Desc", "price_pln": 1200, "is_active": True})
    pid2 = r.json()["id"]
    r = client.get("/api/cart")
    cart_id2 = r.json()["id"]
    client.post("/api/cart/items", json={"product_id": pid2, "qty": 2})

    second_payload = {
        "cart_id": cart_id2,
        "first_name": "Anna",
        "last_name": "Nowak",
        "phone": "+48555111222",
        "address_line1": "Lesna 5",
        "address_line2": "m.2",
        "city": "Krakow",
        "postal_code": "30-001",
        "country": "PL",
        "shipping_method": "PICKUP",
    }
    r = client.post("/api/checkout", json=second_payload)
    assert r.status_code == 201, r.text

    updated_profile = client.get("/api/me/checkout-profile").json()
    assert updated_profile["first_name"] == "Anna"
    assert updated_profile["address_line2"] == "m.2"

    del fastapi_app.dependency_overrides[get_current_user]


def test_order_snapshot_independent_from_profile(client: TestClient):
    mock_user = UserDB(id=1, email="snapshot@test.com", full_name="Snapshot User", is_active=True)
    fastapi_app.dependency_overrides[get_current_user] = lambda: mock_user

    # product and cart
    r = client.post("/api/products", json={"name": "Snap Prod", "description": "Desc", "price_pln": 2000, "is_active": True})
    pid = r.json()["id"]
    r = client.get("/api/cart")
    cart_id = r.json()["id"]
    client.post("/api/cart/items", json={"product_id": pid, "qty": 1})

    payload = {
        "cart_id": cart_id,
        "first_name": "Piotr",
        "last_name": "Stary",
        "phone": "+48500999888",
        "address_line1": "Stara 1",
        "address_line2": None,
        "city": "Poznan",
        "postal_code": "60-001",
        "country": "PL",
        "shipping_method": "PICKUP",
    }
    r = client.post("/api/checkout", json=payload)
    assert r.status_code == 201
    order = r.json()
    assert order["buyer_first_name"] == "Piotr"

    # Update profile via another checkout
    r = client.post("/api/products", json={"name": "Snap Prod 2", "description": "Desc", "price_pln": 3000, "is_active": True})
    pid2 = r.json()["id"]
    r = client.get("/api/cart")
    cart_id2 = r.json()["id"]
    client.post("/api/cart/items", json={"product_id": pid2, "qty": 1})

    payload2 = {
        "cart_id": cart_id2,
        "first_name": "Marek",
        "last_name": "Nowy",
        "phone": "+48500666000",
        "address_line1": "Nowa 2",
        "address_line2": None,
        "city": "Gdynia",
        "postal_code": "81-002",
        "country": "PL",
        "shipping_method": "PICKUP",
    }
    r2 = client.post("/api/checkout", json=payload2)
    assert r2.status_code == 201

    # Fetch original order -> snapshot should remain old data
    r3 = client.get(f"/api/orders/{order['id']}")
    assert r3.status_code == 200
    order_after = r3.json()
    assert order_after["buyer_first_name"] == "Piotr"
    assert order_after["buyer_last_name"] == "Stary"
    assert order_after["shipping_address_line1"] == "Stara 1"

    del fastapi_app.dependency_overrides[get_current_user]

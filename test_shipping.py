import pytest
from fastapi.testclient import TestClient

from test_api_flow import client


@pytest.mark.usefixtures("client")
class TestShipping:
    def test_free_shipping_threshold(self, client: TestClient):
        # product above threshold (210 PLN)
        r = client.post(
            "/api/products",
            json={"name": "Duza swieca", "description": "", "price_pln": 21000, "is_active": True},
        )
        assert r.status_code == 201, r.text
        pid = r.json()["id"]

        cart = client.get("/api/cart").json()
        cart_id = cart["id"]

        client.post("/api/cart/items", json={"product_id": pid, "qty": 1})

        r = client.get(f"/api/shipping/methods?cart_id={cart_id}")
        assert r.status_code == 200, r.text
        data = r.json()
        locker = next(m for m in data["methods"] if m["method"] == "INPOST_LOCKER")
        courier = next(m for m in data["methods"] if m["method"] == "COURIER")
        assert locker["cost_pln"] == 0 and locker["is_free"]
        assert courier["cost_pln"] == 0 and courier["is_free"]

        r = client.post(f"/api/cart/shipping?cart_id={cart_id}", json={"shipping_method": "INPOST_LOCKER"})
        assert r.status_code == 200, r.text
        assert r.json()["shipping_cost_pln"] == 0

    def test_pickup_always_zero(self, client: TestClient):
        r = client.post(
            "/api/products",
            json={"name": "Mala swieca", "description": "", "price_pln": 1000, "is_active": True},
        )
        assert r.status_code == 201, r.text
        pid = r.json()["id"]

        cart = client.get("/api/cart").json()
        cart_id = cart["id"]
        client.post("/api/cart/items", json={"product_id": pid, "qty": 1})

        r = client.post(f"/api/cart/shipping?cart_id={cart_id}", json={"shipping_method": "PICKUP"})
        assert r.status_code == 200, r.text
        assert r.json()["shipping_cost_pln"] == 0

    def test_invalid_method_returns_400(self, client: TestClient):
        cart_id = client.get("/api/cart").json()["id"]
        r = client.post(f"/api/cart/shipping?cart_id={cart_id}", json={"shipping_method": "DRONE"})
        assert r.status_code == 400

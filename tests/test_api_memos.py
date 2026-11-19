import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models.memo import Memo


@pytest.fixture
def client():
    return TestClient(app)


def test_api_dashboard_metrics(client):
    response = client.get("/api/v1/reports/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_memos" in data
    assert "pending_review" in data
    assert "total_spent_bdt" in data


def test_api_products_list(client):
    response = client.get("/api/v1/products")
    assert response.status_code == 200
    products = response.json()
    assert len(products) > 0
    names = [p["name"] for p in products]
    assert any("Sunscreen" in n for n in names)


def test_api_suppliers_list(client):
    response = client.get("/api/v1/suppliers")
    assert response.status_code == 200
    suppliers = response.json()
    assert any("K Color Cosmetics" in s["name"] for s in suppliers)


def test_api_memo_details(client):
    db = SessionLocal()
    memo = db.query(Memo).first()
    db.close()
    assert memo is not None

    response = client.get(f"/api/v1/memos/{memo.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["memo_number"] == "3508"
    assert len(data["lines"]) == 8


def test_api_ask_data(client):
    response = client.post("/api/v1/ask-data", json={"query": "কে কালার কসমেটিক্স থেকে কত টাকার মাল কিনেছি?"})
    assert response.status_code == 200
    data = response.json()
    assert data["error"] is None
    assert "K Color Cosmetics" in data["answer"] or "total" in data["answer"].lower()

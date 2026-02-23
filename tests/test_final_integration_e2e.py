import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app, get_db
from app.database import Base
from app import models

# 1. KONFIGURACJA BAZY (In-Memory)
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

# Używamy klienta, ale override zrobimy w fixture
client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_database():
    """Przygotowuje środowisko przed testem."""
    app.dependency_overrides[get_db] = override_get_db
    
    # Tworzymy tabele
    Base.metadata.create_all(bind=engine)
    
    # Dodajemy dane
    db = TestingSessionLocal()
    
    # Produkt
    product = models.Product(
        id=10,
        name="Stempel E2E",
        category="Testowe",
        unit_cost=100.0,
        current_stock=1000,
        lead_time_days=5,
        average_daily_consumption=10.0,
        unit="szt"
    )
    
    # Dostawca - POPRAWKA: Usunięto wszystkie pola, których nie ma w models.py
    # Zostawiamy tylko te, które są zdefiniowane w klasie Supplier
    supplier = models.Supplier(
        id=1, 
        name="Dostawca Testowy", 
        contact_email="test@test.com"
    )
    
    db.add(supplier)
    db.add(product)
    db.commit()
    db.close()
    
    yield
    
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()

def test_full_system_integration_flow():
    """
    [E2E] Weryfikacja pełnego procesu: Zamówienie -> Wykrycie Anomalii -> Zapis.
    """
    payload = {
        "product_id": 10,
        "quantity": 100,
        "total_price": 10000.0,
        "supplier_id": 1,
        "order_type": "KOSZT/JIT"
    }

    res = client.post("/orders", json=payload)
    
    if res.status_code != 200:
        print(f"\n[DEBUG ERROR] Kod: {res.status_code}, Treść: {res.text}")

    assert res.status_code == 200, "Błąd tworzenia zamówienia (oczekiwano 200 OK)"
    
    order_data = res.json()
    assert "ai_metadata" in order_data
    assert order_data["id"].startswith("ORD-")
    
    history_res = client.get("/orders")
    assert history_res.status_code == 200
    all_orders = history_res.json()
    
    found = any(o["id"] == order_data["id"] for o in all_orders)
    assert found is True, "Zamówienie nie zapisało się w bazie!"
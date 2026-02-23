import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app, get_db
from app.database import Base
from app import models

# Konfiguracja bazy w pamięci (izolowana)
engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_persistence_db():
    """Fixture, który przygotowuje bazę i nadpisuje zależność."""
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    
    # Dodajemy produkt ID=1, którego test potrzebuje
    db = TestingSessionLocal()
    p = models.Product(
        id=1, 
        name="Produkt Testowy", 
        category="Test", 
        unit_cost=10.0, 
        current_stock=100
    )
    db.add(p)
    db.commit()
    db.close()
    
    yield
    
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()

@patch("app.main.anomaly_detector.is_anomaly")
def test_order_persistence_ai_flags(mock_is_anomaly: MagicMock):
    """
    [Weryfikacja Persystencji]
    Sprawdza, czy po wykryciu anomalii pola 'is_anomaly' są obecne w bazie.
    """
    mock_is_anomaly.return_value = True

    payload = {
        "product_id": 1, # Teraz ten produkt istnieje!
        "quantity": 5000,
        "total_price": 50000.0,
        "order_type": "standard"
    }

    # 1. Tworzymy zamówienie
    response = client.post("/orders", json=payload)
    
    if response.status_code != 200:
        print(f"[DEBUG] Error: {response.text}")

    assert response.status_code == 200
    order_id = response.json()["id"]

    # 2. Pobieramy je z bazy, by sprawdzić flagi
    history_res = client.get("/orders")
    assert history_res.status_code == 200
    orders = history_res.json()
    
    target_order = next((o for o in orders if o["id"] == order_id), None)
    assert target_order is not None
    assert target_order["is_anomaly"] is True
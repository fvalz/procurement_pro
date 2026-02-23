import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app, get_db
from app.database import Base
from app import models

# STATICPOOL + :memory: to klucz do stabilności na Windows
engine = create_engine(
    "sqlite:///:memory:", 
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    # Dodajemy produkt, który test za chwilę kupi
    db.add(models.Product(id=10, name="Stempel", category="X", unit_cost=100, current_stock=50, average_daily_consumption=1))
    db.commit()
    yield
    # Nie musimy usuwać pliku, bo baza jest w RAM - zero PermissionError!

def test_full_system_integration_flow():
    # 1. Kupujemy produkt ID 10
    res = client.post("/orders", json={"product_id": 10, "quantity": 100, "total_price": 10000})
    assert res.status_code == 200
    data = res.json()
    
    # 2. Sprawdzamy czy AI zadziałało (100 sztuk to anomalia przy burn=1)
    assert data["is_anomaly"] is True
    assert "ai_metadata" in data
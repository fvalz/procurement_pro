import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session

# Importy z Twojej aplikacji
from app.main import app, get_db
from app import models

def override_get_db_persistence():
    """Atrapa bazy danych dla testu zapisu."""
    db = MagicMock(spec=Session)
    
    # Mock produktu i kontraktu, aby przejść walidację w main.py
    mock_product = models.Product(
        id=1, 
        name="Testowy Produkt", 
        unit_cost=10.0, 
        current_stock=100,
        lead_time_days=7
    )
    mock_contract = models.Contract(
        id=1, 
        price=10.0, 
        is_active=True, 
        supplier_id=1,
        payment_terms_days=30
    )
    
    def mock_query(model):
        q = MagicMock()
        if model == models.Product:
            q.filter.return_value.first.return_value = mock_product
        elif model == models.Contract:
            q.filter.return_value.order_by.return_value.first.return_value = mock_contract
        return q

    db.query.side_effect = mock_query
    yield db

# Podmiana zależności
app.dependency_overrides[get_db] = override_get_db_persistence
client = TestClient(app)

@patch("app.main.anomaly_detector.is_anomaly")
def test_order_persistence_ai_flags(mock_is_anomaly: MagicMock):
    """
    [Weryfikacja Persystencji]
    Sprawdza, czy po wykryciu anomalii pola 'is_anomaly' i 'anomaly_score'
    są obecne w strukturze danych wysyłanej do bazy.
    """
    # 1. Konfigurujemy AI, by zgłosiło anomalię
    mock_is_anomaly.return_value = True
    
    payload = {
        "product_id": 1,
        "quantity": 5000,
        "total_price": 50000.0,
        "order_type": "standard"
    }
    
    # 2. Wywołujemy endpoint
    response = client.post("/orders", json=payload)
    
    # 3. Sprawdzamy odpowiedź
    assert response.status_code == 200
    data = response.json()
    
    # Weryfikujemy, czy API zwróciło nowe pola (serializacja ze schemas.py)
    assert "is_anomaly" in data, "Pole 'is_anomaly' nieobecne w odpowiedzi API."
    assert data["is_anomaly"] is True, "AI wykryło anomalię, ale pole w bazie/API ma wartość False."
    assert "anomaly_score" in data, "Pole 'anomaly_score' nieobecne w odpowiedzi API."
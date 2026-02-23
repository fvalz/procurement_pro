import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session

# Importy z aplikacji
from app.main import app, get_db
from app import models

def override_get_db():
    """
    Zastępuje prawdziwą sesję bazy danych obiektem Mock.
    Gwarantuje, że testy API nie zmodyfikują produkcyjnej/deweloperskiej bazy.
    """
    db = MagicMock(spec=Session)
    
    # Przygotowanie wirtualnych danych dla endpointu zamówień
    mock_product = models.Product(
        id=1, name="Stempel Ø10", unit_cost=50.0, lead_time_days=7
    )
    mock_contract = models.Contract(
        id=1, product_id=1, supplier_id=1, price=45.0, 
        payment_terms_days=14, is_active=True
    )
    
    # Symulacja zapytań ORM (łańcuchowanie wywołań)
    def mock_query(model):
        query_mock = MagicMock()
        if model == models.Product:
            query_mock.filter.return_value.first.return_value = mock_product
        elif model == models.Contract:
            query_mock.filter.return_value.order_by.return_value.first.return_value = mock_contract
        elif model == models.Order:
            query_mock.all.return_value = []  # Dla endpointu trenowania zwracamy pustą listę zamówień
        return query_mock

    db.query.side_effect = mock_query
    yield db

# Podmiana zależności w uruchomionej instancji FastAPI
app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

@patch("app.main.anomaly_detector.is_anomaly")
def test_create_order_injects_ai_metadata(mock_is_anomaly: MagicMock) -> None:
    """
    [Weryfikacja API & MLOps]
    Sprawdza, czy endpoint tworzenia zamówienia poprawnie mierzy czas inferencji
    (Inference Time) i dołącza ustrukturyzowane metadane AI do odpowiedzi JSON.
    """
    # Wymuszamy, aby model nie zablokował tego konkretnego zamówienia
    mock_is_anomaly.return_value = False
    
    payload = {
        "product_id": 1,
        "supplier_id": 1,
        "quantity": 100,
        "total_price": 4500.0,
        "status": "pending",
        "payment_terms_days": 30,
        "order_type": "standard",
        "delay_days": 0
    }
    
    response = client.post("/orders", json=payload)
    
    assert response.status_code == 200, f"Endpoint zwrócił błąd: {response.text}"
    data = response.json()
    
    # Walidacja obecności bloku analitycznego
    assert "ai_metadata" in data, "Zabrakło pola ai_metadata w głównym obiekcie JSON."
    assert data["ai_metadata"] is not None, "Pole ai_metadata jest null."
    
    metadata = data["ai_metadata"]
    
    # Weryfikacja struktury metadanych (MLOps)
    assert "inference_time_ms" in metadata, "Brak pomiaru czasu działania modelu (Inference Time)."
    assert type(metadata["inference_time_ms"]) in [float, int], "Czas predykcji ma błędny typ danych."
    assert metadata["is_flagged"] is False, "Status oflagowania nie zgadza się z wynikiem modelu."
    assert metadata["engine"] == "IsolationForest_v2.1", "Błędna sygnatura silnika AI."

def test_trigger_ai_training_background_task() -> None:
    """
    [Wymagania Niefunkcjonalne - WNF]
    Weryfikuje, czy endpoint zlecający ciężki trening modelu odpowiada
    natychmiastowo, poprawnie zlecając operację do FastAPI BackgroundTasks.
    """
    response = client.post("/system/ai/retrain")
    
    assert response.status_code == 200, "Serwer nie przyjął żądania treningu."
    data = response.json()
    
    # Oczekujemy natychmiastowego zwrotu statusu 'processing' bez czekania na koniec pętli uczącej
    assert data["status"] == "processing", "Endpoint zablokował wątek zamiast zwrócić status 'processing'."
    assert "WNF" in data["architecture_note"], "Zabrakło notatki dokumentacyjnej o asynchroniczności."
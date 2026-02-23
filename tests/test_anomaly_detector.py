import pytest
import logging
import numpy as np
from unittest.mock import MagicMock, patch

# Importujemy klasę, a nie gotowy singleton, aby każdy test miał "czystą kartę"
from app.services.anomaly_detector import AnomalyDetector


@pytest.fixture
def isolated_detector() -> AnomalyDetector:
    """
    Dostarcza świeżą, nietrenowaną instancję detektora dla każdego testu.
    Gwarantuje to brak wycieków stanu między testami.
    """
    detector = AnomalyDetector()
    detector.is_trained = False
    detector.model = None
    detector.training_stats = {}
    return detector


@pytest.fixture
def mock_historical_orders() -> list:
    """
    Generuje syntetyczny zbiór danych historycznych (15 zamówień).
    Symulujemy stabilne dostawy: Ilość=10, Cena~100 PLN, Cena Jednostkowa~10 PLN.
    """
    orders = []
    for i in range(15):
        mock_order = MagicMock()
        mock_order.quantity = 10
        mock_order.total_price = 100.0 + (i * 2.0)  # Niewielka wariancja ceny całkowitej
        mock_order.contract_price = 10.0
        orders.append(mock_order)
    return orders


def test_deterministic_contract_validation(isolated_detector: AnomalyDetector) -> None:
    """
    [Reguła Twarda] Weryfikuje, czy system natychmiast blokuje zamówienie,
    jeśli cena jednostkowa przekracza cenę kontraktową o ponad 15%,
    nawet jeśli model ML nie jest jeszcze wytrenowany.
    """
    # Scenariusz: Zamawiamy 10 sztuk za 1500 PLN (Cena jedn. = 150 PLN)
    # Kontrakt przewiduje 100 PLN. 150 PLN to 50% przebicia (> 15%).
    is_anomaly = isolated_detector.is_anomaly(
        quantity=10, 
        total_price=1500, 
        contract_price=100
    )
    
    assert is_anomaly is True, "System przepuścił drastyczne przepłacenie poza kontraktem!"


def test_model_training_and_feature_extraction(isolated_detector: AnomalyDetector, mock_historical_orders: list) -> None:
    """
    [Uczenie Maszynowe] Sprawdza, czy proces treningu poprawnie ekstrahuje 
    4 wymiary cech (Feature Engineering) oraz oblicza statystyki XAI.
    """
    isolated_detector.train(mock_historical_orders)
    
    assert isolated_detector.is_trained is True, "Model nie zmienił flagi na is_trained=True."
    assert isolated_detector.model is not None, "Obiekt IsolationForest nie został zainicjalizowany."
    
    # Mamy 4 cechy: Ilość, Cena Całkowita, Cena Jednostkowa, Odchylenie od Kontraktu
    assert len(isolated_detector.training_stats) == 4, "Błąd w wymiarowości macierzy statystyk XAI."
    
    # Weryfikacja logiki matematycznej (cena jednostkowa dla pierwszego elementu to 100/10 = 10.0)
    # Średnia cena jednostkowa (indeks 2) powinna oscylować wokół 10.0 - 11.5
    assert 10.0 <= isolated_detector.training_stats[2]["mean"] <= 12.0


def test_xai_reasoning_generation(isolated_detector: AnomalyDetector, mock_historical_orders: list, caplog: pytest.LogCaptureFixture) -> None:
    """
    [Explainable AI] Zmusza model do oflagowania transakcji i przechwytuje logi,
    aby zweryfikować czy system XAI podaje inżynieryjne uzasadnienie w konsoli.
    """
    # 1. Trenujemy model syntetycznymi danymi
    isolated_detector.train(mock_historical_orders)
    
    # 2. Wstrzykujemy (mockujemy) decyzję modelu ML, wymuszając wynik anomalii (-1)
    with patch.object(isolated_detector.model, 'predict', return_value=np.array([-1])):
        
        with caplog.at_level(logging.WARNING):
            
            # ZMIANA: quantity=10 (zgodne ze średnią historyczną).
            # Dzięki temu wariancja dla ilości to 0, a model XAI skupi się na 
            # niewyobrażalnie wysokiej cenie całkowitej/jednostkowej.
            result = isolated_detector.is_anomaly(quantity=10, total_price=99000, contract_price=None)
            
            assert result is True, "Model zablokowany na -1 nie zwrócił True."
            
            # Weryfikacja wyjścia tekstowego XAI
            log_output = caplog.text
            assert "Zablokowano transakcję! Uzasadnienie modelu:" in log_output
            
            # Sprawdzamy, czy system wymienia nazwy cech z naszego wektora (teraz zdominuje go cena)
            assert "Cena Jednostkowa" in log_output or "Cena Całkowita" in log_output
            assert "% wpływu" in log_output
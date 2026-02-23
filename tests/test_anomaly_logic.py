import pytest
import random
from unittest.mock import MagicMock
from app.services.anomaly_detector import AnomalyDetector
from app import models

@pytest.fixture
def trained_detector():
    """Fixture przygotowujący detektor z realistycznym zróżnicowaniem danych."""
    detector = AnomalyDetector()
    
    training_data = []
    # Generujemy 50 zamówień z lekkim szumem (normalny rozkład)
    for i in range(50):
        qty = random.uniform(8, 12) # Norma ok. 10
        price_unit = random.uniform(48, 52) # Norma ok. 50
        
        order = MagicMock(spec=models.Order)
        order.quantity = qty
        order.total_price = qty * price_unit
        order.is_anomaly = False
        
        # Symulacja relacji kontraktu dla metody train
        contract = MagicMock(spec=models.Contract)
        contract.price = 50.0
        contract.is_active = True
        
        product = MagicMock(spec=models.Product)
        product.contracts = [contract]
        order.product = product
        
        training_data.append(order)
    
    detector.train(training_data)
    return detector

def test_normal_order(trained_detector):
    """Testuje zamówienie w granicach normy statystycznej."""
    # Ilość 11 (blisko 10), Cena 550 (jedn. 50)
    is_anom = trained_detector.is_anomaly(quantity=11, total_price=550.0, contract_price=50.0)
    assert is_anom is False

def test_hard_rule_price_anomaly(trained_detector):
    """Testuje blokadę twardą (cena > 20% kontraktu)."""
    # Cena jedn. 70 przy kontrakcie 50 (+40%)
    is_anom = trained_detector.is_anomaly(quantity=10, total_price=700.0, contract_price=50.0)
    assert is_anom is True

def test_statistical_anomaly(trained_detector):
    """Testuje wykrycie anomalii skali przez AI."""
    # Ilość 500 to 50-krotność normy (10). 
    # Nawet jeśli cena jednostkowa (51) jest OK, AI widzi izolację punktu w przestrzeni Quantity/Total.
    is_anom = trained_detector.is_anomaly(quantity=500, total_price=25500.0, contract_price=50.0)
    assert is_anom is True
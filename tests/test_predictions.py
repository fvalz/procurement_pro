import pytest
from unittest.mock import MagicMock, patch
from typing import List, Dict, Any
from sqlalchemy.orm import Session

# Importy z aplikacji
from app.main import get_ai_predictions
from app.models import Product, Order

@pytest.fixture
def mock_db() -> MagicMock:
    """
    Przygotowuje fałszywą sesję bazy danych (Mock) z jednym produktem
    w stanie stabilnym, bez nadchodzących zamówień.
    
    Returns:
        MagicMock: Zamockowana instancja sesji bazy danych.
    """
    db_session = MagicMock(spec=Session)
    
    # Tworzenie sztucznego produktu do testów
    mock_product = Product(
        id=1,
        name="Stempel Ø10",
        current_stock=100,
        average_daily_consumption=10.0, # Zapas wystarczy na 10 dni
        lead_time_days=7
    )
    
    # Konfiguracja łańcucha zapytań (Query Chain Mocking)
    # 1. db.query(Product).all() -> zwraca nasz produkt
    mock_product_query = MagicMock()
    mock_product_query.all.return_value = [mock_product]
    
    # 2. db.query(Order).filter(...).all() -> zwraca pustą listę (brak zamówień w drodze)
    mock_order_query = MagicMock()
    mock_order_query.filter.return_value.all.return_value = []
    
    # Mapowanie zapytań do odpowiednich modeli
    def side_effect(model: Any) -> MagicMock:
        if model == Product:
            return mock_product_query
        elif model == Order:
            return mock_order_query
        raise ValueError("Nieobsługiwany model w teście")
        
    db_session.query.side_effect = side_effect
    return db_session


@patch("app.main.random.gauss")
def test_probabilistic_threshold_adaptation(mock_gauss: MagicMock, mock_db: MagicMock) -> None:
    """
    Weryfikuje, czy system poprawnie zmienia status na 'warning', gdy 
    model stochastyczny przewiduje opóźnienie w łańcuchu dostaw.
    """
    # SCENARIUSZ 1: Idealna dostawa (Rozkład Gaussa zwraca dokładnie Lead Time = 7)
    mock_gauss.return_value = 7.0
    
    results_ideal: List[Dict[str, Any]] = get_ai_predictions(limit=10, db=mock_db)
    
    assert len(results_ideal) == 1
    # Zapas 10 dni, idealny LT to 7, bufor = 7 * 0.5 = 3.5. Próg: 10.5. 
    # Dni do końca (10) < 10.5, więc nawet w idealnym scenariuszu jest to już "warning" (stan ostrzegawczy).
    assert results_ideal[0]["status"] == "warning", "Błąd obliczania progu dla idealnej dostawy."
    assert results_ideal[0]["restock_recommended"] is True

    # SCENARIUSZ 2: Spore opóźnienie (Rozkład Gaussa zwraca Lead Time = 11)
    mock_gauss.return_value = 11.0
    
    results_delayed: List[Dict[str, Any]] = get_ai_predictions(limit=10, db=mock_db)
    
    # Próg ostrzegawczy z wariancją:
    # LT (7) + Odchylenie (11-7=4) + Bufor (11 * 0.5 = 5.5) = 16.5
    # Dni zapasu (10) <= Próg (16.5) -> głęboki warning
    assert results_delayed[0]["status"] == "warning", "System nie wykrył zagrożenia przy wariancji opóźnienia."
    
    # Weryfikacja dokładności odwołań
    assert mock_gauss.call_count == 2
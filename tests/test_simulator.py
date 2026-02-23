import pytest
from unittest.mock import patch
from app.services.simulator import LogisticsSimulator

@pytest.fixture
def simulator() -> LogisticsSimulator:
    """Instancja symulatora do testów."""
    return LogisticsSimulator()

def test_monte_carlo_zero_stock(simulator: LogisticsSimulator) -> None:
    """
    [Przypadek brzegowy / Edge Case] 
    Weryfikuje, czy algorytm zwraca dokładnie 100% ryzyka przerwania 
    ciągłości produkcji, gdy na magazynie nie ma fizycznie towaru.
    """
    risk = simulator.run_monte_carlo_stockout_risk(
        current_stock=0.0, 
        daily_burn=50.0, 
        lead_time=7
    )
    assert risk == 100.0, "Błąd: Ryzyko przy pustym magazynie musi wynosić 100%."

@patch('app.services.simulator.random.gauss')
@patch('app.services.simulator.random.uniform')
def test_monte_carlo_deterministic_stockout(mock_uniform: patch, mock_gauss: patch, simulator: LogisticsSimulator) -> None:
    """
    [Weryfikacja Stochastyki] 
    Testuje deterministycznie logikę algorytmu Monte Carlo. Zamrażamy zmienne 
    losowe, by upewnić się, że matematyka wyliczana wewnątrz pętli jest poprawna.
    """
    # Symulujemy pesymistyczne opóźnienie: transport jedzie 10 dni (zamiast np. 7)
    mock_gauss.return_value = 10.0
    
    # Symulujemy nagły skok popytu na linii produkcyjnej o 15%
    mock_uniform.return_value = 1.15

    # Bazowe dzienne zużycie to 10 sztuk
    daily_burn = 10.0
    
    # Oczekiwana konsumpcja wg algorytmu: 10 dni * 10 sztuk * 1.15 (skok popytu) = 115 sztuk.
    
    # SCENARIUSZ A: Magazyn ma 100 sztuk.
    # W każdej ze 100 iteracji symulacji towaru zabraknie (100 < 115).
    risk_high = simulator.run_monte_carlo_stockout_risk(
        current_stock=100.0, 
        daily_burn=daily_burn, 
        lead_time=7, 
        iterations=50
    )
    assert risk_high == 100.0, "Matematyka zawiodła: Algorytm nie wykrył 100% ryzyka braku zapasów."

    # SCENARIUSZ B: Magazyn ma 120 sztuk.
    # W każdej ze 100 iteracji towaru wystarczy (120 > 115).
    risk_low = simulator.run_monte_carlo_stockout_risk(
        current_stock=120.0, 
        daily_burn=daily_burn, 
        lead_time=7, 
        iterations=50
    )
    assert risk_low == 0.0, "Matematyka zawiodła: Algorytm fałszywie zgłosił ryzyko mimo odpowiedniego bufora."
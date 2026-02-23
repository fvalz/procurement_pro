import pytest
from types import SimpleNamespace
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from app.main import app, get_db

def override_get_db_scripted():
    """
    Mock "Scenariuszowy". 
    Zamiast analizować zapytania SQL, po prostu zwraca dane w ustalonej kolejności.
    To omija wszelkie problemy z filtrami, typami klas i importami.
    """
    db_mock = MagicMock()

    # 1. PRZYGOTOWANIE PRODUKTÓW
    # Muszą być "bogatymi" mockami, żeby Pydantic (schemas.Product) ich nie odrzucił
    p1 = MagicMock()
    p1.id = 1
    p1.name = "Stempel"
    p1.category = "Tnące"
    p1.unit_cost = 10.0
    p1.current_stock = 5
    p1.lead_time_days = 3
    p1.unit = "szt"
    p1.average_daily_consumption = 1.0
    # Ważne: musimy oszukać SQLAlchemy, że to nie jest lista, tylko obiekt
    p1.__table__ = MagicMock() 

    p2 = MagicMock()
    p2.id = 2
    p2.name = "Matryca"
    p2.category = "Tnące"
    p2.unit_cost = 20.0
    p2.current_stock = 5
    p2.lead_time_days = 3
    p2.unit = "szt"
    p2.average_daily_consumption = 1.0
    p2.__table__ = MagicMock()

    # 2. DEFINICJA SCENARIUSZA (Iterator)
    # Pierwsze wywołanie .all() zwróci listę produktów.
    # Następne 50 wywołań (dla kontraktów) zwróci pustą listę.
    scenario = [[p1, p2]] + [[] for _ in range(50)]
    scenario_iterator = iter(scenario)

    def side_effect_all():
        try:
            return next(scenario_iterator)
        except StopIteration:
            return []

    # 3. KONFIGURACJA MOCKA ZAPYTANIA
    # Tworzymy uniwersalny obiekt query, który "połyka" wszystkie metody (.filter, .limit...)
    # i zwraca samego siebie, aż do momentu wywołania .all()
    query_mock = MagicMock()
    query_mock.filter.return_value = query_mock
    query_mock.limit.return_value = query_mock
    query_mock.offset.return_value = query_mock
    query_mock.order_by.return_value = query_mock
    
    # Podpinamy nasz scenariusz pod .all()
    query_mock.all.side_effect = side_effect_all

    # Każde wywołanie db.query(...) zwraca ten sam query_mock
    db_mock.query.return_value = query_mock
    
    yield db_mock

# Podmiana zależności
app.dependency_overrides[get_db] = override_get_db_scripted
client = TestClient(app)

@patch("app.main.ai_search.search")
def test_read_products_semantic_integration(mock_search):
    """
    [INTEGRACJA] Test scenariuszowy (Scripted Mock).
    Niezależny od bazy danych, filtrów SQL i wersji bibliotek.
    """
    
    # 1. Mockujemy AI
    # Main.py używa: product_ids = [p.id for p in ai_matched_products]
    # Więc wystarczy SimpleNamespace z id.
    mock_search.return_value = {
        "results": [SimpleNamespace(id=1), SimpleNamespace(id=2)],
        "max_score": 0.95
    }
    
    # 2. Wywołujemy endpoint
    # Wewnątrz endpointu:
    # 1. db.query(Product)...all() -> Mock zwraca [p1, p2] (z iteratora)
    # 2. Pętla po produktach:
    #    db.query(Contract)...all() -> Mock zwraca [] (z iteratora)
    response = client.get("/products?search=narzedzie")
    
    # 3. Weryfikacja
    assert response.status_code == 200
    data = response.json()
    
    # Debug krytyczny
    if len(data) != 2:
        print(f"\n[CRITICAL ERROR] Otrzymano: {data}")

    assert len(data) == 2, "Endpoint musi zwrócić 2 produkty ze scenariusza!"
    assert data[0]["id"] == 1
    assert data[0]["name"] == "Stempel"
    assert data[1]["id"] == 2
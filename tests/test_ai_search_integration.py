import pytest
from unittest.mock import patch
from types import SimpleNamespace
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Importujemy aplikację i modele
from app.main import app, get_db
from app.database import Base
from app import models

def test_read_products_semantic_integration():
    """
    [INTEGRACJA 100%]
    Testuje pełną ścieżkę: Endpoint -> AI (Mock) -> Baza (SQLite RAM) -> Response.
    Wszystko dzieje się lokalnie w teście, co gwarantuje izolację.
    """

    # 1. KONFIGURACJA BAZY DANYCH (Tylko dla tego testu)
    # Używamy pamięci RAM, żeby było szybko i czysto
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Tworzymy tabele
    Base.metadata.create_all(bind=engine)

    # 2. SEEDING (Zasilamy bazę danymi)
    # Dodajemy produkty, które za chwilę "znajdzie" AI
    db_session = TestingSessionLocal()
    
    # Tworzymy produkty z PEŁNYM zestawem pól, żeby uniknąć błędów walidacji Pydantic
    p1 = models.Product(
        id=1, 
        name="Stempel", 
        category="Tnące", 
        unit_cost=10.0, 
        current_stock=5, 
        lead_time_days=3, 
        unit="szt", 
        average_daily_consumption=1.0,
        description="Opis 1"
    )
    p2 = models.Product(
        id=2, 
        name="Matryca", 
        category="Tnące", 
        unit_cost=20.0, 
        current_stock=5, 
        lead_time_days=3, 
        unit="szt", 
        average_daily_consumption=1.0,
        description="Opis 2"
    )
    
    db_session.add(p1)
    db_session.add(p2)
    db_session.commit()
    db_session.close()

    # 3. NADPISANIE ZALEŻNOŚCI (Dependency Override)
    # To sprawia, że endpoint /products użyje naszej bazy w RAM
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    
    # Tworzymy klienta API
    client = TestClient(app)

    # 4. MOCKOWANIE AI I WYKONANIE TESTU
    # Patchujemy funkcję search w module app.main.ai_search
    with patch("app.main.ai_search.search") as mock_search:
        # Symulujemy odpowiedź AI - zwracamy obiekty z atrybutem ID
        # main.py robi: [p.id for p in results], więc SimpleNamespace(id=X) wystarczy
        mock_search.return_value = {
            "results": [SimpleNamespace(id=1), SimpleNamespace(id=2)],
            "max_score": 0.95
        }

        # Strzał do API
        response = client.get("/products?search=narzedzie")

        # 5. WERYFIKACJA
        assert response.status_code == 200
        data = response.json()

        # Debug w razie problemów
        if len(data) != 2:
            print(f"\n[DEBUG] Baza zawierała produkty ID: 1, 2")
            print(f"[DEBUG] AI zwróciło ID: 1, 2")
            print(f"[DEBUG] API zwróciło: {data}")

        assert len(data) == 2, "API powinno zwrócić 2 produkty z bazy in-memory"
        
        # Sprawdzamy konkretne dane
        assert data[0]["id"] == 1
        assert data[0]["name"] == "Stempel"
        assert data[1]["id"] == 2
        assert data[1]["name"] == "Matryca"

    # Sprzątanie (opcjonalne, bo override jest lokalny dla app w pamięci, ale dobra praktyka)
    app.dependency_overrides.clear()
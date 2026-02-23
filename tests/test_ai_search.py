import pytest
from unittest.mock import MagicMock, patch
from typing import List

# Importujemy nasz serwis z pominięciem ładowania wagi modelu
from app.services.ai_search import AISearchService

@pytest.fixture
def mock_products() -> List[MagicMock]:
    """
    Syntetyczna baza asortymentowa przygotowana na potrzeby weryfikacji 
    wstrzykiwania logiki domenowej (kategorii).
    """
    prod1 = MagicMock()
    prod1.id = 1
    prod1.name = "Śruba M8"
    prod1.category = "Elementy złączne"

    prod2 = MagicMock()
    prod2.id = 2
    prod2.name = "Wkręt do drewna"
    prod2.category = "Elementy złączne"

    prod3 = MagicMock()
    prod3.id = 3
    prod3.name = "Młotek"
    prod3.category = "Narzędzia ręczne"

    return [prod1, prod2, prod3]

@patch('app.services.ai_search.SentenceTransformer')
def test_hybrid_search_category_weighting(mock_transformer_class: MagicMock, mock_products: List[MagicMock]) -> None:
    """
    [Hybrid Search] Weryfikuje matematyczną modyfikację rankingu SBERT.
    Sprawdza, czy premia kategorialna (+0.15) potrafi przełamać czyste 
    podobieństwo kosinusowe i wypromować produkt z tej samej dziedziny.
    """
    # 1. Izolacja instancji
    search_service = AISearchService()
    search_service.model = MagicMock()  # Omijamy ciężki model NLP
    search_service.products_cache = mock_products
    search_service.embeddings = MagicMock()

    # 2. Symulacja błędu sieci neuronowej (tzw. zjawisko Halucynacji Semantycznej)
    # Wyobraźmy sobie zapytanie: "metalowy wbijak". 
    # Czysty model SBERT uznaje, że Młotek (id:2) pasuje na 0.35, a Wkręt (id:1) na 0.34.
    mock_raw_hits = [[
        {'corpus_id': 2, 'score': 0.35},  # Młotek (inna kategoria)
        {'corpus_id': 1, 'score': 0.34},  # Wkręt (docelowa kategoria)
    ]]

    with patch('app.services.ai_search.util.semantic_search', return_value=mock_raw_hits):
        
        # Wymuszamy poszukiwania w kontekście dziedziny "Elementy złączne"
        response = search_service.search("metalowy element", target_category="Elementy złączne", top_k=2)

        results = response["results"]

        # 3. Weryfikacja logiczna:
        # Młotek -> 0.35 (brak premii, inna dziedzina)
        # Wkręt -> 0.34 + 0.15 (premia Hybrid Search) = 0.49
        # Wniosek: Wkręt musi zająć pierwsze miejsce w tablicy wynikowej.
        
        assert len(results) == 2, "Metoda search nie zwróciła poprawnej liczby elementów."
        assert results[0].name == "Wkręt do drewna", "Algorytm Hybrid Search nie zaaplikował wagi dziedzinowej!"
        assert response["max_score"] == 0.49, "Błąd w kalkulacji matematycznej maksymalnego wyniku (max_score)."


@patch('app.services.ai_search.SentenceTransformer')
def test_confidence_score_low_match(mock_transformer_class: MagicMock, mock_products: List[MagicMock]) -> None:
    """
    [Confidence Score] Testuje moduł asertywności sieci neuronowej.
    System musi umieć przyznać się do błędu, jeśli nie znajdzie nic 
    powyżej progu ufności (0.40).
    """
    search_service = AISearchService()
    search_service.model = MagicMock()
    search_service.products_cache = mock_products
    search_service.embeddings = MagicMock()

    # Symulujemy zwrot bardzo słabych wektorów z przestrzeni wielowymiarowej (szum)
    mock_raw_hits = [[
        {'corpus_id': 0, 'score': 0.30},
        {'corpus_id': 1, 'score': 0.28},
    ]]

    with patch('app.services.ai_search.util.semantic_search', return_value=mock_raw_hits):
        
        response = search_service.search("całkowicie losowy ciąg znaków", target_category=None)

        assert "Nie znaleziono precyzyjnego dopasowania" in response["confidence_message"], \
            "System sztucznej inteligencji nie poinformował o niskiej pewności (brak alertu)!"
        assert response["max_score"] == 0.30, "System źle wyekstrahował bazowy wynik prawdopodobieństwa."
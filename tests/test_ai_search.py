import logging
import os
import pickle
import numpy as np
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer, util

# Konfiguracja loggera
logger = logging.getLogger("AISearch")

class AISearchService:
    """
    Zaawansowany silnik wyszukiwania semantycznego (Semantic Search Engine).
    Wykorzystuje model wielojęzyczny do obsługi zapytań w języku polskim.
    Implementuje podejście Hybrid Search (Vector + Keyword Boost).
    """
    
    # ZMIANA 1: Używamy modelu Multilingual, który lepiej radzi sobie z polskim
    MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
    CACHE_FILE = "embeddings_cache.pkl"

    def __init__(self):
        self.model = None
        self.products_metadata = []
        self.embeddings = None
        self.is_ready = False
        self._load_model()

    def _load_model(self):
        try:
            logger.info(f"🧠 [AI SEARCH] Ładowanie modelu NLP: {self.MODEL_NAME}...")
            self.model = SentenceTransformer(self.MODEL_NAME)
            self.is_ready = True
            logger.info("✅ [AI SEARCH] Model załadowany. Gotowy do pracy.")
        except Exception as e:
            logger.error(f"❌ [AI SEARCH] Błąd ładowania modelu: {e}")
            self.is_ready = False

    def index_products(self, products: List[Any]) -> None:
        """
        Tworzy indeks wektorowy dla listy produktów.
        Łączy nazwę, kategorię i opis, aby AI miało pełny kontekst.
        """
        if not self.is_ready or not products:
            return

        logger.info(f"🔄 [AI SEARCH] Indeksowanie {len(products)} produktów...")
        
        # Przygotowanie metadanych (id, nazwa, kategoria) do szybkiego dostępu
        self.products_metadata = [
            {
                "id": p.id,
                "name": p.name,
                "category": p.category,
                "description": getattr(p, "description", "") or ""
            }
            for p in products
        ]

        # ZMIANA 2: Rich Context - wektoryzujemy nie tylko nazwę, ale też kategorię i opis
        # To pozwala znaleźć "Beton" wpisując "materiał budowlany"
        texts_to_embed = [
            f"{p.category} {p.name} {getattr(p, 'description', '') or ''}" 
            for p in products
        ]

        # Generowanie embeddingów (batch processing dla wydajności)
        self.embeddings = self.model.encode(texts_to_embed, convert_to_tensor=True, show_progress_bar=False)
        
        # Zapisz cache (opcjonalnie, dla szybszego restartu w przyszłości)
        self._save_cache()
        logger.info("✅ [AI SEARCH] Indeksowanie zakończone.")

    def search(self, query: str, target_category: Optional[str] = None, top_k: int = 5, threshold: float = 0.25) -> Dict[str, Any]:
        """
        Wykonuje wyszukiwanie hybrydowe.
        1. Oblicza podobieństwo kosinusowe (Vector Search).
        2. Dodaje bonus punktowy za dokładne wystąpienie słów kluczowych (Keyword Boost).
        3. Filtruje wyniki poniżej progu (threshold), aby usunąć szum.
        """
        if not self.is_ready or self.embeddings is None:
            logger.warning("⚠️ [AI SEARCH] Silnik niegotowy lub pusty indeks.")
            return {"results": [], "message": "Search engine not ready"}

        # 1. Wektoryzacja zapytania
        query_embedding = self.model.encode(query, convert_to_tensor=True)

        # 2. Obliczenie podobieństwa (Cosine Similarity)
        # util.cos_sim zwraca macierz [[score1, score2, ...]]
        cos_scores = util.cos_sim(query_embedding, self.embeddings)[0]

        # Konwersja do listy CPU numpy dla łatwej obróbki
        scores = cos_scores.cpu().numpy()

        results = []
        query_lower = query.lower()
        query_words = query_lower.split()

        for idx, score in enumerate(scores):
            meta = self.products_metadata[idx]
            final_score = float(score)

            # Filtrowanie po kategorii (Hard Filter)
            if target_category and meta["category"] != target_category:
                continue

            # ZMIANA 3: Hybrid Keyword Boost
            # Jeśli słowo z zapytania występuje w nazwie produktu -> podbijamy wynik.
            # To naprawia sytuację, gdzie wektorowo coś jest blisko, ale użytkownik szukał konkretu.
            name_lower = meta["name"].lower()
            if query_lower in name_lower:
                final_score += 0.3  # Duży bonus za dokładną frazę
            else:
                for word in query_words:
                    if len(word) > 2 and word in name_lower:
                        final_score += 0.1  # Mały bonus za pojedyncze słowo

            # ZMIANA 4: Odsiewanie szumu (Threshold)
            # Jeśli po wszystkich bonusach wynik jest nadal niski, ignorujemy go.
            if final_score >= threshold:
                results.append({
                    "id": meta["id"],
                    "name": meta["name"],
                    "category": meta["category"],
                    "score": round(final_score, 4),
                    "is_ai_match": True
                })

        # Sortowanie malejąco po wyniku
        results = sorted(results, key=lambda x: x["score"], reverse=True)
        
        return {
            "query": query,
            "count": len(results[:top_k]),
            "results": results[:top_k]
        }

    def _save_cache(self):
        try:
            with open(self.CACHE_FILE, "wb") as f:
                pickle.dump({"metadata": self.products_metadata, "embeddings": self.embeddings}, f)
        except Exception:
            pass # Cache jest opcjonalny, nie przerywamy w razie błędu I/O

# Singleton - jedna instancja na całą aplikację
ai_search = AISearchService()
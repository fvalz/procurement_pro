import os
import joblib
import logging
from sentence_transformers import SentenceTransformer, util
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# WNF2: Stała ścieżka do pamięci podręcznej wektorów
CACHE_FILE = "embeddings_cache.pkl"

class AISearchService:
    """
    Ekspercki system wyszukiwania semantycznego (SBERT).
    Implementuje Hybrid Search (Wagi dziedzinowe), Caching wektorów (Optymalizacja WNF2) 
    oraz analizę poziomu ufności (Confidence Score).
    """

    def __init__(self) -> None:
        self.model: Optional[SentenceTransformer] = None
        self.embeddings: Any = None
        self.products_cache: List[Any] = []
        
        try:
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("🧠 [AI SEARCH] Sieć neuronowa SBERT zainicjalizowana pomyślnie.")
        except Exception as e:
            logger.error(f"❌ [AI SECURITY] Błąd ładowania rdzenia NLP: {e}")

    def index_products(self, products: List[Any]) -> None:
        """
        Zarządza wektoryzacją asortymentu. Wdraża mechanizm Caching Embeddings, 
        aby ominąć barierę obliczeniową CPU przy ponownych startach serwera.
        """
        if not self.model or not products:
            return
        
        self.products_cache = products
        current_ids = [p.id for p in products]
        
        # 1. Odczyt z pamięci podręcznej (Caching Embeddings)
        if os.path.exists(CACHE_FILE):
            try:
                cached_data = joblib.load(CACHE_FILE)
                cached_ids = cached_data.get("ids", [])
                
                # Zabezpieczenie integralności: Wczytujemy cache tylko, jeśli baza się nie zmieniła
                if cached_ids == current_ids:
                    self.embeddings = cached_data["embeddings"]
                    logger.info("⚡ [AI SEARCH] Wczytano wektory z cache. Zoptymalizowano czas startu (WNF2).")
                    return
                else:
                    logger.info("🔄 [AI SEARCH] Wykryto zmianę w asortymencie. Wymagana reindeksacja.")
            except Exception as e:
                logger.warning(f"⚠️ [AI SEARCH] Odrzucono uszkodzony cache wektorów: {e}")

        # 2. Generowanie nowych wektorów (jeśli brak cache lub baza uległa zmianie)
        descriptions = [f"{p.name} {p.category}" for p in products]
        
        logger.info(f"🧠 [AI SEARCH] Trwa mapowanie wektorowe dla {len(products)} produktów...")
        self.embeddings = self.model.encode(descriptions, convert_to_tensor=True)
        
        # 3. Zapis do pamięci podręcznej
        try:
            joblib.dump({"embeddings": self.embeddings, "ids": current_ids}, CACHE_FILE)
            logger.info("💾 [AI SEARCH] Zapisano nową macierz wektorów na dysk.")
        except Exception as e:
            logger.error(f"❌ [AI SEARCH] Nie udało się zapisać pamięci podręcznej: {e}")

    def search(self, query: str, target_category: Optional[str] = None, top_k: int = 5) -> Dict[str, Any]:
        """
        Wyszukiwanie wykorzystujące algorytm Hybrid Search.
        Łączy matematyczne podobieństwo kosinusowe z logiką biznesową (wagi kategorii).
        """
        if self.model is None or self.embeddings is None:
            return {"results": [], "confidence_message": "Brak zainicjalizowanego modelu NLP.", "max_score": 0.0}

        query_embedding = self.model.encode(query, convert_to_tensor=True)
        
        # Pobieramy większą pulę do przefiltrowania przez Hybrid Search
        raw_hits = util.semantic_search(query_embedding, self.embeddings, top_k=top_k * 3)[0]
        
        scored_results = []
        for hit in raw_hits:
            product = self.products_cache[hit['corpus_id']]
            base_score = float(hit['score'])
            
            # HYBRID SEARCH: Wzmacnianie wagi dziedzinowej
            if target_category and product.category.lower() == target_category.lower():
                base_score += 0.15  # Algorytmiczne faworyzowanie tej samej rodziny produktów
                
            scored_results.append((base_score, product))
        
        # Ponowne sortowanie według ulepszonej wagi (malejąco)
        scored_results.sort(key=lambda x: x[0], reverse=True)
        
        final_products = []
        best_score = 0.0
        
        for score, product in scored_results[:top_k]:
            if score > best_score:
                best_score = score
            if score > 0.25:  # Absolutne minimum użyteczności
                final_products.append(product)

        # CONFIDENCE SCORE (Próg ufności)
        confidence_msg = "Znaleziono precyzyjne dopasowanie."
        if len(final_products) == 0:
            confidence_msg = "Brak wyników spełniających minimalne kryteria semantyczne."
        elif best_score < 0.40:
            confidence_msg = f"Nie znaleziono precyzyjnego dopasowania (Max Ufność: {best_score:.2f}). Sugeruję weryfikację ręczną."

        return {
            "results": final_products,
            "confidence_message": confidence_msg,
            "max_score": best_score
        }

    def find_alternatives(self, product_name: str, category: str, top_k: int = 3) -> Dict[str, Any]:
        """
        Deleguje logikę szukania zamienników do głównego silnika Hybrid Search.
        """
        query = f"{product_name} {category}"
        
        # Używamy ulepszonej metody search, podając kategorię celu
        search_response = self.search(query=query, target_category=category, top_k=top_k + 1)
        
        alternatives = []
        for prod in search_response["results"]:
            if prod.name != product_name:
                alternatives.append(prod)
                
        # Zwracamy spójny obiekt ze zaktualizowanym statusem ufności
        return {
            "results": alternatives[:top_k],
            "confidence_message": search_response["confidence_message"],
            "max_score": search_response["max_score"]
        }

# Inicjalizacja instancji Singleton
ai_search = AISearchService()
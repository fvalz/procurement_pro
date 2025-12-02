from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from app import schemas

class AISearchService:
    def __init__(self):
        print("🧠 [AI] Inicjalizacja serwisu...")
        self.model = None
        self.product_vectors = None
        self.products_cache = [] 
        
        try:
            from sentence_transformers import SentenceTransformer
            # Model 'all-MiniLM-L6-v2'
            self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            print("✅ [AI] Model załadowany pomyślnie!")
        except Exception as e:
            print(f"⚠️ [AI-ERROR] Nie udało się pobrać modelu: {e}")
            self.model = None

    def index_products(self, products: list[schemas.Product]):
        """Zapisuje produkty i tworzy ich wektory"""
        self.products_cache = products
        
        if not products:
            print("⚠️ [AI] Otrzymano pustą listę produktów do indeksowania!")
            return

        if self.model:
            try:
                print(f"🧠 [AI] Indeksowanie {len(products)} produktów...")
                # Tworzymy bogatsze opisy dla lepszego dopasowania
                descriptions = [f"{p.name} {p.category} {p.name}" for p in products]
                self.product_vectors = self.model.encode(descriptions)
                print("✅ [AI] Produkty zaindeksowane i gotowe do szukania!")
            except Exception as e:
                print(f"❌ [AI] Błąd indeksowania: {e}")
        else:
            print("ℹ️ [AI] Brak modelu - indeksowanie pominięte.")

    def search(self, query: str, top_k: int = 10) -> list[schemas.Product]:
        """Szuka produktów z logowaniem diagnostycznym"""
        # 1. Sprawdzenie czy mamy w czym szukać
        if not self.products_cache:
            print("❌ [AI-SEARCH] Pusty cache produktów! Sprawdź startup_event w main.py")
            return []

        print(f"🔍 [AI-SEARCH] Zapytanie: '{query}'")

        # 2. TRYB AI
        if self.model and self.product_vectors is not None:
            try:
                query_vector = self.model.encode([query])
                similarities = cosine_similarity(query_vector, self.product_vectors)[0]
                
                # Sortowanie wyników
                top_indices = similarities.argsort()[-top_k:][::-1]
                
                results = []
                print(f"📊 [AI-DEBUG] Top 3 dopasowania dla '{query}':")
                
                for i, idx in enumerate(top_indices[:3]):
                    score = similarities[idx]
                    prod = self.products_cache[idx]
                    print(f"   {i+1}. {prod.name} (Score: {score:.4f})")

                # Filtracja z niższym progiem (0.1)
                for idx in top_indices:
                    if similarities[idx] > 0.1:  # <--- OBNIŻONY PRÓG
                        results.append(self.products_cache[idx])
                
                if not results:
                    print("⚠️ [AI-SEARCH] Znaleziono dopasowania, ale zbyt słabe (< 0.1).")
                
                return results
            except Exception as e:
                print(f"❌ [AI] Błąd obliczeń: {e}")

        # 3. FALLBACK (Jeśli AI zawiedzie lub zwróci pusto, spróbujmy po słowach)
        print("🔍 [FALLBACK] Uruchamiam proste szukanie tekstowe...")
        query_parts = query.lower().split()
        results = []
        for p in self.products_cache:
            # Sprawdź czy którakolwiek część zapytania (np. "pisania") jest w nazwie
            if any(part in p.name.lower() for part in query_parts if len(part) > 2):
                results.append(p)
        
        return results[:top_k]

# Singleton
ai_search = AISearchService()
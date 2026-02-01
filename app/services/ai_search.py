from sentence_transformers import SentenceTransformer, util
import logging

logger = logging.getLogger(__name__)

class AISearchService:
    def __init__(self):
        # Pobieramy lekki i szybki model NLP (działa na CPU)
        try:
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("🧠 [AI SEARCH] Model NLP załadowany poprawnie.")
        except Exception as e:
            logger.error(f"❌ [AI SEARCH] Błąd ładowania modelu: {e}")
            self.model = None

        self.products_cache = []
        self.embeddings = None

    def index_products(self, products: list):
        """Tworzy wektory (embeddings) dla wszystkich produktów przy starcie"""
        if not self.model or not products:
            return
        
        self.products_cache = products
        # Tworzymy opisy do wektoryzacji: "Laptop Dell XPS elektronika biurowa"
        descriptions = [f"{p.name} {p.category}" for p in products]
        
        logger.info(f"🧠 [AI SEARCH] Tworzenie wektorów dla {len(products)} produktów...")
        self.embeddings = self.model.encode(descriptions, convert_to_tensor=True)
        logger.info("✅ [AI SEARCH] Indeksowanie zakończone.")

    def search(self, query: str, top_k: int = 5):
        """Wyszukuje produkty na podstawie zapytania tekstowego"""
        if self.model is None or self.embeddings is None:
            return []

        # Zamień zapytanie użytkownika na wektor
        query_embedding = self.model.encode(query, convert_to_tensor=True)

        # Oblicz podobieństwo (Cosine Similarity)
        hits = util.semantic_search(query_embedding, self.embeddings, top_k=top_k)
        
        # Zwróć pasujące obiekty produktów
        results = []
        for hit in hits[0]:
            if hit['score'] > 0.25: # Próg trafności (żeby nie pokazywać śmieci)
                product = self.products_cache[hit['corpus_id']]
                results.append(product)
        
        return results

    def find_alternatives(self, product_name: str, category: str, top_k: int = 3):
        """
        Szuka zamienników dla danego produktu.
        To jest ta metoda, której brakowało i powodowała błąd 500!
        """
        if self.model is None or self.embeddings is None:
            return []

        # Tworzymy zapytanie bazujące na nazwie szukanego produktu
        query = f"{product_name} {category}"
        query_embedding = self.model.encode(query, convert_to_tensor=True)

        # Szukamy podobnych (pobieramy k+1, bo pierwszym wynikiem będzie ten sam produkt)
        hits = util.semantic_search(query_embedding, self.embeddings, top_k=top_k + 1)
        
        alternatives = []
        for hit in hits[0]:
            found_product = self.products_cache[hit['corpus_id']]
            # Ignoruj produkt o tej samej nazwie (nie chcemy polecać tego samego jako zamiennika)
            if found_product.name != product_name:
                alternatives.append(found_product)
        
        # Zwracamy tylko top_k wyników
        return alternatives[:top_k]

# Singleton
ai_search = AISearchService()
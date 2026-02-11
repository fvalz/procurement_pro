import os
import sys
import random
import uuid
import logging
from datetime import datetime, timedelta

# Konfiguracja logowania - staranny, inżynierski format
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Ustawienie ścieżek dostępu do modułów aplikacji
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from app.database import SessionLocal
    from app import models
except ImportError as e:
    logger.error(f"Krytyczny błąd importu: {e}. Upewnij się, że skrypt jest w folderze głównym.")
    sys.exit(1)

def run_initialization():
    print("\n" + "="*60)
    print("🛠️  ZAAWANSOWANA INICJALIZACJA SYSTEMU PROCUREMENT PRO")
    print("="*60)
    
    db = SessionLocal()
    
    try:
        # 1. Weryfikacja danych startowych
        products = db.query(models.Product).all()
        suppliers = db.query(models.Supplier).all()

        if not products or not suppliers:
            logger.error("Baza danych jest pusta! Uruchom najpierw 'recreate_db.py'.")
            return

        # 2. GENEROWANIE WIELOWYMIAROWYCH KONTRAKTÓW (Multi-Sourcing)
        print(f"📦 KROK 1: Tworzenie sieci kontraktów (Multi-Sourcing)...")
        for product in products:
            # Każdy produkt ma od 1 do 3 dostawców (konkurencja rynkowa)
            num_contracts = random.randint(1, 3)
            available_suppliers = random.sample(suppliers, k=min(len(suppliers), num_contracts))
            
            for supplier in available_suppliers:
                # Symulacja negocjacji: cena kontraktowa vs rynkowa (unit_cost)
                # 80% szans na dobry kontrakt (taniej), 20% na zły (do renegocjacji)
                is_overpriced = random.random() < 0.2
                modifier = random.uniform(1.10, 1.30) if is_overpriced else random.uniform(0.85, 0.95)
                
                new_contract = models.Contract(
                    supplier_id=supplier.id,
                    product_id=product.id,
                    price=round(product.unit_cost * modifier, 2),
                    valid_from=datetime.now() - timedelta(days=random.randint(60, 120)),
                    valid_until=datetime.now() + timedelta(days=random.randint(30, 180)),
                    payment_terms_days=random.choice([14, 30, 45, 60]),
                    is_active=True,
                    penalty_clause_details="Zgodnie z ogólnymi warunkami zakupu (OWZ)."
                )
                db.add(new_contract)

        # 3. GENEROWANIE HISTORII ZAMÓWIEŃ DLA MODELI AI
        print(f"📈 KROK 2: Generowanie historii operacyjnej (Trening dla AI)...")
        # Generujemy ok. 150 zamówień, aby Isolation Forest miał bazę statystyczną
        for i in range(150):
            product = random.choice(products)
            # Normalna ilość zamówienia kręci się wokół min_stock_level
            normal_qty = random.randint(int(product.min_stock_level), int(product.min_stock_level * 2))
            
            # Pobieramy cenę z aktywnego kontraktu
            contract = db.query(models.Contract).filter_by(product_id=product.id).first()
            price = contract.price if contract else product.unit_cost

            history_order = models.Order(
                id=f"HIST-{uuid.uuid4().hex[:8].upper()}",
                product_id=product.id,
                supplier_id=contract.supplier_id if contract else None,
                quantity=float(normal_qty),
                total_price=round(normal_qty * price, 2),
                status="delivered",
                order_type="manual",
                created_at=datetime.now() - timedelta(days=random.randint(1, 90)),
                payment_terms_days=30
            )
            db.add(history_order)

        # 4. WSTRZYKIWANIE "PROBLEMÓW" (Demonstracja siły AI)
        print("🚨 KROK 3: Wstrzykiwanie anomalii i celowych błędów...")
        
        # ANOMALIA 1: Gigantyczne zamówienie (Błąd ludzki / Próba nadużycia)
        p1 = random.choice(products)
        db.add(models.Order(
            id="ERR-QTY-999", product_id=p1.id, quantity=10000.0, 
            total_price=round(10000 * p1.unit_cost, 2), status="pending_approval",
            order_type="manual", created_at=datetime.now()
        ))

        # ANOMALIA 2: Cena jednostkowa "z kosmosu" (Błąd w systemie dostawcy)
        p2 = random.choice(products)
        db.add(models.Order(
            id="ERR-PRC-888", product_id=p2.id, quantity=5.0, 
            total_price=round(p2.unit_cost * 500, 2), status="pending_approval",
            order_type="manual", created_at=datetime.now()
        ))

        # SCENARIUSZ RENEGOCJACJI: Bardzo drogi kontrakt kończący się za chwilę
        p3 = random.choice(products)
        db.add(models.Contract(
            supplier_id=suppliers[0].id,
            product_id=p3.id,
            price=round(p3.unit_cost * 2.5, 2), # 250% ceny rynkowej
            valid_from=datetime.now() - timedelta(days=100),
            valid_until=datetime.now() + timedelta(days=5), # Kończy się zaraz!
            is_active=True
        ))

        db.commit()
        print("\n" + "="*60)
        print("✨ PROCES ZAKOŃCZONY POMYŚLNIE")
        print(f"   - Kontrakty wygenerowane (w tym multi-sourcing)")
        print(f"   - Historia zamówień gotowa do analizy Isolation Forest")
        print(f"   - Przygotowano scenariusze do renegocjacji dla AI")
        print("="*60)

    except Exception as e:
        db.rollback()
        logger.error(f"Wystąpił błąd podczas inicjalizacji: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_initialization()
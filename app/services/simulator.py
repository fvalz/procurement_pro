import asyncio
import logging
import random
import uuid
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app import models, database

# Konfiguracja loggera - to wygląda profesjonalnie w konsoli
logger = logging.getLogger(__name__)

# Stałe konfiguracyjne (dobre praktyki inżynierskie - nie używamy "magic numbers")
EMA_ALPHA = 0.1          # Współczynnik wygładzania (waga nowych danych)
SPIKE_CHANCE = 0.05      # 5% szans na nagły skok popytu
CONSUMPTION_CHANCE = 0.4 # 40% szans, że produkt w ogóle "ruszy" danego dnia

class SimulationService:
    def __init__(self):
        self.current_date = datetime.now()
        self.is_running = False
        self.simulation_speed = 1.0 

    def get_status(self):
        return {
            "current_date": self.current_date.strftime("%Y-%m-%d"),
            "is_running": self.is_running
        }

    async def run_engine(self):
        """
        Główny silnik symulacji (asynchroniczna pętla).
        To ta metoda jest uruchamiana przez przycisk w React.
        """
        logger.info("🚀 [SIMULATOR] Silnik symulacji uruchomiony.")
        
        while self.is_running:
            # 1. Pobieramy nową sesję bazy danych dla każdego cyklu
            # (Ważne: sesja musi być zamykana po każdym dniu, żeby nie zapchać puli połączeń)
            db = database.SessionLocal()
            try:
                self.run_daily_cycle(db)
            except Exception as e:
                logger.error(f"❌ [SIMULATOR] Błąd krytyczny w cyklu: {e}")
            finally:
                db.close()

            # 2. Czekamy 1 sekundę (1 sekunda realna = 1 dzień wirtualny)
            await asyncio.sleep(1.0 / self.simulation_speed)
        
        logger.info("🛑 [SIMULATOR] Silnik zatrzymany.")

    def run_daily_cycle(self, db: Session):
        """Logika biznesowa jednego dnia symulacji"""
        
        # 1. Upływ czasu
        self.current_date += timedelta(days=1)
        # logger.info(f"📅 [SYMULACJA] Przetwarzanie dnia: {self.current_date.strftime('%Y-%m-%d')}")

        # 2. Zużycie + Uczenie się (AI Learning - EMA)
        products = db.query(models.Product).filter(models.Product.current_stock > 0).all()
        
        for product in products:
            daily_consumption = 0
            
            # Stochastyczna symulacja popytu
            if random.random() < CONSUMPTION_CHANCE:
                # Scenariusz: Nagły skok (Spike)
                if random.random() < SPIKE_CHANCE: 
                    daily_consumption = random.randint(5, 20)
                    logger.warning(f"🔥 [SPIKE] Nagły skok popytu na {product.name}: -{daily_consumption} szt.")
                # Scenariusz: Normalne zużycie
                else:
                    daily_consumption = max(1, int(product.current_stock * 0.05), random.randint(1, 3))
                
                # Aktualizacja stanu
                new_stock = max(0, product.current_stock - daily_consumption)
                product.current_stock = new_stock
            
            # --- ALGORYTM EMA (Exponential Moving Average) ---
            # Aktualizacja prognozy średniego zużycia
            current_avg = product.average_daily_consumption or 1.0
            new_avg = (current_avg * (1 - EMA_ALPHA)) + (daily_consumption * EMA_ALPHA)
            product.average_daily_consumption = new_avg

        # 3. Dostawy (Przyjmowanie towaru)
        # Szukamy zamówień, których data dostawy właśnie minęła lub jest dzisiaj
        pending_orders = db.query(models.Order).filter(
            models.Order.status == "ordered",
            models.Order.estimated_delivery <= self.current_date
        ).all()

        for order in pending_orders:
            order.status = "delivered"
            if order.product:
                order.product.current_stock += order.quantity
                logger.info(f"📦 [DOSTAWA] Przyjęto {order.quantity} szt. produktu {order.product.name}")

        # 4. Auto-Replenishment (Bot Zakupowy)
        low_stock_products = db.query(models.Product).filter(
            models.Product.current_stock <= models.Product.min_stock_level
        ).all()

        for p in low_stock_products:
            # Sprawdź, czy już nie ma aktywnego zamówienia (żeby nie dublować)
            active_order = db.query(models.Order).filter(
                models.Order.product_id == p.id, 
                models.Order.status.in_(["ordered", "pending_approval"])
            ).first()
            
            if not active_order:
                # Logika zamawiania: (Min Level * 2) - Current
                qty_to_order = max(10, (p.min_stock_level * 2) - p.current_stock)
                
                # Wybór dostawcy (Fix: Musimy przypisać supplier_id!)
                # Pobieramy pierwszego lepszego dostawcę lub domyślnego
                supplier = db.query(models.Supplier).first()
                supplier_id = supplier.id if supplier else None

                # Obliczenie ceny na podstawie ceny produktu (Fix: Zamiast sztywnego 50.0)
                total_price = float(p.unit_cost) * qty_to_order

                new_ord = models.Order(
                    id=f"AUTO-{uuid.uuid4().hex[:6].upper()}",
                    product_id=p.id,
                    supplier_id=supplier_id, # Przypisanie dostawcy
                    quantity=qty_to_order,
                    total_price=total_price,
                    status="ordered",
                    order_type="automatic",
                    created_at=self.current_date,
                    estimated_delivery=self.current_date + timedelta(days=p.lead_time_days)
                )
                db.add(new_ord)
                logger.info(f"🤖 [BOT] Generuję zamówienie: {p.name} | Ilość: {qty_to_order}")

        # 5. Zapis statystyk (dla wykresów w Rozdziale 4)
        total_items = sum(p.current_stock for p in db.query(models.Product).all())
        stat = models.DailyStats(
            date=self.current_date, 
            total_items=int(total_items), 
            low_stock_count=len(low_stock_products), 
            pending_orders=len(pending_orders) # Tylko liczba nowych
        )
        db.add(stat)

        # Zatwierdzenie wszystkich zmian w bazie
        db.commit()

# Singleton
simulator = SimulationService()
import asyncio
import logging
import random
import uuid
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app import models, database

logger = logging.getLogger(__name__)

# Parametry symulacji
EMA_ALPHA = 0.1          
SPIKE_CHANCE = 0.05      
CONSUMPTION_CHANCE = 0.4 

class SimulationService:
    def __init__(self):
        self.current_date = datetime.now()
        self.is_running = False
        self.simulation_speed = 1.0 
        self.recent_events = [] # <--- TU JEST KLUCZ: Lista zdarzeń dla Frontendu

    def log_event(self, message: str, level: str = "info"):
        """Magiczna funkcja: pisze do konsoli ORAZ zapisuje dla Reacta"""
        # 1. Konsola (CMD)
        if level == "warning":
            logger.warning(message)
            icon = "🔥"
        elif level == "error":
            logger.error(message)
            icon = "❌"
        elif "DOSTAWA" in message:
            logger.info(message)
            icon = "🚚"
        elif "BOT" in message:
            logger.info(message)
            icon = "🤖"
        else:
            logger.info(message)
            icon = "ℹ️"

        # 2. Pamięć (React)
        timestamp = self.current_date.strftime("%Y-%m-%d")
        # Dodajemy na początek listy (najnowsze na górze)
        self.recent_events.insert(0, {
            "id": uuid.uuid4().hex,
            "date": timestamp,
            "message": message,
            "icon": icon,
            "type": level
        })
        
        # Trzymamy tylko 50 ostatnich, żeby nie zapchać RAMu
        if len(self.recent_events) > 50:
            self.recent_events.pop()

    def get_status(self):
        return {
            "current_date": self.current_date.strftime("%Y-%m-%d"),
            "is_running": self.is_running,
            "events": self.recent_events # <--- Frontend to odczyta!
        }

    async def run_engine(self):
        self.log_event("🚀 SILNIK URUCHOMIONY", "info")
        while self.is_running:
            db = database.SessionLocal()
            try:
                self.run_daily_cycle(db)
            except Exception as e:
                self.log_event(f"Błąd krytyczny: {str(e)}", "error")
            finally:
                db.close()
            await asyncio.sleep(1.0)
        self.log_event("⏹️ SILNIK ZATRZYMANY", "info")

    def run_daily_cycle(self, db: Session):
        self.current_date += timedelta(days=1)

        # 1. Zużycie
        products = db.query(models.Product).filter(models.Product.current_stock > 0).all()
        for product in products:
            if random.random() < CONSUMPTION_CHANCE: 
                # Spikes
                if random.random() < SPIKE_CHANCE:
                    spike_qty = random.randint(5, 20)
                    product.current_stock = max(0, product.current_stock - spike_qty)
                    self.log_event(f"Nagły skok popytu na {product.name}: -{spike_qty} szt.", "warning")
                else:
                    consumption = random.randint(1, 5)
                    product.current_stock = max(0, product.current_stock - consumption)
                
                # EMA Learning
                avg = product.average_daily_consumption or 1.0
                product.average_daily_consumption = (avg * 0.9) + (1 * 0.1)

        # 2. Dostawy
        pending = db.query(models.Order).filter(
            models.Order.status == "ordered", 
            models.Order.estimated_delivery <= self.current_date
        ).all()
        
        for order in pending:
            order.status = "delivered"
            if order.product:
                order.product.current_stock += order.quantity
                # Używamy nowej funkcji log_event zamiast zwykłego print/logger
                self.log_event(f"Dostawa: {order.product.name} (+{int(order.quantity)})")

        # 3. Auto-Replenishment (Bot)
        low_stock = db.query(models.Product).filter(
            models.Product.current_stock <= models.Product.min_stock_level
        ).all()

        for p in low_stock:
            active = db.query(models.Order).filter(
                models.Order.product_id == p.id, 
                models.Order.status.in_(["ordered", "pending_approval"])
            ).first()
            
            if not active:
                qty = max(10, (p.min_stock_level * 2) - p.current_stock)
                
                # Bezpieczne pobieranie ceny (Fix z poprzedniego kroku)
                price = 50.0
                try:
                    if hasattr(p, 'unit_cost') and p.unit_cost: price = float(p.unit_cost)
                    elif hasattr(p, 'unit_price') and p.unit_price: price = float(p.unit_price)
                except: pass
                
                total = price * qty
                
                new_ord = models.Order(
                    id=f"AUTO-{uuid.uuid4().hex[:6].upper()}",
                    product_id=p.id,
                    quantity=qty,
                    total_price=total,
                    status="ordered",
                    created_at=self.current_date,
                    estimated_delivery=self.current_date + timedelta(days=p.lead_time_days or 3),
                    payment_terms_days=30
                )
                db.add(new_ord)
                self.log_event(f"BOT Zamawia: {p.name} ({int(qty)} szt.)")

        # 4. Statystyki
        total_items = sum(p.current_stock for p in db.query(models.Product).all())
        stat = models.DailyStats(
            date=self.current_date, 
            total_items=int(total_items), 
            low_stock_count=len(low_stock), 
            pending_orders=len(pending)
        )
        db.add(stat)
        db.commit()

simulator = SimulationService()
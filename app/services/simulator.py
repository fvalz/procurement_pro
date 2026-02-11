import asyncio
import random
import math
import logging
import uuid
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from app import models, database
from app.services.anomaly_detector import anomaly_detector

logger = logging.getLogger(__name__)

class LogisticsSimulator:
    def __init__(self):
        self.is_running = False
        self.current_date = datetime.now()
        self.events = []
        self.ema_alpha = 0.2 

    def get_status(self):
        return {
            "current_date": self.current_date.strftime("%Y-%m-%d"),
            "is_running": self.is_running,
            "events": self.events[:20] 
        }

    def log_event(self, message, type="info"):
        icon_map = {
            "bot": "🤖", 
            "warning": "🚨", 
            "success": "✅", 
            "info": "📦", 
            "negotiate": "🤝",
            "truck": "🚚"
        }
        self.events.insert(0, {
            "id": random.randint(1000, 99999),
            "date": self.current_date.strftime("%Y-%m-%d"),
            "message": message,
            "type": type,
            "icon": icon_map.get(type, "ℹ️")
        })
        if len(self.events) > 50: self.events.pop()

    async def run_simulation_loop(self):
        logger.info("🚀 Cyfrowy Bliźniak (Digital Twin) uruchomiony.")
        while True:
            if self.is_running:
                db = database.SessionLocal()
                try:
                    self.run_day_cycle(db)
                except Exception as e:
                    logger.error(f"❌ Krytyczny błąd symulacji: {e}")
                    db.rollback()
                finally:
                    db.close()
            # 2 sekundy rzeczywiste = 1 dzień symulacji
            await asyncio.sleep(2)

    def run_day_cycle(self, db: Session):
        # 1. PRZESUNIĘCIE CZASU
        self.current_date += timedelta(days=1)
        
        # 2. GLOBALNE PRZYJMOWANIE DOSTAW (KROK KRYTYCZNY)
        arriving_orders = db.query(models.Order).filter(
            models.Order.status == "ordered",
            models.Order.estimated_delivery <= self.current_date
        ).all()

        for order in arriving_orders:
            p = order.product
            if p:
                p.current_stock += int(order.quantity)
                order.status = "delivered"
                self.log_event(f"Odebrano dostawę: {p.name} (+{int(order.quantity)} szt.)", "truck")

        # 3. ANALIZA PRODUKTÓW I ZUŻYCIE
        products = db.query(models.Product).all()
        total_stock_value = 0
        total_consumption = 0
        
        for p in products:
            # --- Symulacja Zużycia ---
            demand_spike = 1.0
            if random.random() > 0.97: 
                demand_spike = random.uniform(2.0, 4.0)
                self.log_event(f"Skok popytu na {p.name}!", "warning")

            raw_burn = max(0, random.gauss(p.average_daily_consumption or 3, 1)) * demand_spike
            daily_burn = int(raw_burn)

            # Aktualizacja EMA (średnie zużycie do prognoz)
            current_avg = p.average_daily_consumption or 3.0
            p.average_daily_consumption = (daily_burn * self.ema_alpha) + (current_avg * (1 - self.ema_alpha))

            if p.current_stock > 0:
                actual_burn = min(p.current_stock, daily_burn)
                p.current_stock -= actual_burn
                total_consumption += actual_burn
            
            total_stock_value += (p.current_stock * p.unit_cost)

            # --- INTELIGENTNY REPLENISHMENT (GWARANCJA BRAKU NADMIARU) ---
            # Obliczamy ile towaru już do nas jedzie (tylko status 'ordered')
            incoming_stock = db.query(func.sum(models.Order.quantity)).filter(
                models.Order.product_id == p.id,
                models.Order.status == "ordered"
            ).scalar() or 0

            # Pozycja magazynowa = zapas na półce + zapas w drodze
            inventory_position = p.current_stock + incoming_stock
            
            # Punkt zamówienia: Zużycie * (Czas dostawy + 2 dni bufora)
            reorder_point = (p.average_daily_consumption * (p.lead_time_days or 7)) + (p.average_daily_consumption * 2)

            # Zamawiamy TYLKO jeśli (zapas + droga) < punktu zamówienia
            if inventory_position < reorder_point:
                self._create_jit_order(db, p, inventory_position)

        # 4. ZAPIS STATYSTYK
        try:
            stat_entry = models.DailyStats(
                date=self.current_date,
                total_inventory_value=total_stock_value,
                total_orders_count=total_consumption
            )
            db.add(stat_entry)
        except: pass

        db.commit()

    def _create_jit_order(self, db: Session, product, inventory_position):
        """Logika wyboru dostawcy i tworzenia zamówienia."""
        contracts = db.query(models.Contract).filter(
            models.Contract.product_id == product.id,
            models.Contract.is_active == True
        ).all()

        if not contracts: return

        # Obliczamy na ile dni starczy obecny zapas (bez drogi)
        burn = product.average_daily_consumption or 0.1
        days_until_empty = product.current_stock / burn
        
        cheapest_contract = min(contracts, key=lambda x: x.price)
        
        # Domyślnie bierzemy najtańszego
        selected_contract = cheapest_contract
        sourcing_strategy = "KOSZT"
        lead_time = product.lead_time_days or 7

        # Jeśli towar skończy się szybciej niż dowiezie go najtańszy dostawca...
        if days_until_empty < lead_time:
            # ...szukamy kogokolwiek, kto dowiezie towar szybciej (Express Mode)
            # W pracy inżynierskiej opisz to jako 'Time-Critical Multi-Objective Optimization'
            for c in contracts:
                express_lead_time = int(lead_time * 0.5) # Symulacja dostawy ekspresowej (50% szybciej)
                if c.id != cheapest_contract.id and days_until_empty >= express_lead_time:
                    selected_contract = c
                    sourcing_strategy = "RATUNKOWE (CZAS)"
                    lead_time = express_lead_time
                    break

        # Ilość docelowa: Zapas na 14 dni pracy
        target_stock_level = product.average_daily_consumption * 14
        qty_to_order = int(math.ceil(target_stock_level - inventory_position))
        
        if qty_to_order > 0:
            total_price = qty_to_order * selected_contract.price
            
            new_order = models.Order(
                id=f"AUTO-{uuid.uuid4().hex[:6].upper()}",
                product_id=product.id,
                supplier_id=selected_contract.supplier_id,
                quantity=qty_to_order,
                total_price=total_price,
                status="ordered",
                created_at=self.current_date,
                estimated_delivery=self.current_date + timedelta(days=lead_time),
                payment_terms_days=selected_contract.payment_terms_days
            )

            try:
                new_order.order_type = sourcing_strategy
            except Exception:
                logger.warning("Nie udało się przypisać order_type - model bazy danych nie został poprawnie odświeżony.")

            db.add(new_order)

            # Audyt AI
            if anomaly_detector.is_anomaly(float(qty_to_order), float(total_price), float(selected_contract.price)):
                new_order.status = "pending_approval"
                self.log_event(f"AI Audit: Zablokowano zamówienie {product.name}", "warning")
            else:
                self.log_event(f"{sourcing_strategy}: Zamówiono {product.name} ({qty_to_order} szt.)", "bot")

            db.add(new_order)

# Instancja modułu
simulator = LogisticsSimulator()
import asyncio
import random
import math
import logging
import uuid
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import or_, func, desc
from app import models, database
from app.services.anomaly_detector import anomaly_detector

logger = logging.getLogger(__name__)

class LogisticsSimulator:
    def __init__(self):
        self.is_running = False
        self.current_date = datetime.now()
        self.events = []
        self.ema_alpha = 0.03 

    def get_status(self):
        return {
            "current_date": self.current_date.strftime("%Y-%m-%d"),
            "is_running": self.is_running,
            "events": self.events[:20] 
        }

    def log_event(self, message, type="info"):
        icon_map = {
            "bot": "🤖", "warning": "🚨", "error": "❌", "success": "✅", 
            "info": "📦", "negotiate": "🤝", "truck": "🚚", "bandage": "🩹"
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
        db = database.SessionLocal()
        try:
            last_order = db.query(models.Order).filter(models.Order.created_at.isnot(None)).order_by(desc(models.Order.created_at)).first()
            if last_order and last_order.created_at > datetime.now():
                self.current_date = last_order.created_at
                logger.info(f"⏳ Synchronizacja czasu z bazą: {self.current_date.strftime('%Y-%m-%d')}")
            else:
                self.current_date = datetime.now()
        except Exception:
            self.current_date = datetime.now()
        finally:
            db.close()

        while True:
            if self.is_running:
                db = database.SessionLocal()
                try:
                    self.run_day_cycle(db)
                except Exception as e:
                    logger.error(f"❌ Błąd cyklu: {e}")
                    db.rollback()
                finally:
                    db.close()
            await asyncio.sleep(1.5) # Przyspieszona pętla dla lepszej dynamiki testów

    def run_day_cycle(self, db: Session):
        self.current_date += timedelta(days=1)
        
        # Pobieramy wszystkie aktywne zamówienia w drodze
        pending_orders = db.query(models.Order).filter(models.Order.status == "ordered").all()

        for order in pending_orders:
            # --- POPRAWKA LOGIKI LOSOWANIA: Sprawdzamy transporty bez zapisanego opóźnienia ---
            if getattr(order, 'delay_days', 0) == 0 and getattr(order, 'order_type', '') != 'EMERGENCY':
                # Szansa 15% na wystąpienie zatoru w dowolnym momencie trwania transportu
                if random.random() > 0.85:
                    delay = random.randint(3, 6) # Wyraźniejsze opóźnienie dla testów UX
                    order.delay_days = delay 
                    order.estimated_delivery += timedelta(days=delay)
                    if order.product:
                        self.log_event(f"⚠️ LOGISTYKA: Zator na trasie {order.product.name} (+{delay} dni)!", "warning")

        # Odbiór dostaw (również tych spóźnionych / Ghost Deliveries)
        arriving_orders = db.query(models.Order).filter(
            models.Order.status == "ordered",
            models.Order.estimated_delivery <= self.current_date
        ).all()

        for order in arriving_orders:
            p = order.product
            if p:
                p.current_stock += int(order.quantity)
                order.status = "delivered"
                # delay_days zostawiamy w bazie dla celów analitycznych, ale towar już dotarł
                
                if getattr(order, 'order_type', '') == 'EMERGENCY':
                    self.log_event(f"🩹 RATUNEK: Luka {p.name} załatana.", "success")
                else:
                    self.log_event(f"🚚 Odebrano transport (JIT): {p.name}", "truck")

        products = db.query(models.Product).all()
        total_stock_value = 0
        total_consumption = 0
        
        for p in products:
            demand_spike = 1.0
            current_avg = max(p.average_daily_consumption or 0.0, 1.0)
            
            # Losowe skoki popytu dla realizmu (szansa 6%)
            if random.random() > 0.94: 
                demand_spike = random.uniform(1.8, 3.0) 

            raw_burn = max(1.0, random.gauss(current_avg, current_avg * 0.2)) * demand_spike
            daily_burn = int(math.ceil(raw_burn))

            p.average_daily_consumption = (daily_burn * self.ema_alpha) + (current_avg * (1 - self.ema_alpha))

            if p.current_stock > 0:
                actual_burn = min(p.current_stock, daily_burn)
                p.current_stock -= actual_burn
                total_consumption += actual_burn
            
            if p.current_stock == 0 and daily_burn > 0:
                self.log_event(f"POSTÓJ PRODUKCJI: Brak materiału {p.name}!", "error")
            
            total_stock_value += (p.current_stock * p.unit_cost)

            avg_burn = max(p.average_daily_consumption or 1.0, 1.0) 
            physical_days_left = p.current_stock / avg_burn
            lead_time = p.lead_time_days or 7
            
            ordered_today = False

            # --- DOPRACOWANY PRÓG AWARYJNY ---
            if physical_days_left <= 1.2:
                next_order = db.query(models.Order).filter(
                    models.Order.product_id == p.id,
                    models.Order.status == "ordered"
                ).order_by(models.Order.estimated_delivery.asc()).first()

                days_until_next = (next_order.estimated_delivery - self.current_date).days if next_order else 999

                # Jeśli nic nie dojedzie w ciągu najbliższych 2 dni -> akcja ratunkowa
                if days_until_next > 1:
                    gap = min(7, days_until_next - physical_days_left + 1)
                    self._create_order(db, p, inventory_position=p.current_stock, is_emergency=True, gap_days=gap)
                    ordered_today = True

            # --- AGRESYWNY BUFOR JIT (Punkt zamawiania ROP) ---
            if not ordered_today:
                incoming_stock = db.query(func.sum(models.Order.quantity)).filter(
                    models.Order.product_id == p.id,
                    models.Order.status.in_(["ordered", "pending_approval"])
                ).scalar() or 0

                inventory_position = p.current_stock + incoming_stock
                # Bufor 1.3x lead_time dla maksymalnej stabilności niebieskiego słupka
                reorder_point = avg_burn * (lead_time + (lead_time * 1.3))

                if inventory_position < reorder_point:
                    self._create_order(db, p, inventory_position=inventory_position, is_emergency=False)

        try:
            stat_entry = models.DailyStats(
                date=self.current_date,
                total_inventory_value=total_stock_value,
                total_orders_count=total_consumption
            )
            db.add(stat_entry)
        except Exception: pass

        db.commit()

    def _create_order(self, db: Session, product, inventory_position, is_emergency=False, gap_days=None):
        avg_burn = max(product.average_daily_consumption or 1.0, 1.0)
        contract = db.query(models.Contract).filter(models.Contract.product_id == product.id, models.Contract.is_active == True).first()
        supplier_id = contract.supplier_id if contract else 1
        base_price = contract.price if contract else (product.unit_cost or 50.0)

        if is_emergency:
            qty = max(5, int(math.ceil(avg_burn * (gap_days or 5))))
            price = base_price * 1.5 
            lt = 1 
            s_strategy = "EMERGENCY"
        else:
            qty = max(15, int(math.ceil(avg_burn * (product.lead_time_days + 10))))
            price = base_price
            lt = product.lead_time_days or 7
            s_strategy = "KOSZT/JIT"

        new_order = models.Order(
            id=f"AUTO-{uuid.uuid4().hex[:6].upper()}",
            product_id=product.id,
            supplier_id=supplier_id,
            quantity=qty,
            total_price=qty * price,
            status="ordered",
            order_type=s_strategy, 
            created_at=self.current_date,
            estimated_delivery=self.current_date + timedelta(days=lt),
            payment_terms_days=contract.payment_terms_days if contract else 14,
            delay_days=0
        )

        if not is_emergency and anomaly_detector.is_anomaly(float(qty), float(qty * price), float(price)):
            new_order.status = "pending_approval"
            self.log_event(f"🚨 AI Audit: Zablokowano {product.name}", "warning")
        else:
            if not is_emergency:
                self.log_event(f"🤖 Optymalizacja JIT: {product.name}", "bot")

        db.add(new_order)

simulator = LogisticsSimulator()
import asyncio
import random
import math
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List

from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app import models, database
from app.services.anomaly_detector import anomaly_detector

logger = logging.getLogger(__name__)

class LogisticsSimulator:
    """
    Cyfrowy Bliźniak (Digital Twin) łańcucha dostaw.
    Wersja: 3.1 (Pending orders delay handling)
    """
    def __init__(self) -> None:
        self.is_running: bool = False
        self.current_date: datetime = datetime.now()
        self.events: List[Dict[str, Any]] = []
        self.ema_alpha: float = 0.05 

    @property
    def effective_date(self) -> datetime:
        return self.current_date

    def get_status(self) -> Dict[str, Any]:
        return {
            "current_date": self.effective_date.strftime("%Y-%m-%d"),
            "is_running": self.is_running,
            "events": self.events[:20] 
        }

    def log_event(self, message: str, type: str = "info") -> None:
        icon_map = {
            "bot": "🤖", "warning": "🚨", "error": "❌", "success": "✅", 
            "info": "📦", "negotiate": "🤝", "truck": "🚚", "bandage": "🩹",
            "math": "📊", "check": "📋"
        }
        self.events.insert(0, {
            "id": random.randint(1000, 99999),
            "date": self.effective_date.strftime("%Y-%m-%d"),
            "message": message,
            "type": type,
            "icon": icon_map.get(type, "ℹ️")
        })
        if len(self.events) > 50: 
            self.events.pop()

    def run_monte_carlo_stockout_risk(self, current_stock: float, daily_burn: float, lead_time: int, iterations: int = 100) -> float:
        if current_stock <= 0: return 100.0
        stockouts = 0
        for _ in range(iterations):
            simulated_lt = max(1.0, random.gauss(float(lead_time), 1.0))
            simulated_demand = daily_burn * simulated_lt * random.uniform(0.9, 1.1)
            if current_stock < simulated_demand: stockouts += 1
        return (stockouts / iterations) * 100.0

    async def run_simulation_loop(self) -> None:
        logger.info("🚀 Cyfrowy Bliźniak (Digital Twin) uruchomiony.")
        db = database.SessionLocal()
        try:
            last_order = db.query(models.Order).filter(models.Order.created_at.isnot(None)).order_by(desc(models.Order.created_at)).first()
            if last_order and last_order.created_at > datetime.now():
                self.current_date = last_order.created_at
                logger.info(f"⏳ Wznowienie symulacji od daty: {self.current_date.strftime('%Y-%m-%d')}")
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
                    logger.error(f"❌ Błąd cyklu symulacji: {e}")
                    db.rollback()
                finally:
                    db.close()
            await asyncio.sleep(1.5)

    def _parse_date_safe(self, date_obj):
        if date_obj is None:
            return None
        if isinstance(date_obj, datetime):
            return date_obj
        if isinstance(date_obj, str):
            try:
                return datetime.fromisoformat(date_obj.replace(" ", "T"))
            except ValueError:
                return None
        if hasattr(date_obj, 'day') and not hasattr(date_obj, 'hour'):
            return datetime.combine(date_obj, datetime.min.time())
        return None

    def run_day_cycle(self, db: Session) -> None:
        self.current_date += timedelta(days=1)
        op_date = self.effective_date
        
        end_of_sim_day = op_date.replace(hour=23, minute=59, second=59)

        # --- 1. PANCERNY CATCH-UP (NAPRAWA DOSTAW) ---
        active_orders = db.query(models.Order).filter(models.Order.status == "ordered").all()
        processed_count = 0
        
        for order in active_orders:
            should_deliver = False
            est = self._parse_date_safe(order.estimated_delivery)
            
            if est is None:
                should_deliver = True
            elif est <= end_of_sim_day:
                should_deliver = True

            if should_deliver:
                qty = int(order.quantity)
                db.query(models.Product).filter(models.Product.id == order.product_id).update(
                    {models.Product.current_stock: models.Product.current_stock + qty}
                )
                order.status = "delivered"
                
                days_diff = (op_date - (est or op_date)).days
                p_name = order.product.name if order.product else "Produkt"
                
                if days_diff > 1:
                    self.log_event(f"🧹 CATCH-UP: Wymuszono dostawę {p_name} (+{qty})", "check")
                elif getattr(order, 'order_type', '') == 'EMERGENCY':
                    self.log_event(f"🩹 RATUNEK: Dostarczono {p_name} (+{qty})", "success")
                else:
                    self.log_event(f"🚚 JIT: Dostawa {p_name} (+{qty}) przyjęta.", "truck")
                
                processed_count += 1
        
        if processed_count > 0:
            db.commit()
            db.expire_all()

        # --- 1.5 OBSŁUGA ZAMÓWIEŃ OCZEKUJĄCYCH NA AKCEPTACJĘ ---
        pending_orders = db.query(models.Order).filter(
            models.Order.status == "pending_approval"
        ).all()
        for order in pending_orders:
            if order.estimated_delivery:
                order.estimated_delivery += timedelta(days=1)
            order.pending_days = (order.pending_days or 0) + 1
            if order.product:
                self.log_event(
                    f"⏳ Opóźnienie akceptacji: {order.product.name} ({order.pending_days} dni)", 
                    "warning"
                )
        if pending_orders:
            db.commit()
            db.expire_all()

        # --- 2. SYMULACJA ZATORÓW ---
        remaining_orders = [o for o in active_orders if o.status == "ordered"]

        for order in remaining_orders:
            if getattr(order, 'delay_days', 0) == 0 and getattr(order, 'order_type', '') != 'EMERGENCY':
                if random.random() > 0.85:
                    delay = random.randint(3, 6) 
                    order.delay_days = delay 
                    est = self._parse_date_safe(order.estimated_delivery)
                    if est:
                        order.estimated_delivery = est + timedelta(days=delay)
                        if order.product:
                            self.log_event(f"⚠️ LOGISTYKA: Zator {order.product.name} (+{delay} dni)!", "warning")

        # --- 3. MRP ENGINE ---
        products = db.query(models.Product).all()
        
        current_active = db.query(models.Order).filter(
            models.Order.status == "ordered"
        ).all()
        incoming_cache = {}
        for o in current_active:
            incoming_cache[o.product_id] = incoming_cache.get(o.product_id, 0) + o.quantity

        total_val = 0
        total_cons = 0

        for p in products:
            avg_cons = max(p.average_daily_consumption or 1.0, 1.0)
            burn = max(1.0, random.gauss(avg_cons, avg_cons * 0.1))
            
            if random.random() > 0.98: burn *= 1.5
            
            actual_burn = min(p.current_stock, int(burn))
            p.current_stock -= actual_burn
            total_cons += actual_burn
            total_val += (p.current_stock * p.unit_cost)
            
            p.average_daily_consumption = (actual_burn * 0.1) + (avg_cons * 0.9)

            if p.current_stock == 0 and burn > 0:
                self.log_event(f"BRAK TOWARU: {p.name}", "error")

            days_left = p.current_stock / avg_cons
            incoming = incoming_cache.get(p.id, 0)
            
            next_delivery_date = None
            prod_orders = [o for o in current_active if o.product_id == p.id]
            if prod_orders:
                prod_orders.sort(key=lambda x: str(x.estimated_delivery))
                next_delivery_date = self._parse_date_safe(prod_orders[0].estimated_delivery)

            days_until_delivery = 999
            if next_delivery_date:
                days_until_delivery = (next_delivery_date - op_date).days

            ordered = False
            
            if days_left <= 0.8:
                if incoming == 0 or (days_until_delivery > days_left + 1):
                    gap = 5
                    self._create_order(db, p, p.current_stock, True, gap)
                    ordered = True

            if not ordered:
                inventory_pos = p.current_stock + incoming
                reorder_point = (avg_cons * (p.lead_time_days or 7)) + (avg_cons * 4.0)
                
                if inventory_pos < reorder_point:
                    self._create_order(db, p, inventory_pos, False)

        try:
            db.add(models.DailyStats(date=op_date.date(), total_inventory_value=total_val, total_orders_count=total_cons))
        except: pass
        
        db.commit()

    def _create_order(self, db, product, inv_pos, is_emergency, gap=None):
        avg = max(product.average_daily_consumption or 1.0, 1.0)
        contract = db.query(models.Contract).filter(models.Contract.product_id==product.id, models.Contract.is_active==True).first()
        price = contract.price if contract else product.unit_cost
        supplier_id = contract.supplier_id if contract else 1
        
        date = self.effective_date
        
        if is_emergency:
            qty = int(avg * (gap or 3) * 1.5) 
            lt = 1
            typ = "EMERGENCY"
            price *= 1.5
        else:
            qty = int(avg * 21)
            lt = product.lead_time_days or 7
            typ = "KOSZT/JIT"

        is_anom = False
        if not is_emergency:
            is_anom = anomaly_detector.is_anomaly(qty, qty*price, price)

        status = "pending_approval" if is_anom else "ordered"
        
        order = models.Order(
            id=f"AUTO-{uuid.uuid4().hex[:6].upper()}",
            product_id=product.id,
            supplier_id=supplier_id,
            quantity=qty,
            total_price=qty*price,
            status=status,
            order_type=typ,
            created_at=date,
            estimated_delivery=date + timedelta(days=lt),
            is_anomaly=is_anom,
            pending_days=0  # nowe pole
        )
        
        if is_anom: self.log_event(f"🚨 AI: Zablokowano {product.name}", "warning")
        elif is_emergency: self.log_event(f"🩹 RATUNEK: Zamówiono {product.name}", "bandage")
        else: self.log_event(f"🤖 JIT: Zamówiono {product.name}", "bot")
        
        db.add(order)

simulator = LogisticsSimulator()
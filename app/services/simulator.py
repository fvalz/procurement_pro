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
    Implementuje probabilistyczny model wyliczania zapasów bezpieczeństwa (Safety Stock)
    oraz lekką symulację Monte Carlo do estymacji ryzyka (Stockout Probability).
    """
    def __init__(self) -> None:
        self.is_running: bool = False
        self.current_date: datetime = datetime.now()
        self.events: List[Dict[str, Any]] = []
        self.ema_alpha: float = 0.03 

    def get_status(self) -> Dict[str, Any]:
        return {
            "current_date": self.current_date.strftime("%Y-%m-%d"),
            "is_running": self.is_running,
            "events": self.events[:20] 
        }

    def log_event(self, message: str, type: str = "info") -> None:
        icon_map = {
            "bot": "🤖", "warning": "🚨", "error": "❌", "success": "✅", 
            "info": "📦", "negotiate": "🤝", "truck": "🚚", "bandage": "🩹",
            "math": "📊"
        }
        self.events.insert(0, {
            "id": random.randint(1000, 99999),
            "date": self.current_date.strftime("%Y-%m-%d"),
            "message": message,
            "type": type,
            "icon": icon_map.get(type, "ℹ️")
        })
        if len(self.events) > 50: 
            self.events.pop()

    def run_monte_carlo_stockout_risk(self, current_stock: float, daily_burn: float, lead_time: int, iterations: int = 100) -> float:
        """
        Monte Carlo Lite: Wykonuje 100 szybkich przebiegów symulacyjnych.
        Losuje czas dostawy z rozkładu Gaussa i zwraca procentowe prawdopodobieństwo
        wyczerpania zapasów (Stockout) przed przyjazdem transportu.
        """
        if current_stock <= 0:
            return 100.0
            
        stockouts = 0
        for _ in range(iterations):
            # Stochastyczna symulacja czasu dostawy (średnia=LT, odchylenie=1.5 dnia)
            simulated_lt = max(1.0, random.gauss(float(lead_time), 1.5))
            
            # Stochastyczna symulacja popytu w tym czasie (dodatkowa wariancja +/- 15%)
            simulated_demand = daily_burn * simulated_lt * random.uniform(0.85, 1.15)
            
            if current_stock < simulated_demand:
                stockouts += 1
                
        return (stockouts / iterations) * 100.0

    async def run_simulation_loop(self) -> None:
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
                    logger.error(f"❌ Błąd cyklu symulacji: {e}")
                    db.rollback()
                finally:
                    db.close()
            await asyncio.sleep(1.5)

    def run_day_cycle(self, db: Session) -> None:
        self.current_date += timedelta(days=1)
        
        # 1. Przetwarzanie zamówień w drodze i generowanie opóźnień stochastycznych
        pending_orders = db.query(models.Order).filter(models.Order.status == "ordered").all()

        for order in pending_orders:
            if getattr(order, 'delay_days', 0) == 0 and getattr(order, 'order_type', '') != 'EMERGENCY':
                if random.random() > 0.85:
                    delay = random.randint(3, 6) 
                    order.delay_days = delay 
                    order.estimated_delivery += timedelta(days=delay)
                    if order.product:
                        self.log_event(f"⚠️ LOGISTYKA: Zator na trasie {order.product.name} (+{delay} dni)!", "warning")

        # 2. Odbiór dostaw
        arriving_orders = db.query(models.Order).filter(
            models.Order.status == "ordered",
            models.Order.estimated_delivery <= self.current_date
        ).all()

        for order in arriving_orders:
            p = order.product
            if p:
                p.current_stock += int(order.quantity)
                order.status = "delivered"
                
                if getattr(order, 'order_type', '') == 'EMERGENCY':
                    self.log_event(f"🩹 RATUNEK: Luka {p.name} załatana.", "success")
                else:
                    self.log_event(f"🚚 Odebrano transport (JIT): {p.name}", "truck")

        # 3. Konsumpcja materiałów i analityka predykcyjna (MRP)
        products = db.query(models.Product).all()
        total_stock_value = 0
        total_consumption = 0
        
        for p in products:
            demand_spike = 1.0
            current_avg = max(p.average_daily_consumption or 0.0, 1.0)
            
            # Wstrzykiwanie szumu popytowego (Demand Noise)
            if random.random() > 0.94: 
                demand_spike = random.uniform(1.8, 3.0) 

            raw_burn = max(1.0, random.gauss(current_avg, current_avg * 0.2)) * demand_spike
            daily_burn = int(math.ceil(raw_burn))

            # Aktualizacja wygładzonej średniej kroczącej (EMA)
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

            # --- RATUNKOWY PROTOKÓŁ ZAMÓWIEŃ (Emergency) ---
            if physical_days_left <= 1.2:
                next_order = db.query(models.Order).filter(
                    models.Order.product_id == p.id,
                    models.Order.status == "ordered"
                ).order_by(models.Order.estimated_delivery.asc()).first()

                days_until_next = (next_order.estimated_delivery - self.current_date).days if next_order else 999

                if days_until_next > 1:
                    gap = min(7, days_until_next - int(physical_days_left) + 1)
                    self._create_order(db, p, inventory_position=p.current_stock, is_emergency=True, gap_days=gap)
                    ordered_today = True

            # --- IMPLEMENTACJA PROBABILISTYCZNEGO SAFETY STOCK ---
            if not ordered_today:
                incoming_stock = db.query(func.sum(models.Order.quantity)).filter(
                    models.Order.product_id == p.id,
                    models.Order.status.in_(["ordered", "pending_approval"])
                ).scalar() or 0

                inventory_position = p.current_stock + incoming_stock
                
                # Z-score = 1.65 (dla 95% poziomu obsługi klienta / Service Level)
                Z_SCORE = 1.65
                # Sigma LT = 1.5 dnia (odchylenie standardowe czasu dostawy przyjęte w module Gaussa)
                SIGMA_LT = 1.5 
                
                # Wzór: SS = Z * Sigma_LT * D_avg
                safety_stock = Z_SCORE * SIGMA_LT * avg_burn
                
                # Punkt zamawiania: Popyt w czasie oczekiwania + Zapas Bezpieczeństwa
                reorder_point = (avg_burn * lead_time) + safety_stock

                if inventory_position < reorder_point:
                    # Przed zamówieniem uruchamiamy symulację Monte Carlo
                    risk_pct = self.run_monte_carlo_stockout_risk(p.current_stock, avg_burn, lead_time)
                    
                    if risk_pct > 15.0:
                        self.log_event(f"📊 Monte Carlo: Ryzyko braku {p.name} wynosi {risk_pct:.1f}%", "math")
                        
                    self._create_order(db, p, inventory_position=inventory_position, is_emergency=False)

        try:
            stat_entry = models.DailyStats(
                date=self.current_date,
                total_inventory_value=total_stock_value,
                total_orders_count=total_consumption
            )
            db.add(stat_entry)
        except Exception: 
            pass

        db.commit()

    def _create_order(self, db: Session, product: models.Product, inventory_position: float, is_emergency: bool = False, gap_days: int = None) -> None:
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
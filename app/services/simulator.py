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
    Zarządza czasem symulacji, konsumpcją materiałów i automatyzacją zamówień.
    """
    def __init__(self) -> None:
        self.is_running: bool = False
        self.current_date: datetime = datetime.now()
        self.events: List[Dict[str, Any]] = []
        self.ema_alpha: float = 0.03 

    @property
    def effective_date(self) -> datetime:
        """
        Zwraca datę operacyjną. Zabezpiecza przed cofaniem się czasu względem zegara systemowego.
        """
        return max(self.current_date, datetime.now())

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
        if current_stock <= 0:
            return 100.0
            
        stockouts = 0
        for _ in range(iterations):
            simulated_lt = max(1.0, random.gauss(float(lead_time), 1.5))
            simulated_demand = daily_burn * simulated_lt * random.uniform(0.85, 1.15)
            if current_stock < simulated_demand:
                stockouts += 1
                
        return (stockouts / iterations) * 100.0

    async def run_simulation_loop(self) -> None:
        logger.info("🚀 Cyfrowy Bliźniak (Digital Twin) uruchomiony.")
        db = database.SessionLocal()
        try:
            # Synchronizacja czasu przy starcie
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
        # Przesunięcie czasu o 1 dzień
        self.current_date += timedelta(days=1)
        op_date = self.effective_date
        
        # --- 1. PROTOKÓŁ CATCH-UP (NADRABIANIE DOSTAW) ---
        # Wyszukujemy wszystkie zamówienia, których termin dostawy minął lub jest dzisiaj.
        # Niezależnie od opóźnień, jeśli data nadeszła -> towar wchodzi na stan.
        
        hanging_deliveries = db.query(models.Order).filter(
            models.Order.status == "ordered",
            models.Order.estimated_delivery <= op_date
        ).all()
        
        processed_count = 0
        for order in hanging_deliveries:
            p = order.product
            if p:
                # AKTUALIZACJA STOCKU (Kluczowy moment)
                p.current_stock += int(order.quantity)
                order.status = "delivered"
                
                # Logika powiadomień
                days_late = (op_date - order.estimated_delivery).days
                if days_late > 1:
                    # Jeśli system "przegapił" dostawę o kilka dni
                    self.log_event(f"📋 NADROBIONO: {p.name} (Zaległość {days_late} dni)", "check")
                else:
                    # Standardowa dostawa w terminie
                    if getattr(order, 'order_type', '') == 'EMERGENCY':
                        self.log_event(f"🩹 RATUNEK: Luka {p.name} załatana.", "success")
                    else:
                        self.log_event(f"🚚 Odebrano transport (JIT): {p.name}", "truck")
                processed_count += 1
                
        if processed_count > 0:
            db.commit() # Zatwierdzamy stan magazynowy PRZED analizą zapotrzebowania

        # --- 2. SYMULACJA OPÓŹNIEŃ DLA PRZYSZŁYCH DOSTAW ---
        # Opóźniamy tylko te, które są jeszcze w drodze (data > op_date)
        future_orders = db.query(models.Order).filter(
            models.Order.status == "ordered",
            models.Order.estimated_delivery > op_date
        ).all()

        for order in future_orders:
            # Emergency nigdy się nie spóźnia
            if getattr(order, 'delay_days', 0) == 0 and getattr(order, 'order_type', '') != 'EMERGENCY':
                # 15% szans na losowe opóźnienie
                if random.random() > 0.85:
                    delay = random.randint(3, 6) 
                    order.delay_days = delay 
                    order.estimated_delivery += timedelta(days=delay)
                    if order.product:
                        self.log_event(f"⚠️ LOGISTYKA: Zator na trasie {order.product.name} (+{delay} dni)!", "warning")

        # --- 3. KONSUMPCJA I ZAMAWIANIE (MRP) ---
        products = db.query(models.Product).all()
        total_stock_value = 0
        total_consumption = 0
        
        for p in products:
            demand_spike = 1.0
            current_avg = max(p.average_daily_consumption or 0.0, 1.0)
            
            # Szum popytowy
            if random.random() > 0.94: 
                demand_spike = random.uniform(1.8, 3.0) 

            raw_burn = max(1.0, random.gauss(current_avg, current_avg * 0.2)) * demand_spike
            daily_burn = int(math.ceil(raw_burn))

            # Aktualizacja EMA (średniej kroczącej)
            p.average_daily_consumption = (daily_burn * self.ema_alpha) + (current_avg * (1 - self.ema_alpha))

            # Zużycie materiału
            if p.current_stock > 0:
                actual_burn = min(p.current_stock, daily_burn)
                p.current_stock -= actual_burn
                total_consumption += actual_burn
            
            if p.current_stock == 0 and daily_burn > 0:
                self.log_event(f"POSTÓJ PRODUKCJI: Brak materiału {p.name}!", "error")
            
            total_stock_value += (p.current_stock * p.unit_cost)

            # Analiza zapasów
            avg_burn = max(p.average_daily_consumption or 1.0, 1.0) 
            physical_days_left = p.current_stock / avg_burn
            lead_time = p.lead_time_days or 7
            
            ordered_today = False

            # --- RATUNKOWY PROTOKÓŁ ZAMÓWIEŃ (Emergency) ---
            # Dzięki sekcji Catch-Up powyżej, p.current_stock jest aktualny.
            # Jeśli dostawa weszła, physical_days_left wzrosło i ten warunek się nie spełni.
            if physical_days_left <= 1.2:
                # Sprawdzamy czy już coś jedzie
                next_order = db.query(models.Order).filter(
                    models.Order.product_id == p.id,
                    models.Order.status == "ordered"
                ).order_by(models.Order.estimated_delivery.asc()).first()

                days_until_next = (next_order.estimated_delivery - op_date).days if next_order else 999

                # Jeśli nic nie jedzie lub będzie za długo -> zamawiamy Emergency
                if days_until_next > 1:
                    gap = min(7, days_until_next - int(physical_days_left) + 1)
                    self._create_order(db, p, inventory_position=p.current_stock, is_emergency=True, gap_days=gap)
                    ordered_today = True

            # --- STANDARDOWE ZAMAWIANIE (JIT / Safety Stock) ---
            if not ordered_today:
                incoming_stock = db.query(func.sum(models.Order.quantity)).filter(
                    models.Order.product_id == p.id,
                    models.Order.status.in_(["ordered", "pending_approval"])
                ).scalar() or 0

                inventory_position = p.current_stock + incoming_stock
                
                Z_SCORE = 1.65
                SIGMA_LT = 1.5 
                safety_stock = Z_SCORE * SIGMA_LT * avg_burn
                reorder_point = (avg_burn * lead_time) + safety_stock

                if inventory_position < reorder_point:
                    risk_pct = self.run_monte_carlo_stockout_risk(p.current_stock, avg_burn, lead_time)
                    if risk_pct > 15.0:
                        self.log_event(f"📊 Monte Carlo: Ryzyko braku {p.name} wynosi {risk_pct:.1f}%", "math")
                    self._create_order(db, p, inventory_position=inventory_position, is_emergency=False)

        # Zapis statystyk dziennych
        try:
            stat_entry = models.DailyStats(
                date=op_date.date(),
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
        
        # Używamy effective_date, aby nie tworzyć zamówień z przeszłości
        creation_date = self.effective_date

        if is_emergency:
            qty = max(5, int(math.ceil(avg_burn * (gap_days or 5))))
            price = base_price * 1.5 
            lt = 1 
            s_strategy = "EMERGENCY"
        else:
            cycle_days = 14 
            target_coverage = (product.lead_time_days or 7) + cycle_days
            qty = max(15, int(math.ceil(avg_burn * target_coverage)))
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
            created_at=creation_date,
            estimated_delivery=creation_date + timedelta(days=lt),
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
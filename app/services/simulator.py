import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app import models
import uuid

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

    def toggle_simulation(self, running: bool):
        self.is_running = running
        return self.get_status()

    def run_daily_cycle(self, db: Session):
        # 1. Czas
        self.current_date += timedelta(days=1)
        print(f"🔄 [SYMULACJA] Dzień: {self.current_date.strftime('%Y-%m-%d')}")

        # 2. Zużycie + Uczenie się (AI Learning)
        products = db.query(models.Product).filter(models.Product.current_stock > 0).all()
        updates_count = 0
        
        for product in products:
            daily_consumption = 0
            
            # Symulacja ruchu (40% szansy)
            if random.random() < 0.40:
                if random.random() < 0.05: 
                    daily_consumption = random.randint(5, 15) # Spike
                    print(f"   🔥 [SPIKE] Nagłe zużycie {product.name}: -{daily_consumption}")
                else:
                    daily_consumption = max(1, int(product.current_stock * 0.05), random.randint(1, 3))
                
                new_stock = max(0, product.current_stock - daily_consumption)
                product.current_stock = new_stock
                updates_count += 1
            
            # --- ALGORYTM EMA (Exponential Moving Average) ---
            # Uczymy się tempa zużycia. Waga 0.1 dla nowej obserwacji.
            current_avg = product.average_daily_consumption or 1.0
            new_avg = (current_avg * 0.9) + (daily_consumption * 0.1)
            product.average_daily_consumption = new_avg

        # 3. Dostawy
        pending_orders = db.query(models.Order).filter(
            models.Order.status == "ordered",
            models.Order.estimated_delivery <= self.current_date
        ).all()

        for order in pending_orders:
            order.status = "delivered"
            if order.product:
                order.product.current_stock += order.quantity
                print(f"   📦 [DOSTAWA] +{order.quantity} {order.product.name}")

        # 4. Auto-Replenishment (Bot)
        low_stock = db.query(models.Product).filter(models.Product.current_stock <= models.Product.min_stock_level).all()
        auto_orders = 0
        for p in low_stock:
            has_order = db.query(models.Order).filter(models.Order.product_id==p.id, models.Order.status=="ordered").first()
            if not has_order:
                qty = max(10, (p.min_stock_level * 2) - p.current_stock)
                new_ord = models.Order(
                    id=f"AUTO-{uuid.uuid4().hex[:6].upper()}",
                    product_id=p.id,
                    quantity=qty,
                    total_price=50.0 * qty, # Uproszczenie
                    status="ordered",
                    order_type="production",
                    created_at=self.current_date,
                    estimated_delivery=self.current_date + timedelta(days=p.lead_time_days)
                )
                db.add(new_ord)
                auto_orders += 1
                print(f"   🤖 [BOT] Zamawiam: {p.name}")

        # 5. Statystyki
        total_items = sum(p.current_stock for p in db.query(models.Product).all())
        stat = models.DailyStats(
            date=self.current_date, 
            total_items=int(total_items), 
            low_stock_count=len(low_stock), 
            pending_orders=db.query(models.Order).filter(models.Order.status == "ordered").count()
        )
        db.add(stat)

        db.commit()
        return {"date": self.current_date.strftime("%Y-%m-%d"), "consumed": updates_count}

simulator = SimulationService()
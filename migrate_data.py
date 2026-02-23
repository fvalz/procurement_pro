import random
import uuid
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app import models, database
from app.services.anomaly_detector import anomaly_detector # Importujemy detektor
from passlib.context import CryptContext

# Konfiguracja logowania
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def generate_suppliers(count=90):
    prefixes = ["Stal", "Tech", "Auto", "Press", "Metal", "Tool", "Form", "CNC", "Die", "Pro"]
    suffixes = ["Pol", "Ex", "Master", "System", "Parts", "Hurt", "Met", "Trans", "Flex", "Fix"]
    legal_forms = ["Sp. z o.o.", "GmbH", "Inc.", "S.A."]
    
    suppliers_list = []
    generated_names = set()

    while len(suppliers_list) < count:
        name = f"{random.choice(prefixes)}-{random.choice(suffixes)} {random.choice(legal_forms)}"
        if name in generated_names: continue
        generated_names.add(name)
        
        quality_tier = random.choice(["premium", "standard", "budget"])
        if quality_tier == "premium":
            rel, speed = random.uniform(0.95, 1.0), random.uniform(4.5, 5.0)
        elif quality_tier == "standard":
            rel, speed = random.uniform(0.85, 0.94), random.uniform(3.5, 4.4)
        else:
            rel, speed = random.uniform(0.70, 0.84), random.uniform(2.0, 3.4)

        suppliers_list.append(models.Supplier(
            name=name,
            contact_email=f"sales@{name.lower().replace(' ', '').replace('.', '').replace('-', '')}.com",
            reliability_score=round(rel, 2),
            delivery_speed_rating=round(speed, 1)
        ))
    return suppliers_list

def init_db():
    db = database.SessionLocal()
    # 1. Reset bazy
    models.Base.metadata.drop_all(bind=database.engine)
    models.Base.metadata.create_all(bind=database.engine)
    logger.info("🧹 Baza zresetowana.")

    # 2. Użytkownicy
    db.add_all([
        models.User(email="admin@auto-press.pl", hashed_password=pwd_context.hash("admin123"), role="admin", full_name="Główny Technolog"),
        models.User(email="ai@system.local", hashed_password=pwd_context.hash("bot"), role="bot", full_name="AI Procurement Bot"),
    ])
    db.commit()

    # 3. Dostawcy i Produkty
    suppliers = generate_suppliers(50)
    db.add_all(suppliers)
    db.commit()
    suppliers = db.query(models.Supplier).all()

    products_data = [
        {"name": "Stempel tnący Ø8.0mm", "cat": "Elementy Tnące", "price": 42.0, "burn": 18, "lead": 7},
        {"name": "Matryca tnąca Ø8.2mm", "cat": "Elementy Tnące", "price": 75.0, "burn": 8, "lead": 5},
        {"name": "Słup prowadzący Ø32mm", "cat": "Prowadzenie", "price": 210.0, "burn": 2, "lead": 10},
        {"name": "Sprężyna ISO NIEBIESKA", "cat": "Sprężyny", "price": 16.5, "burn": 25, "lead": 2}
    ]

    db_products = []
    for p in products_data:
        new_prod = models.Product(
            name=p["name"], category=p["cat"], unit_cost=p["price"],
            current_stock=int(p["burn"] * 10), unit="szt.",
            average_daily_consumption=float(p["burn"]), lead_time_days=p["lead"],
            supplier_id=random.choice(suppliers).id
        )
        db_products.append(new_prod)
    db.add_all(db_products)
    db.commit()

    # 4. Kontrakty (Baza do liczenia Price_Deviation)
    contracts = []
    for product in db_products:
        contract_price = round(product.unit_cost * random.uniform(0.95, 1.05), 2)
        contracts.append(models.Contract(
            product_id=product.id, supplier_id=product.supplier_id,
            price=contract_price, start_date=datetime.now() - timedelta(days=365),
            is_active=True
        ))
    db.add_all(contracts)
    db.commit()

    # 5. Historia zamówień (Ważne dla AI)
    logger.info("📊 Generowanie danych historycznych...")
    today = datetime.now()
    all_orders = []

    for day_offset in range(90, 0, -1): # Więcej danych = lepsze AI
        date = today - timedelta(days=day_offset)
        for prod in db_products:
            if random.random() > 0.90:
                # Losujemy, czy to ma być anomalia (5% szans)
                is_fraud = random.random() > 0.95
                
                # Normalne zamówienie vs Anomalia
                if is_fraud:
                    qty = prod.average_daily_consumption * random.uniform(50, 100) # Drastycznie duża ilość
                    price_mult = random.uniform(2.5, 5.0) # Drastycznie wysoka cena
                else:
                    qty = prod.average_daily_consumption * random.uniform(5, 15)
                    price_mult = 1.0

                new_order = models.Order(
                    id=f"HIST-{uuid.uuid4().hex[:6].upper()}",
                    product_id=prod.id,
                    supplier_id=prod.supplier_id,
                    quantity=int(qty),
                    total_price=round(qty * prod.unit_cost * price_mult, 2),
                    status="delivered",
                    created_at=date,
                    is_anomaly=is_fraud
                )
                all_orders.append(new_order)

    db.add_all(all_orders)
    db.commit()
    
    # 6. URUCHOMIENIE TRENINGU MODELU
    logger.info("🧠 Dane gotowe. Uruchamiam automatyczny trening modelu AI...")
    # Pobieramy wszystkie zamówienia do treningu
    all_db_orders = db.query(models.Order).all()
    anomaly_detector.train(all_db_orders)
    
    db.close()
    logger.info("🚀 MIGRACJA I TRENING ZAKOŃCZONE.")

if __name__ == "__main__":
    init_db()
import random
import uuid
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app import models, database
from passlib.context import CryptContext

# Konfiguracja hashowania haseł
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def generate_suppliers(count=90):
    prefixes = [
        "Stal", "Tech", "Auto", "Press", "Metal", "Tool", "Form", "CNC", "Die", "Pro", 
        "Euro", "Global", "Inter", "Pol", "Silesia", "Mechanic", "Precise", "Fast", "Heavy", "Smart"
    ]
    suffixes = [
        "Pol", "Ex", "Master", "System", "Parts", "Hurt", "Met", "Trans", "Flex", "Fix", 
        "Solutions", "Components", "Works", "Group", "Ind", "Supplies", "Technic", "Service"
    ]
    legal_forms = ["Sp. z o.o.", "GmbH", "Inc.", "S.A.", "Co.", "KG", "s.c."]
    
    suppliers_list = []
    generated_names = set()

    print(f"🏭 Generowanie {count} dostawców z branży Automotive...")

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
    # 1. Twardy reset struktury
    models.Base.metadata.drop_all(bind=database.engine)
    models.Base.metadata.create_all(bind=database.engine)
    print("🧹 Baza zresetowana. Nowy schemat (is_anomaly, anomaly_score) aktywny.")

    # 2. Użytkownicy
    db.add_all([
        models.User(email="admin@auto-press.pl", hashed_password=pwd_context.hash("admin123"), role="admin", full_name="Główny Technolog"),
        models.User(email="ai@system.local", hashed_password=pwd_context.hash("bot"), role="bot", full_name="AI Procurement Bot"),
    ])
    db.commit()

    # 3. Dostawcy
    suppliers = generate_suppliers(90)
    db.add_all(suppliers)
    db.commit()
    # Odświeżamy dostawców, by mieć ich ID z bazy
    suppliers = db.query(models.Supplier).all()

    # 4. Produkty
    products_data = [
        {"name": "Stempel tnący Ø8.0mm", "cat": "Elementy Tnące", "price": 42.0, "burn": 18, "lead": 7},
        {"name": "Matryca tnąca Ø8.2mm", "cat": "Elementy Tnące", "price": 75.0, "burn": 8, "lead": 5},
        {"name": "Słup prowadzący Ø32mm", "cat": "Prowadzenie", "price": 210.0, "burn": 2, "lead": 10},
        {"name": "Sprężyna ISO NIEBIESKA", "cat": "Sprężyny", "price": 16.5, "burn": 25, "lead": 2},
        {"name": "Śruba imbusowa M16x80", "cat": "Normalia", "price": 5.5, "burn": 35, "lead": 1},
        {"name": "Czujnik indukcyjny M12", "cat": "Automatyka", "price": 195.0, "burn": 6, "lead": 7}
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
    db_products = db.query(models.Product).all()

    # 5. Kontrakty
    contracts = []
    for product in db_products:
        for sup in random.sample(suppliers, k=random.randint(2, 4)):
            contracts.append(models.Contract(
                product_id=product.id, supplier_id=sup.id,
                price=round(product.unit_cost * random.uniform(0.9, 1.1), 2),
                start_date=datetime.now() - timedelta(days=100),
                is_active=True
            ))
    db.add_all(contracts)
    db.commit()

    # 6. Historia z uwzględnieniem anomalii (AI DATASET)
    print("📊 Generowanie historii z flagami anomalii...")
    today = datetime.now()
    
    for day_offset in range(60, 0, -1):
        date = today - timedelta(days=day_offset)
        for prod in db_products:
            if random.random() > 0.95: # 5% szans na zamówienie danego dnia
                is_fraud = random.random() > 0.92 # Co 12 zamówienie to anomalia dla AI
                qty = prod.average_daily_consumption * (50 if is_fraud else 10)
                
                new_order = models.Order(
                    id=f"HIST-{uuid.uuid4().hex[:6].upper()}",
                    product_id=prod.id,
                    supplier_id=prod.supplier_id,
                    quantity=int(qty),
                    total_price=round(qty * prod.unit_cost * (2.0 if is_fraud else 1.0), 2),
                    status="delivered",
                    created_at=date,
                    estimated_delivery=date + timedelta(days=prod.lead_time_days),
                    order_type="KOSZT/JIT",
                    is_anomaly=is_fraud,
                    # Dla anomalii losujemy niski score (Isolation Forest), dla reszty wysoki
                    anomaly_score=random.uniform(-0.5, -0.1) if is_fraud else random.uniform(0.1, 0.5)
                )
                db.add(new_order)

        # Statystyki dzienne
        db.add(models.DailyStats(
            date=date.date(),
            total_inventory_value=sum(p.current_stock * p.unit_cost for p in db_products),
            total_orders_count=random.randint(10, 50)
        ))

    db.commit()
    db.close()
    print("🚀 MIGRACJA ZAKOŃCZONA. Dane AI (is_anomaly) są gotowe.")

if __name__ == "__main__":
    init_db()
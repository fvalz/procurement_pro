import random
import uuid
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app import models, database
from app.services.anomaly_detector import anomaly_detector
from passlib.context import CryptContext

# Konfiguracja logowania
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def generate_suppliers(count=90):
    prefixes = ["Stal", "Tech", "Auto", "Press", "Metal", "Tool", "Form", "CNC", "Die", "Pro", "Robo", "Hydro", "Fast"]
    suffixes = ["Pol", "Ex", "Master", "System", "Parts", "Hurt", "Met", "Trans", "Flex", "Fix", "Solutions", "Components"]
    legal_forms = ["Sp. z o.o.", "GmbH", "Inc.", "S.A.", "KG", "Co."]
    
    suppliers_list = []
    generated_names = set()

    while len(suppliers_list) < count:
        name = f"{random.choice(prefixes)}-{random.choice(suffixes)} {random.choice(legal_forms)}"
        if name in generated_names: continue
        generated_names.add(name)
        
        quality_tier = random.choices(["premium", "standard", "budget"], weights=[0.2, 0.5, 0.3], k=1)[0]
        
        if quality_tier == "premium":
            rel = random.uniform(0.95, 0.99)
            speed = random.uniform(4.5, 5.0)
        elif quality_tier == "standard":
            rel = random.uniform(0.85, 0.94)
            speed = random.uniform(3.5, 4.4)
        else:
            rel = random.uniform(0.70, 0.84)
            speed = random.uniform(2.0, 3.4)

        suppliers_list.append(models.Supplier(
            name=name,
            contact_email=f"sales@{name.lower().replace(' ', '').replace('.', '').replace('-', '')}.com",
            reliability_score=round(rel, 2),
            delivery_speed_rating=round(speed, 1)
        ))
    return suppliers_list

def generate_automotive_products():
    """Generuje listę ok. 80-100 realistycznych produktów automotive"""
    products = []
    
    # 1. ELEMENTY TNĄCE
    sizes = [4.0, 5.5, 6.0, 8.0, 10.0, 12.0, 16.0, 20.0]
    for s in sizes:
        products.append({
            "name": f"Stempel tnący HSS Ø{s}mm", "cat": "Elementy Tnące",
            "price": round(35 + (s * 4), 2), "burn": random.randint(10, 30), "lead": 7
        })
        products.append({
            "name": f"Matryca tnąca Ø{s+0.2}mm", "cat": "Elementy Tnące",
            "price": round(60 + (s * 5), 2), "burn": random.randint(5, 15), "lead": 5
        })

    # 2. PROWADZENIE
    guide_sizes = [25, 32, 40, 50, 63]
    for g in guide_sizes:
        products.append({
            "name": f"Słup prowadzący demontowalny Ø{g}mm", "cat": "Prowadzenie",
            "price": round(150 + (g * 3), 2), "burn": random.randint(1, 4), "lead": 14
        })
        products.append({
            "name": f"Tuleja z kołnierzem, brąz/grafit Ø{g}mm", "cat": "Prowadzenie",
            "price": round(120 + (g * 2.5), 2), "burn": random.randint(2, 6), "lead": 10
        })

    # 3. SPRĘŻYNY ISO
    colors = [("ZIELONA", "lekkie"), ("NIEBIESKA", "średnie"), ("CZERWONA", "ciężkie"), ("ŻÓŁTA", "b.ciężkie")]
    lengths = ["25x51", "32x64", "40x76", "50x305"]
    for col, load in colors:
        for l in lengths:
            products.append({
                "name": f"Sprężyna ISO {col} {l}mm", "cat": "Sprężyny",
                "price": round(15 + random.uniform(5, 40), 2), "burn": random.randint(10, 50), "lead": 3
            })

    # 4. AUTOMATYKA
    sensors = [
        ("Czujnik indukcyjny M8", 85.0), ("Czujnik indukcyjny M12", 95.0), 
        ("Czujnik indukcyjny M18", 110.0), ("Fotokomórka odbiciowa", 250.0),
        ("Wyłącznik krańcowy rolkowy", 65.0), ("Kabel M12 5-pin 5m", 45.0)
    ]
    for s_name, s_price in sensors:
        products.append({
            "name": s_name, "cat": "Automatyka", 
            "price": s_price, "burn": random.randint(2, 8), "lead": 7
        })

    # 5. NORMALIA
    bolts = ["M6x20", "M8x30", "M10x45", "M12x60", "M16x80"]
    for b in bolts:
        products.append({
            "name": f"Śruba imbusowa DIN912 {b} 12.9", "cat": "Normalia",
            "price": round(random.uniform(0.5, 8.0), 2), "burn": random.randint(100, 500), "lead": 2
        })
        products.append({
            "name": f"Kołek ustalający hartowany {b.split('x')[0].replace('M', 'Ø')}m6", "cat": "Normalia",
            "price": round(random.uniform(2.0, 12.0), 2), "burn": random.randint(50, 200), "lead": 2
        })

    # 6. CHEMIA
    chemicals = ["Smar do prowadnic litowy", "Olej do tłoczenia", "Zmywacz do form"]
    for c in chemicals:
         products.append({
            "name": c, "cat": "Chemia Przemysłowa",
            "price": round(random.uniform(40.0, 150.0), 2), "burn": random.randint(5, 20), "lead": 4
        })

    return products

def init_db():
    db = database.SessionLocal()
    
    # 1. Reset bazy
    logger.info("🧹 Usuwanie starej bazy...")
    models.Base.metadata.drop_all(bind=database.engine)
    models.Base.metadata.create_all(bind=database.engine)
    logger.info("✅ Baza utworzona na nowo.")

    # 2. Użytkownicy
    logger.info("👤 Tworzenie użytkowników...")
    users = [
        models.User(email="admin@procurement-pro.pl", hashed_password=pwd_context.hash("admin123"), role="admin", full_name="Główny Inżynier"),
        models.User(email="jan.kowalski@procurement-pro.pl", hashed_password=pwd_context.hash("user123"), role="user", full_name="Jan Kowalski"),
        models.User(email="ai@system.local", hashed_password=pwd_context.hash("bot"), role="bot", full_name="AI Procurement Bot"),
    ]
    db.add_all(users)
    db.commit()

    # 3. Dostawcy
    logger.info("🏭 Generowanie 60 dostawców...")
    suppliers = generate_suppliers(60)
    db.add_all(suppliers)
    db.commit()
    suppliers_db = db.query(models.Supplier).all()

    # 4. Produkty
    logger.info("📦 Generowanie produktów automotive...")
    products_data = generate_automotive_products()
    
    db_products = []
    # Słownik pomocniczy, żeby pamiętać parametry generowania (burn rate, lead time)
    product_metadata = {} 

    for p in products_data:
        main_supplier = random.choice(suppliers_db)
        
        # Bezpieczne tworzenie produktu (tylko podstawowe pola)
        prod_args = {
            "name": p["name"], 
            "category": p["cat"], 
            "unit_cost": p["price"],
            "current_stock": int(p["burn"] * random.uniform(7, 14)),
            "unit": "szt." if "Smar" not in p["name"] else "l",
            "supplier_id": main_supplier.id
        }
        
        # Opcjonalne pola jeśli istnieją w modelu
        if hasattr(models.Product, 'min_stock_level'):
            prod_args['min_stock_level'] = int(p["burn"] * 3)
        if hasattr(models.Product, 'average_daily_consumption'):
            prod_args['average_daily_consumption'] = float(p["burn"])
        if hasattr(models.Product, 'lead_time_days'):
            prod_args['lead_time_days'] = p["lead"]

        new_prod = models.Product(**prod_args)
        db.add(new_prod)
        db.flush() 
        
        # Zapisujemy metadane do generowania historii
        product_metadata[new_prod.id] = {
            "burn": float(p["burn"]),
            "lead": int(p["lead"])
        }
        
        db_products.append(new_prod)
    
    db.commit()

    # 5. Kontrakty
    logger.info("📜 Generowanie kontraktów (Multipourcing)...")
    contracts = []
    for product in db_products:
        potential_suppliers = random.sample(suppliers_db, k=random.randint(2, 4))
        
        for sup in potential_suppliers:
            price_variation = random.uniform(0.85, 1.15)
            contract_price = round(product.unit_cost * price_variation, 2)
            
            # Bezpieczne tworzenie kontraktu
            contract_args = {
                "product_id": product.id,
                "supplier_id": sup.id,
                "price": contract_price,
                "start_date": datetime.now() - timedelta(days=random.randint(100, 365)),
                "is_active": True
            }

            # Dodajemy supplier_name tylko jeśli kolumna istnieje w models.py
            if hasattr(models.Contract, 'supplier_name'):
                contract_args['supplier_name'] = sup.name
            
            # Dodajemy payment_terms tylko jeśli istnieje
            if hasattr(models.Contract, 'payment_terms_days'):
                contract_args['payment_terms_days'] = 30

            contracts.append(models.Contract(**contract_args))
    
    db.add_all(contracts)
    db.commit()

    # 6. Historia zamówień
    logger.info("📊 Generowanie historii zamówień (Data Mining)...")
    today = datetime.now()
    all_orders = []

    for day_offset in range(120, 0, -1):
        date = today - timedelta(days=day_offset)
        daily_products = random.sample(db_products, k=int(len(db_products) * 0.15))
        
        for prod in daily_products:
            meta = product_metadata.get(prod.id, {"burn": 5, "lead": 7})
            burn_rate = meta["burn"]
            lead_time = meta["lead"]

            is_anomaly_scenario = random.random() > 0.97
            
            if is_anomaly_scenario:
                if random.random() > 0.5:
                    qty = burn_rate * random.uniform(50, 200)
                    price_factor = 1.0
                else:
                    qty = burn_rate * random.uniform(5, 10)
                    price_factor = random.uniform(3.0, 10.0)
            else:
                qty = burn_rate * random.uniform(3, 7)
                price_factor = 1.0

            prod_contracts = [c for c in contracts if c.product_id == prod.id]
            if prod_contracts:
                chosen_contract = random.choice(prod_contracts)
                base_price = chosen_contract.price
                supplier_id = chosen_contract.supplier_id
            else:
                base_price = prod.unit_cost
                supplier_id = prod.supplier_id

            final_price_unit = base_price * price_factor
            
            order_data = {
                "id": f"ORD-{uuid.uuid4().hex[:8].upper()}",
                "product_id": prod.id,
                "supplier_id": supplier_id,
                "quantity": int(qty),
                "total_price": round(qty * final_price_unit, 2),
                "status": "delivered",
                "created_at": date,
                "is_anomaly": is_anomaly_scenario
            }
            
            if hasattr(models.Order, 'order_type'):
                order_data["order_type"] = "KOSZT/JIT" if not is_anomaly_scenario else "BŁĄD/PILNE"
            if hasattr(models.Order, 'estimated_delivery'):
                order_data["estimated_delivery"] = date + timedelta(days=lead_time)
            
            new_order = models.Order(**order_data)
            all_orders.append(new_order)

    db.add_all(all_orders)
    db.commit()
    
    # 7. TRENING AI
    logger.info(f"🧠 Trening modelu na {len(all_orders)} zamówieniach...")
    training_data = db.query(models.Order).all()
    anomaly_detector.train(training_data)
    
    db.close()
    logger.info("🚀 MIGRACJA ZAKOŃCZONA SUKCESEM. System gotowy do pracy.")

if __name__ == "__main__":
    init_db()
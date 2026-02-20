import random
import uuid
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app import models, database
from passlib.context import CryptContext

# Konfiguracja hashowania haseł
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def generate_suppliers(count=90):
    """
    Generator proceduralny nazw dostawców, aby stworzyć dużą, realistyczną bazę
    bez ręcznego wpisywania 90 nazw.
    """
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
        
        if name in generated_names:
            continue
            
        generated_names.add(name)
        
        # Generowanie realistycznych atrybutów
        quality_tier = random.choice(["premium", "standard", "budget"])
        
        if quality_tier == "premium":
            rel = random.uniform(0.95, 1.0)
            speed = random.uniform(4.5, 5.0)
        elif quality_tier == "standard":
            rel = random.uniform(0.85, 0.94)
            speed = random.uniform(3.5, 4.4)
        else: # budget
            rel = random.uniform(0.70, 0.84)
            speed = random.uniform(2.0, 3.4)

        suppliers_list.append(models.Supplier(
            name=name,
            contact_email=f"sales@{name.lower().replace(' ', '').replace('.', '').replace('-', '')}.com",
            reliability_score=round(rel, 2),
            delivery_speed_rating=round(speed, 1)
        ))
    
    return suppliers_list

def init_db():
    # 1. Reset bazy (Drop all and Create all zapewnia utworzenie nowych kolumn, w tym delay_days)
    db = database.SessionLocal()
    models.Base.metadata.drop_all(bind=database.engine)
    models.Base.metadata.create_all(bind=database.engine)
    print("🧹 Wyczyszczono starą bazę i utworzono nowe tabele (z kolumną delay_days).")

    # 2. Użytkownicy
    users = [
        models.User(email="admin@auto-press.pl", hashed_password=pwd_context.hash("admin123"), role="admin", full_name="Główny Technolog"),
        models.User(email="jan@auto-press.pl", hashed_password=pwd_context.hash("user123"), role="employee", full_name="Specjalista ds. Zakupów"),
        models.User(email="ai@system.local", hashed_password=pwd_context.hash("bot"), role="bot", full_name="AI Procurement Bot"),
    ]
    db.add_all(users)
    db.commit()
    print("👤 Dodano użytkowników.")

    # 3. Dodawanie 90 dostawców
    suppliers = generate_suppliers(90)
    db.add_all(suppliers)
    db.commit()
    print(f"✅ Dodano {len(suppliers)} dostawców do bazy.")

    # 4. Lista 30 Produktów (Automotive Press Tooling)
    products_data = [
        # Elementy tnące
        {"name": "Stempel tnący okrągły Ø8.0mm HSS ISO 8020", "cat": "Elementy Tnące", "price": 42.00, "burn": 18, "lead": 7},
        {"name": "Stempel tnący okrągły Ø10.0mm HSS ISO 8020", "cat": "Elementy Tnące", "price": 48.00, "burn": 20, "lead": 7},
        {"name": "Stempel tnący okrągły Ø12.5mm HSS ISO 8020", "cat": "Elementy Tnące", "price": 55.00, "burn": 12, "lead": 7},
        {"name": "Stempel kształtowy (fasolka) 10x20mm", "cat": "Elementy Tnące", "price": 145.00, "burn": 4, "lead": 14},
        {"name": "Matryca tnąca (tuleja) Ø8.2mm", "cat": "Elementy Tnące", "price": 75.00, "burn": 8, "lead": 5},
        {"name": "Matryca tnąca (tuleja) Ø10.2mm", "cat": "Elementy Tnące", "price": 82.00, "burn": 10, "lead": 5},
        {"name": "Wybijak cylindryczny Ø6mm (z łbem)", "cat": "Elementy Tnące", "price": 28.00, "burn": 25, "lead": 3},
        # Prowadzenie
        {"name": "Słup prowadzący demontowalny Ø32mm L=160", "cat": "Prowadzenie", "price": 210.00, "burn": 2, "lead": 10},
        {"name": "Słup prowadzący demontowalny Ø50mm L=200", "cat": "Prowadzenie", "price": 340.00, "burn": 2, "lead": 10},
        {"name": "Tuleja prowadząca z kołnierzem Ø32mm (brąz/grafit)", "cat": "Prowadzenie", "price": 180.00, "burn": 3, "lead": 7},
        {"name": "Koszyk kulkowy Ø32mm", "cat": "Prowadzenie", "price": 95.00, "burn": 5, "lead": 3},
        # Sprężyny
        {"name": "Sprężyna ISO 10243 ZIELONA (Lekka) Ø25x50", "cat": "Sprężyny", "price": 12.00, "burn": 30, "lead": 2},
        {"name": "Sprężyna ISO 10243 NIEBIESKA (Średnia) Ø25x64", "cat": "Sprężyny", "price": 16.50, "burn": 25, "lead": 2},
        {"name": "Sprężyna ISO 10243 ŻÓŁTA (Super Ciężka) Ø40x100", "cat": "Sprężyny", "price": 45.00, "burn": 10, "lead": 3},
        {"name": "Sprężyna gazowa (Azotowa) 1500 daN", "cat": "Sprężyny", "price": 890.00, "burn": 2, "lead": 14},
        # Normalia i Montaż
        {"name": "Śruba pasowana M10x40 (ISO 7379)", "cat": "Normalia", "price": 12.50, "burn": 20, "lead": 2},
        {"name": "Śruba imbusowa M16x80 (kl. 12.9)", "cat": "Normalia", "price": 5.50, "burn": 35, "lead": 1},
        {"name": "Kołek ustalający hartowany 10m6x40", "cat": "Normalia", "price": 3.20, "burn": 20, "lead": 2},
        # Chemia i Automatyka
        {"name": "Czujnik indukcyjny M12 (wykr. blachy)", "cat": "Automatyka", "price": 195.00, "burn": 6, "lead": 7},
        {"name": "Olej do tłoczenia (Beczka 200L)", "cat": "Chemia", "price": 3500.00, "burn": 2, "lead": 5},
        {"name": "Smar stały do prowadnic (Puszka 1kg)", "cat": "Chemia", "price": 120.00, "burn": 6, "lead": 3},
    ]

    db_products = []
    for p in products_data:
        main_supplier = random.choice(suppliers)
        new_prod = models.Product(
            name=p["name"],
            category=p["cat"],
            unit_cost=p["price"],
            current_stock=int(p["burn"] * 10) + random.randint(5, 20),
            description="Specjalistyczna część tłocznika. Norma: Automotive standard.",
            average_daily_consumption=float(p["burn"]),
            lead_time_days=p["lead"],
            supplier_id=main_supplier.id,
            unit="szt." # Dodane pole jednostki
        )
        db_products.append(new_prod)
    
    db.add_all(db_products)
    db.commit()
    print(f"🔧 Dodano {len(db_products)} produktów specjalistycznych.")

    # 5. Tworzenie Kontraktów (Contracts)
    contracts = []
    print("📜 Generowanie kontraktów handlowych (Multi-sourcing)...")
    for product in db_products:
        potential_suppliers = random.sample(suppliers, k=random.randint(3, 6))
        for sup in potential_suppliers:
            price_mult = random.uniform(0.85, 1.15)
            contracts.append(models.Contract(
                product_id=product.id,
                supplier_id=sup.id,
                price=round(product.unit_cost * price_mult, 2),
                start_date=datetime.now() - timedelta(days=random.randint(50, 200)),
                end_date=datetime.now() + timedelta(days=365),
                payment_terms_days=random.choice([30, 45, 60, 90]),
                is_active=True
            ))
    db.add_all(contracts)
    db.commit()
    print(f"✅ Podpisano {len(contracts)} kontraktów handlowych.")

    # 6. Generowanie Historii (60 dni wstecz)
    print("📊 Generowanie historii transakcji (60 dni)...")
    today = datetime.now()
    daily_stats = []
    orders_to_add = []

    for day_offset in range(60, 0, -1):
        date = today - timedelta(days=day_offset)
        total_value = 0
        total_consumption = 0

        for prod in db_products:
            burn_rate = prod.average_daily_consumption or 0.1
            burn = int(max(1, random.gauss(burn_rate, burn_rate * 0.3)))
            
            if day_offset <= 30 and prod.id % 5 == 0: 
                burn = int(burn * 1.5) # Symulacja trendu wzrostowego

            total_consumption += burn
            total_value += (prod.current_stock * prod.unit_cost)
            
            if random.random() > 0.95: 
                available_contracts = [c for c in contracts if c.product_id == prod.id]
                if available_contracts:
                    contract = random.choice(available_contracts)
                    is_emergency = random.random() > 0.90 
                    
                    order_kwargs = {
                        "id": f"HIST-{uuid.uuid4().hex[:6].upper()}",
                        "product_id": prod.id,
                        "supplier_id": contract.supplier_id,
                        "quantity": max(1, int(burn_rate * (14 if not is_emergency else 5))),
                        "total_price": 0, # Wyliczone poniżej
                        "status": "delivered",
                        "created_at": date - timedelta(days=(1 if is_emergency else prod.lead_time_days)),
                        "estimated_delivery": date,
                        "payment_terms_days": contract.payment_terms_days,
                        "delay_days": 0 # Historia to zamówienia zakończone (0 spóźnienia)
                    }
                    order_kwargs["total_price"] = order_kwargs["quantity"] * (contract.price * 1.5 if is_emergency else contract.price)
                    
                    if hasattr(models.Order, "order_type"):
                        order_kwargs["order_type"] = "EMERGENCY" if is_emergency else "KOSZT/JIT"
                    
                    orders_to_add.append(models.Order(**order_kwargs))

        daily_stats.append(models.DailyStats(
            date=date.date(),
            total_inventory_value=total_value,
            total_orders_count=total_consumption
        ))

    db.add_all(daily_stats)
    db.add_all(orders_to_add)
    db.commit()
    db.close()
    
    print("\n" + "="*50)
    print("🚀 MIGRACJA ZAKOŃCZONA SUKCESEM!")
    print(f"   - Dostawców: {len(suppliers)}")
    print(f"   - Produktów: {len(db_products)}")
    print(f"   - Dni historii: 60 (JIT & Emergency data loaded)")
    print("="*50)

if __name__ == "__main__":
    init_db()
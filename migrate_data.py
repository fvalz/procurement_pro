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
        # Część dostawców jest tania i słaba, część droga i solidna
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
    # 1. Reset bazy
    db = database.SessionLocal()
    models.Base.metadata.drop_all(bind=database.engine)
    models.Base.metadata.create_all(bind=database.engine)
    print("🧹 Wyczyszczono starą bazę i utworzono nowe tabele.")

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
    # Podział na kategorie logiczne dla fabryki tłocznej
    products_data = [
        # --- Kategoria: ELEMENTY TNĄCE (Punches & Dies) ---
        {"name": "Stempel tnący okrągły Ø8.0mm HSS ISO 8020", "cat": "Elementy Tnące", "price": 42.00, "burn": 8, "lead": 7},
        {"name": "Stempel tnący okrągły Ø10.0mm HSS ISO 8020", "cat": "Elementy Tnące", "price": 48.00, "burn": 10, "lead": 7},
        {"name": "Stempel tnący okrągły Ø12.5mm HSS ISO 8020", "cat": "Elementy Tnące", "price": 55.00, "burn": 6, "lead": 7},
        {"name": "Stempel kształtowy (fasolka) 10x20mm", "cat": "Elementy Tnące", "price": 145.00, "burn": 2, "lead": 14},
        {"name": "Matryca tnąca (tuleja) Ø8.2mm", "cat": "Elementy Tnące", "price": 75.00, "burn": 4, "lead": 5},
        {"name": "Matryca tnąca (tuleja) Ø10.2mm", "cat": "Elementy Tnące", "price": 82.00, "burn": 5, "lead": 5},
        {"name": "Wybijak cylindryczny Ø6mm (z łbem)", "cat": "Elementy Tnące", "price": 28.00, "burn": 15, "lead": 3},

        # --- Kategoria: PROWADZENIE (Guiding Elements) ---
        {"name": "Słup prowadzący demontowalny Ø32mm L=160", "cat": "Prowadzenie", "price": 210.00, "burn": 0.2, "lead": 10},
        {"name": "Słup prowadzący demontowalny Ø50mm L=200", "cat": "Prowadzenie", "price": 340.00, "burn": 0.1, "lead": 10},
        {"name": "Tuleja prowadząca z kołnierzem Ø32mm (brąz/grafit)", "cat": "Prowadzenie", "price": 180.00, "burn": 0.5, "lead": 7},
        {"name": "Tuleja prowadząca z kołnierzem Ø50mm (brąz/grafit)", "cat": "Prowadzenie", "price": 260.00, "burn": 0.4, "lead": 7},
        {"name": "Koszyk kulkowy Ø32mm", "cat": "Prowadzenie", "price": 95.00, "burn": 1.5, "lead": 3},
        {"name": "Płyta ślizgowa samosmarna VDI 3357 50x100", "cat": "Prowadzenie", "price": 120.00, "burn": 2.0, "lead": 5},

        # --- Kategoria: SPRĘŻYNY I SIŁOWNIKI (Springs & Nitrogen) ---
        {"name": "Sprężyna ISO 10243 ZIELONA (Lekka) Ø25x50", "cat": "Sprężyny", "price": 12.00, "burn": 20, "lead": 2},
        {"name": "Sprężyna ISO 10243 NIEBIESKA (Średnia) Ø25x64", "cat": "Sprężyny", "price": 16.50, "burn": 15, "lead": 2},
        {"name": "Sprężyna ISO 10243 CZERWONA (Ciężka) Ø32x70", "cat": "Sprężyny", "price": 24.00, "burn": 10, "lead": 2},
        {"name": "Sprężyna ISO 10243 ŻÓŁTA (Super Ciężka) Ø40x100", "cat": "Sprężyny", "price": 45.00, "burn": 8, "lead": 3},
        {"name": "Sprężyna gazowa (Azotowa) 500 daN", "cat": "Sprężyny", "price": 480.00, "burn": 0.3, "lead": 14},
        {"name": "Sprężyna gazowa (Azotowa) 1500 daN", "cat": "Sprężyny", "price": 890.00, "burn": 0.1, "lead": 14},
        {"name": "Zestaw uszczelnień do sprężyny gazowej", "cat": "Serwis", "price": 110.00, "burn": 2.0, "lead": 5},

        # --- Kategoria: NORMALIA I MONTAŻ (Fasteners) ---
        {"name": "Śruba pasowana M10x40 (ISO 7379)", "cat": "Normalia", "price": 12.50, "burn": 12, "lead": 2},
        {"name": "Śruba pasowana M12x50 (ISO 7379)", "cat": "Normalia", "price": 15.00, "burn": 10, "lead": 2},
        {"name": "Śruba imbusowa M16x80 (kl. 12.9)", "cat": "Normalia", "price": 5.50, "burn": 25, "lead": 1},
        {"name": "Kołek ustalający hartowany 10m6x40", "cat": "Normalia", "price": 3.20, "burn": 15, "lead": 2},
        {"name": "Uchwyt transportowy M24 (Ucho)", "cat": "Normalia", "price": 65.00, "burn": 0.5, "lead": 4},

        # --- Kategoria: AUTOMATYKA I CHEMIA (Others) ---
        {"name": "Czujnik indukcyjny M12 (wykr. blachy)", "cat": "Automatyka", "price": 195.00, "burn": 3.0, "lead": 7},
        {"name": "Przewód hydrauliczny zakuwany 2m", "cat": "Hydraulika", "price": 85.00, "burn": 1.0, "lead": 3},
        {"name": "Szybkozłącze hydrauliczne męskie", "cat": "Hydraulika", "price": 45.00, "burn": 2.0, "lead": 3},
        {"name": "Olej do tłoczenia (Beczka 200L)", "cat": "Chemia", "price": 3500.00, "burn": 0.2, "lead": 5},
        {"name": "Smar stały do prowadnic (Puszka 1kg)", "cat": "Chemia", "price": 120.00, "burn": 4.0, "lead": 3},
    ]

    db_products = []
    
    # Przypisywanie produktów do dostawców
    # LOGIKA: Jeden produkt jest dostępny u 3-5 losowych dostawców, a nie u jednego.
    # To pozwala AI wybierać najtańszą ofertę.
    
    for p in products_data:
        # Tworzymy produkt w bazie (przypisujemy "głównego" dostawcę, ale kontrakty będą z wieloma)
        main_supplier = random.choice(suppliers)
        
        new_prod = models.Product(
            name=p["name"],
            category=p["cat"],
            unit_cost=p["price"],
            current_stock=random.randint(20, 100), # Startowy zapas
            description=f"Specjalistyczna część tłocznika. Norma: Automotive standard.",
            average_daily_consumption=float(p["burn"]),
            lead_time_days=p["lead"],
            supplier_id=main_supplier.id
        )
        db_products.append(new_prod)
    
    db.add_all(db_products)
    db.commit()
    print(f"🔧 Dodano {len(db_products)} produktów specjalistycznych.")

    # 5. Tworzenie Kontraktów (Contracts)
    # Tu dzieje się magia JIT: Każdy produkt ma 3-6 ofert od różnych dostawców z listy 90.
    contracts = []
    
    print("📜 Generowanie kontraktów handlowych (Multi-sourcing)...")
    
    for product in db_products:
        # Losujemy 3 do 6 dostawców, którzy mają ten produkt w ofercie
        potential_suppliers = random.sample(suppliers, k=random.randint(3, 6))
        
        for sup in potential_suppliers:
            # Różnicowanie ceny: +/- 15% od ceny bazowej
            price_mult = random.uniform(0.85, 1.15)
            # Różnicowanie terminu płatności
            payment = random.choice([30, 45, 60, 90])
            
            contracts.append(models.Contract(
                product_id=product.id,
                supplier_id=sup.id,
                price=round(product.unit_cost * price_mult, 2),
                start_date=datetime.now() - timedelta(days=random.randint(50, 200)),
                end_date=datetime.now() + timedelta(days=365),
                payment_terms_days=payment,
                is_active=True
            ))
            
    db.add_all(contracts)
    db.commit()
    print(f"✅ Podpisano {len(contracts)} kontraktów.")

    # 6. Generowanie Historii (30 dni wstecz)
    print("📊 Generowanie historii transakcji (cierpliwości)...")
    
    today = datetime.now()
    daily_stats = []
    orders = []

    for day_offset in range(30, 0, -1):
        date = today - timedelta(days=day_offset)
        total_value = 0
        total_consumption = 0

        for prod in db_products:
            # Symulacja zużycia (INT ONLY!)
            burn = int(max(0, random.gauss(prod.average_daily_consumption, prod.average_daily_consumption * 0.3)))
            
            total_consumption += burn
            total_value += (prod.current_stock * prod.unit_cost)
            
            # Wirtualna aktualizacja stanu na potrzeby wykresu (bez zapisu do product)
            # (Tutaj upraszczamy, zakładając, że stan oscyluje wokół średniej)

            # Generowanie historycznych zamówień (żeby tabela zamówień nie była pusta)
            if random.random() > 0.97: # Rzadkie zamówienia (duże partie)
                # Wybór dostawcy z kontraktu
                available_contracts = [c for c in contracts if c.product_id == prod.id]
                if available_contracts:
                    contract = random.choice(available_contracts)
                    qty = int(prod.average_daily_consumption * 20) + 10
                    
                    orders.append(models.Order(
                        id=f"HIST-{uuid.uuid4().hex[:6].upper()}",
                        product_id=prod.id,
                        supplier_id=contract.supplier_id,
                        quantity=qty,
                        total_price=qty * contract.price,
                        status="delivered",
                        created_at=date - timedelta(days=prod.lead_time_days),
                        estimated_delivery=date,
                        payment_terms_days=contract.payment_terms_days
                    ))

        daily_stats.append(models.DailyStats(
            date=date,
            total_inventory_value=total_value,
            total_orders_count=total_consumption
        ))

    db.add_all(daily_stats)
    db.add_all(orders)
    db.commit()
    db.close()
    
    print("\n" + "="*50)
    print("🚀 MIGRACJA ZAKOŃCZONA SUKCESEM!")
    print(f"   - Dostawców: {len(suppliers)}")
    print(f"   - Produktów: {len(db_products)}")
    print(f"   - Kontraktów: {len(contracts)}")
    print(f"   - Dni historii: 30")
    print("="*50)

if __name__ == "__main__":
    init_db()
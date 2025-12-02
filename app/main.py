import os
# --- FIX DLA AI (KERAS 3) ---
os.environ["TF_USE_LEGACY_KERAS"] = "1"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0" 
# ----------------------------

import asyncio
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import uuid

# Importujemy nasze moduły
from . import models, schemas, database
from .services.simulator import simulator
from .services.ai_search import ai_search
from .services.contract_parser import contract_parser

app = FastAPI(
    title="Procurement Pro API",
    description="System inżynierski do zarządzania zakupami z symulacją czasu rzeczywistego i AI.",
    version="2.1.0"
)

# --- KONFIGURACJA CORS ---
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- STARTUP ---
@app.on_event("startup")
async def startup_event():
    """Uruchamia pętlę symulacji ORAZ indeksuje produkty dla AI przy starcie"""
    asyncio.create_task(run_simulation_loop())

    db = database.SessionLocal()
    try:
        print("🧠 [STARTUP] Pobieranie produktów do indeksu AI...")
        products = db.query(models.Product).all()
        products_schemas = [schemas.Product.model_validate(p) for p in products]
        ai_search.index_products(products_schemas)
    except Exception as e:
        print(f"❌ [STARTUP] Błąd indeksowania AI: {e}")
    finally:
        db.close()

async def run_simulation_loop():
    """Pętla symulacji działająca w tle"""
    while True:
        if simulator.is_running:
            db = database.SessionLocal()
            try:
                simulator.run_daily_cycle(db)
            finally:
                db.close()
            await asyncio.sleep(2)
        else:
            await asyncio.sleep(1)

# --- ENDPOINTY STEROWANIA SYMULACJĄ ---

@app.get("/simulation/status")
def get_simulation_status():
    return simulator.get_status()

@app.post("/simulation/start")
def start_simulation():
    return simulator.toggle_simulation(True)

@app.post("/simulation/stop")
def stop_simulation():
    return simulator.toggle_simulation(False)

# --- ENDPOINTY PRODUKTÓW (POPRAWIONE) ---

@app.get("/products", response_model=List[schemas.Product])
def read_products(skip: int = 0, limit: int = 100, search: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Zwraca listę produktów WRAZ z informacją o aktywnych kontraktach (Compliance).
    """
    final_products = []

    # 1. Wybór źródła (AI vs SQL)
    if search:
        ai_results = ai_search.search(search, top_k=limit)
        if not ai_results:
            return []
        found_ids = [p.id for p in ai_results]
        # Pobierz świeże dane z SQL
        db_products = db.query(models.Product).filter(models.Product.id.in_(found_ids)).all()
        # Sortowanie wg trafności AI
        product_map = {p.id: p for p in db_products}
        raw_products = [product_map[pid] for pid in found_ids if pid in product_map]
    else:
        raw_products = db.query(models.Product).offset(skip).limit(limit).all()

    # 2. WZBOGACANIE O DANE KONTRAKTOWE (Compliance Check)
    for prod in raw_products:
        # Konwertujemy model SQL na Pydantic ręcznie, żeby dodać pole 'active_contract'
        p_schema = schemas.Product.model_validate(prod)
        
        # Szukamy aktywnego kontraktu dla tego produktu
        active_contract = db.query(models.Contract).filter(
            models.Contract.product_id == prod.id,
            models.Contract.is_active == True
        ).first()

        if active_contract:
            # Jeśli jest kontrakt -> dodajemy info do obiektu
            p_schema.active_contract = schemas.ContractInfo(
                supplier_name=active_contract.supplier.name if active_contract.supplier else "Kontrakt",
                price=active_contract.price,
                valid_until=active_contract.valid_until
            )
        
        final_products.append(p_schema)

    return final_products
    
    # 2. STANDARD SQL (Bez wyszukiwania)
    return db.query(models.Product).offset(skip).limit(limit).all()

@app.get("/inventory/alerts", response_model=List[schemas.Product])
def read_low_stock_products(db: Session = Depends(get_db)):
    return db.query(models.Product).filter(
        models.Product.current_stock <= models.Product.min_stock_level
    ).all()

# --- ENDPOINTY ZAMÓWIEŃ ---

@app.post("/orders", response_model=schemas.Order)
def create_order(order: schemas.OrderCreate, db: Session = Depends(get_db)):
    db_product = db.query(models.Product).filter(models.Product.id == order.product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail=f"Product with ID {order.product_id} not found")

    supplier_id = order.supplier_id
    price_per_unit = 50.0 
    
    active_contract = db.query(models.Contract).filter(
        models.Contract.product_id == order.product_id,
        models.Contract.is_active == True
    ).first()

    if active_contract:
        supplier_id = active_contract.supplier_id
        price_per_unit = active_contract.price
    elif not supplier_id:
        supplier = db.query(models.Supplier).filter(
            models.Supplier.category == db_product.category
        ).first()
        if supplier:
            supplier_id = supplier.id
    
    total_price = price_per_unit * order.quantity
    current_sim_date = simulator.current_date

    db_order = models.Order(
        id=f"ORD-{uuid.uuid4().hex[:8].upper()}",
        product_id=order.product_id,
        supplier_id=supplier_id,
        quantity=order.quantity,
        total_price=total_price,
        status="ordered",
        order_type=order.order_type,
        created_at=current_sim_date,
        estimated_delivery=current_sim_date + timedelta(days=db_product.lead_time_days)
    )
    
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return db_order

@app.get("/orders", response_model=List[schemas.Order])
def read_orders(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.Order).order_by(models.Order.created_at.desc()).offset(skip).limit(limit).all()

# --- ENDPOINTY KONTRAKTÓW ---

@app.post("/contracts/upload", response_model=schemas.ContractDraft)
async def upload_contract(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()
    try:
        draft_data = contract_parser.parse_pdf(content)
    except Exception as e:
        print(f"Błąd PDF: {e}")
        raise HTTPException(status_code=400, detail=f"Błąd czytania PDF: {str(e)}")
    return draft_data

@app.post("/contracts/confirm")
def confirm_contract(data: schemas.ContractDraft, db: Session = Depends(get_db)):
    """
    Zapisuje zweryfikowany kontrakt do bazy SQL.
    Automatycznie tworzy brakującego dostawcę lub produkt (Auto-Cataloging).
    """
    print(f"📝 [CONTRACT] Próba zapisu umowy: {data.product_name} od {data.supplier_name}")

    # 1. Znajdź lub Stwórz Dostawcę
    supplier = db.query(models.Supplier).filter(models.Supplier.name == data.supplier_name).first()
    if not supplier:
        print(f"   ➕ Dodawanie nowego dostawcy: {data.supplier_name}")
        supplier = models.Supplier(name=data.supplier_name, category="Kontraktowe", rating=5.0)
        db.add(supplier)
        db.commit()
        db.refresh(supplier)

    # 2. Znajdź lub Stwórz Produkt
    # Szukamy dokładnego dopasowania lub tworzymy nowy
    product = db.query(models.Product).filter(models.Product.name == data.product_name).first()
    if not product:
        print(f"   ➕ Dodawanie nowego produktu do katalogu: {data.product_name}")
        product = models.Product(
            name=data.product_name,
            category="Kontraktowe", # Tymczasowa kategoria
            unit="szt.",
            current_stock=0,
            min_stock_level=10
        )
        # Musimy zaindeksować ten nowy produkt w AI!
        # Ale zrobimy to przy restarcie serwera dla uproszczenia, lub dodamy dynamicznie:
        # ai_search.index_products([schemas.Product.model_validate(product)]) (Opcjonalnie)
        
        db.add(product)
        db.commit()
        db.refresh(product)

    # 3. Dezaktywuj stare kontrakty na ten sam produkt (Zasada: 1 aktywna umowa na produkt)
    old_contracts = db.query(models.Contract).filter(
        models.Contract.product_id == product.id,
        models.Contract.is_active == True
    ).all()
    
    for old in old_contracts:
        old.is_active = False
        print(f"   🔻 Archiwizacja starej umowy ID: {old.id}")

    # 4. Utwórz Nowy Kontrakt
    new_contract = models.Contract(
        supplier_id=supplier.id,
        product_id=product.id,
        price=data.price,
        valid_until=data.valid_until,
        is_active=True,
        penalty_clause_details="Standardowa kara umowna 10%" # Domyślnie
    )
    
    db.add(new_contract)
    db.commit()
    db.refresh(new_contract)
    
    print(f"✅ [SUCCESS] Umowa ID {new_contract.id} aktywna do {data.valid_until}")
    return {"message": "Kontrakt zapisany pomyślnie", "contract_id": new_contract.id}


@app.get("/analytics/history")
def get_analytics_history(db: Session = Depends(get_db)):
    """Zwraca pełną historię zmian w magazynie do wykresów"""
    # Pobieramy wszystkie rekordy posortowane datą
    history = db.query(models.DailyStats).order_by(models.DailyStats.date).all()
    return history

@app.get("/analytics/predictions", response_model=List[schemas.Prediction])
def get_predictions(limit: int = 10, db: Session = Depends(get_db)):
    """
    Zwraca prognozę wyczerpania zapasów (Szklana Kula).
    Sortuje od produktów, które skończą się najszybciej.
    """
    products = db.query(models.Product).all()
    predictions = []
    
    for p in products:
        burn_rate = p.average_daily_consumption
        if burn_rate <= 0.1: burn_rate = 0.1 # Zabezpieczenie przed dzieleniem przez 0
        
        days_left = p.current_stock / burn_rate
        
        # Określenie statusu
        status = "safe"
        restock = False
        
        if days_left < p.lead_time_days: # Skończy się ZANIM dojedzie nowa dostawa!
            status = "critical"
            restock = True
        elif days_left < p.lead_time_days * 2:
            status = "warning"
        
        predictions.append(schemas.Prediction(
            product_name=p.name,
            current_stock=p.current_stock,
            burn_rate=round(burn_rate, 2),
            days_left=round(days_left, 1),
            status=status,
            restock_recommended=restock
        ))
    
    # Sortujemy: najpierw te, które mają najmniej dni zapasu
    predictions.sort(key=lambda x: x.days_left)
    
    return predictions[:limit]

@app.get("/analytics/predictions", response_model=List[schemas.Prediction])
def get_predictions(limit: int = 50, db: Session = Depends(get_db)):
    """Zwraca prognozę wyczerpania zapasów (Runway) dla każdego produktu."""
    products = db.query(models.Product).all()
    predictions = []
    
    for p in products:
        # Pobieramy nauczone tempo (min 0.1 żeby nie dzielić przez zero)
        burn_rate = p.average_daily_consumption if p.average_daily_consumption > 0.1 else 0.1
        
        # Kluczowy wzór: Inventory Runway (Zapas / Zużycie)
        days_left = p.current_stock / burn_rate
        
        status = "safe"
        restock = False
        
        # Jeśli zapas skończy się szybciej niż czas dostawy -> Krytyczne!
        if days_left < p.lead_time_days:
            status = "critical"
            restock = True
        elif days_left < p.lead_time_days * 1.5:
            status = "warning"
        
        predictions.append(schemas.Prediction(
            id=p.id,
            product_name=p.name,
            current_stock=p.current_stock,
            burn_rate=round(burn_rate, 2),
            days_left=round(days_left, 1),
            status=status,
            restock_recommended=restock
        ))
    
    # Sortujemy: najpierw te, które zaraz się skończą
    predictions.sort(key=lambda x: x.days_left)
    return predictions[:limit]
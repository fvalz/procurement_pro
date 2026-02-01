import os
# --- KONFIGURACJA DLA AI (Unikanie błędów Keras 3/TensorFlow) ---
os.environ["TF_USE_LEGACY_KERAS"] = "1"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0" 

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, File, UploadFile
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from pydantic import BaseModel 
from fpdf import FPDF 

# Importy lokalne z naszych modułów
from . import models, schemas, database
from .services.simulator import simulator
from .services.ai_search import ai_search
from .services.contract_parser import contract_parser
from .services.anomaly_detector import anomaly_detector

# Konfiguracja loggera
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ProcurementAPI")

app = FastAPI(
    title="Procurement Pro API",
    description="System inżynierski ERP: AI, Symulacja, Finanse, Chatbot.",
    version="4.0.2" 
)

# --- KONFIGURACJA CORS ---
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Zezwalamy na wszystko dla dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency do bazy danych
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- STARTUP SYSTEMU ---
@app.on_event("startup")
async def startup_event():
    """Uruchamia procesy inicjalizacyjne przy starcie serwera"""
    db = database.SessionLocal()
    try:
        # 1. Indeksowanie produktów dla Wyszukiwarki AI
        logger.info("🧠 [AI] Indeksowanie produktów (Embeddings)...")
        products = db.query(models.Product).all()
        # Konwersja modeli SQLAlchemy na Pydantic dla serwisu AI
        products_schemas = [schemas.Product.model_validate(p) for p in products]
        if products_schemas:
            try:
                ai_search.index_products(products_schemas)
            except Exception as e:
                logger.error(f"AI Index Error: {e}")
        
        # 2. Trening Detektora Anomalii na danych historycznych
        logger.info("🕵️‍♂️ [AI] Trening Auditora (Isolation Forest)...")
        orders = db.query(models.Order).all()
        if orders:
            try:
                anomaly_detector.train(orders)
            except Exception as e:
                logger.error(f"Anomaly Training Error: {e}")
        
        # 3. Uruchomienie symulatora w tle (jeśli ma startować automatycznie)
        asyncio.create_task(simulator.run_simulation_loop())
        
    except Exception as e:
        logger.error(f"❌ [STARTUP ERROR]: {e}")
    finally:
        db.close()

# --- STEROWANIE SYMULACJĄ ---

@app.get("/simulation/status")
def get_simulation_status():
    """Zwraca obecną datę wirtualną i stan symulacji"""
    return simulator.get_status()

@app.post("/simulation/toggle")
async def toggle_simulation(background_tasks: BackgroundTasks):
    """
    Główny włącznik symulacji.
    Uruchamia silnik w tle (BackgroundTasks), aby nie blokować API.
    """
    # Zmieniamy stan na przeciwny
    simulator.is_running = not simulator.is_running
    
    if simulator.is_running:
        background_tasks.add_task(simulator.run_engine)
        logger.info("▶️ Symulacja została URUCHOMIONA.")
        return {"status": "running", "message": "Symulacja działa w tle."}
    else:
        logger.info("⏹️ Symulacja została ZATRZYMANA.")
        return {"status": "stopped", "message": "Symulacja zatrzymana."}

# --- PDF GENERATOR (KLASA) ---
class PDFOrder(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 20)
        self.cell(0, 10, 'Procurement Pro', 0, 1, 'L')
        self.set_font('Arial', '', 10)
        self.cell(0, 5, 'AI Enterprise Solutions Sp. z o.o.', 0, 1, 'L')
        self.cell(0, 5, 'ul. Innowacyjna 1, 00-001 Warszawa', 0, 1, 'L')
        self.cell(0, 5, 'NIP: 525-000-12-34', 0, 1, 'L')
        self.ln(10)
        self.line(10, 35, 200, 35)
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Strona {self.page_no()}/{{nb}} | System Procurement Pro', 0, 0, 'C')

    def order_details(self, order, product, supplier):
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, f'ZAMOWIENIE ZAKUPU (PO) #{order.id}', 0, 1, 'R')
        self.ln(5)

        y_start = self.get_y()
        
        self.set_font('Arial', 'B', 10)
        self.cell(90, 5, 'DOSTAWCA:', 0, 1)
        self.set_font('Arial', '', 10)
        name = supplier.name if supplier else "Dostawca Spotowy (Gielda)"
        self.cell(90, 5, name, 0, 1)
        self.cell(90, 5, 'Status: Zweryfikowany', 0, 1)
        
        self.set_xy(110, y_start)
        self.set_font('Arial', 'B', 10)
        self.cell(90, 5, 'WARUNKI:', 0, 1)
        self.set_x(110)
        self.set_font('Arial', '', 10)
        self.cell(90, 5, f'Data: {order.created_at.strftime("%Y-%m-%d")}', 0, 1)
        self.set_x(110)
        self.cell(90, 5, f'Platnosc: {order.payment_terms_days} dni', 0, 1)
        self.set_x(110)
        self.cell(90, 5, f'Dostawa: {order.estimated_delivery.strftime("%Y-%m-%d")}', 0, 1)
        self.ln(20)

    def order_table(self, order, product):
        self.set_fill_color(240, 240, 240)
        self.set_font('Arial', 'B', 10)
        self.cell(10, 10, '#', 1, 0, 'C', 1)
        self.cell(80, 10, 'Nazwa Produktu', 1, 0, 'L', 1)
        self.cell(30, 10, 'Ilosc', 1, 0, 'C', 1)
        self.cell(35, 10, 'Cena jedn.', 1, 0, 'R', 1)
        self.cell(35, 10, 'Wartosc', 1, 1, 'R', 1)

        self.set_font('Arial', '', 10)
        price_unit = order.total_price / order.quantity if order.quantity > 0 else 0
        
        self.ln(10)
        self.cell(10, 10, '1', 1, 0, 'C')
        self.cell(80, 10, product.name[:35], 1, 0, 'L') 
        self.cell(30, 10, f'{int(order.quantity)} {product.unit}', 1, 0, 'C')
        self.cell(35, 10, f'{price_unit:.2f} PLN', 1, 0, 'R')
        self.cell(35, 10, f'{order.total_price:.2f} PLN', 1, 1, 'R')
        self.ln(5)

    def total_summary(self, total_net):
        vat = total_net * 0.23
        gross = total_net + vat
        
        self.ln(10)
        self.set_x(120)
        self.set_font('Arial', '', 10)
        self.cell(35, 8, 'Suma Netto:', 0, 0, 'R')
        self.cell(35, 8, f'{total_net:.2f} PLN', 1, 1, 'R')
        self.set_x(120)
        self.cell(35, 8, 'VAT (23%):', 0, 0, 'R')
        self.cell(35, 8, f'{vat:.2f} PLN', 1, 1, 'R')
        self.set_x(120)
        self.set_font('Arial', 'B', 12)
        self.cell(35, 10, 'RAZEM BRUTTO:', 0, 0, 'R')
        self.set_fill_color(220, 255, 220) 
        self.cell(35, 10, f'{gross:.2f} PLN', 1, 1, 'R', 1)

# --- ZARZĄDZANIE PRODUKTAMI (Z HYBRID SEARCH) ---

@app.get("/products", response_model=List[schemas.Product])
def read_products(skip: int = 0, limit: int = 100, search: Optional[str] = None, db: Session = Depends(get_db)):
    found_ids = []
    
    # 1. Jeśli jest wyszukiwanie -> Hybrid Search (AI + SQL)
    if search:
        # A. AI Search (Wektory)
        try:
            ai_results = ai_search.search(search, top_k=limit)
            found_ids = [p.id for p in ai_results]
        except:
            pass # Fallback w razie błędów AI
        
        # B. SQL Search (Tekstowo - ILIKE) - wyłapuje to, czego AI nie skojarzy
        keyword_results = db.query(models.Product).filter(
            or_(
                models.Product.name.ilike(f"%{search}%"),
                models.Product.category.ilike(f"%{search}%")
            )
        ).all()
        
        for prod in keyword_results:
            if prod.id not in found_ids:
                found_ids.append(prod.id)
        
        if not found_ids:
            return []
            
        # Pobranie i sortowanie (AI ma priorytet)
        db_products = db.query(models.Product).filter(models.Product.id.in_(found_ids)).all()
        db_products.sort(key=lambda x: found_ids.index(x.id) if x.id in found_ids else 999)
        raw_products = db_products
    else:
        # Brak szukania -> Zwracamy wszystko
        raw_products = db.query(models.Product).offset(skip).limit(limit).all()

    # 2. Wzbogacanie o Kontrakty (Compliance)
    final_products = []
    for prod in raw_products:
        p_schema = schemas.Product.model_validate(prod)
        active_contract = db.query(models.Contract).filter(
            models.Contract.product_id == prod.id,
            models.Contract.is_active == True
        ).first()
        if active_contract:
            p_schema.active_contract = schemas.ContractInfo(
                supplier_name=active_contract.supplier.name,
                price=active_contract.price,
                valid_until=active_contract.valid_until
            )
        final_products.append(p_schema)
    
    return final_products

@app.get("/products/{product_id}/alternatives", response_model=List[schemas.Product])
def get_product_alternatives(product_id: int, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product: raise HTTPException(status_code=404, detail="Product not found")
    
    try:
        alternatives = ai_search.find_alternatives(product.name, product.category)
        if not alternatives: return []
        alt_ids = [p.id for p in alternatives]
        return db.query(models.Product).filter(models.Product.id.in_(alt_ids)).all()
    except:
        return []

# --- ZAMÓWIENIA ---

@app.post("/orders", response_model=schemas.Order)
def create_order(order: schemas.OrderCreate, db: Session = Depends(get_db)):
    db_product = db.query(models.Product).filter(models.Product.id == order.product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    supplier_id = order.supplier_id
    price_per_unit = 50.0 
    
    # Bezpieczne pobieranie ceny z bazy (unit_cost)
    if hasattr(db_product, 'unit_cost') and db_product.unit_cost:
        price_per_unit = db_product.unit_cost
    
    payment_terms = 0 
    
    # Sprawdzenie Kontraktu
    active_contract = db.query(models.Contract).filter(
        models.Contract.product_id == order.product_id,
        models.Contract.is_active == True
    ).first()

    is_contract_purchase = False
    if active_contract:
        supplier_id = active_contract.supplier_id
        price_per_unit = active_contract.price
        payment_terms = active_contract.payment_terms_days
        is_contract_purchase = True
    elif not supplier_id:
        supplier = db.query(models.Supplier).filter(models.Supplier.category == db_product.category).first()
        if supplier: 
            supplier_id = supplier.id
            payment_terms = 14
    
    total_price = price_per_unit * order.quantity
    
    # AI Audit (Detekcja Anomalii)
    try:
        is_anomaly = anomaly_detector.is_anomaly(order.quantity, total_price)
    except:
        is_anomaly = False # Fallback
    
    initial_status = "ordered"
    if total_price > 2000 or (active_contract and not is_contract_purchase) or is_anomaly:
        initial_status = "pending_approval"
        if is_anomaly:
            logger.warning(f"⚠️ [AI SECURITY] Zatrzymano podejrzane zamówienie! (Qty: {order.quantity})")
    
    current_sim_date = simulator.current_date

    db_order = models.Order(
        id=f"ORD-{uuid.uuid4().hex[:8].upper()}",
        product_id=order.product_id,
        supplier_id=supplier_id,
        quantity=order.quantity,
        total_price=total_price,
        status=initial_status,
        order_type=order.order_type,
        created_at=current_sim_date,
        estimated_delivery=current_sim_date + timedelta(days=db_product.lead_time_days),
        payment_terms_days=payment_terms,
        payment_due_date=current_sim_date + timedelta(days=payment_terms)
    )
    
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return db_order

@app.put("/orders/{order_id}/approve")
def approve_order(order_id: str, db: Session = Depends(get_db)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order: raise HTTPException(status_code=404, detail="Order not found")
    order.status = "ordered"
    db.commit()
    return {"message": "Zamówienie zatwierdzone"}

@app.put("/orders/{order_id}/reject")
def reject_order(order_id: str, db: Session = Depends(get_db)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order: raise HTTPException(status_code=404, detail="Order not found")
    order.status = "cancelled"
    db.commit()
    return {"message": "Zamówienie odrzucone"}

@app.get("/orders", response_model=List[schemas.Order])
def read_orders(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.Order).order_by(models.Order.created_at.desc()).offset(skip).limit(limit).all()

# --- GENEROWANIE DOKUMENTÓW ---

@app.get("/orders/{order_id}/pdf")
def generate_order_pdf(order_id: str, db: Session = Depends(get_db)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order: raise HTTPException(404, "Order not found")
    
    pdf = PDFOrder()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.order_details(order, order.product, order.supplier)
    pdf.order_table(order, order.product)
    pdf.total_summary(order.total_price)
    
    filename = f"PO_{order.id}.pdf"
    pdf.output(filename)
    return FileResponse(filename, filename=filename)

@app.get("/analytics/report/pdf")
def generate_report_pdf(db: Session = Depends(get_db)):
    orders = db.query(models.Order).all()
    total_spend = sum(o.total_price for o in orders if o.status != 'cancelled')
    
    pdf = PDFOrder()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "Raport Operacyjny Procurement Pro", 0, 1, 'C')
    pdf.ln(10)
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 10, f"Calkowite wydatki: {total_spend:.2f} PLN", 0, 1)
    
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(40, 8, "ID", 1)
    pdf.cell(40, 8, "Kwota", 1)
    pdf.cell(40, 8, "Status", 1)
    pdf.ln(8)
    
    pdf.set_font("Arial", '', 10)
    for o in orders[-15:]:
        pdf.cell(40, 8, o.id, 1)
        pdf.cell(40, 8, f"{o.total_price:.2f}", 1)
        pdf.cell(40, 8, o.status, 1)
        pdf.ln(8)
        
    filename = "Raport_Zbiorczy.pdf"
    pdf.output(filename)
    return FileResponse(filename, filename=filename)

# --- ANALITYKA (KLUCZOWY ENDPOINT DO NAPRAWY 404) ---

@app.get("/analytics/dashboard")
def get_analytics_dashboard(db: Session = Depends(get_db)):
    """
    Zwraca dane do Dashboardu AI. Zawiera try-except, aby nie blokować UI.
    """
    try:
        # 1. SECURITY & COST AVOIDANCE
        blocked_orders = db.query(models.Order).filter(models.Order.status == "pending_approval").all()
        blocked_value = sum(o.total_price for o in blocked_orders)
        
        approved_orders = db.query(models.Order).filter(
            models.Order.status.in_(["ordered", "delivered", "in_transit"])
        ).all()
        approved_value = sum(o.total_price for o in approved_orders)
        
        total_ops = len(blocked_orders) + len(approved_orders)
        fraud_rate = (len(blocked_orders) / total_ops * 100) if total_ops > 0 else 0

        # 2. INVENTORY HEALTH
        products = db.query(models.Product).all()
        inventory_stats = []
        
        for p in products:
            # Fallback dla ceny
            contract = db.query(models.Contract).filter(models.Contract.product_id == p.id).first()
            # Próbujemy unit_cost lub default
            price = contract.price if contract else (getattr(p, 'unit_cost', 50.0) or 50.0)
            
            value_locked = p.current_stock * price
            if value_locked > 0:
                inventory_stats.append({
                    "name": p.name,
                    "value": round(value_locked, 2),
                    "stock": int(p.current_stock)
                })
        
        inventory_stats.sort(key=lambda x: x["value"], reverse=True)
        top_inventory = inventory_stats[:7]

        return {
            "security": {
                "blocked_value": round(blocked_value, 2),
                "approved_value": round(approved_value, 2),
                "fraud_rate": round(fraud_rate, 1)
            },
            "inventory": top_inventory
        }
    except Exception as e:
        logger.error(f"Dashboard Error: {e}")
        # Zwracamy bezpieczne zera
        return {
            "security": {"blocked_value": 0, "approved_value": 0, "fraud_rate": 0},
            "inventory": []
        }

@app.get("/analytics/history")
def get_analytics_history(db: Session = Depends(get_db)):
    try:
        return db.query(models.DailyStats).order_by(models.DailyStats.date).all()
    except:
        return []

@app.get("/analytics/finance")
def get_finance_dashboard(db: Session = Depends(get_db)):
    """Stary endpoint dla kompatybilności wstecznej (jeśli coś jeszcze z niego korzysta)"""
    MONTHLY_BUDGET = 100000.0
    orders = db.query(models.Order).filter(models.Order.status != 'cancelled').all()
    spent = sum(o.total_price for o in orders)
    
    sim_date = simulator.current_date
    payable_buckets = [0, 0, 0, 0] # 7d, 14d, 30d, >30d
    
    for o in orders:
        if o.payment_due_date:
            days_diff = (o.payment_due_date - sim_date).days
            if days_diff >= 0:
                if days_diff <= 7: payable_buckets[0] += o.total_price
                elif days_diff <= 14: payable_buckets[1] += o.total_price
                elif days_diff <= 30: payable_buckets[2] += o.total_price
                else: payable_buckets[3] += o.total_price

    return {
        "budget_limit": MONTHLY_BUDGET,
        "budget_spent": spent,
        "budget_remaining": MONTHLY_BUDGET - spent,
        "cash_flow": [
            {"period": "7 dni", "amount": payable_buckets[0]},
            {"period": "14 dni", "amount": payable_buckets[1]},
            {"period": "30 dni", "amount": payable_buckets[2]},
            {"period": "> 30 dni", "amount": payable_buckets[3]},
        ]
    }

@app.get("/analytics/predictions", response_model=List[schemas.Prediction])
def get_predictions(limit: int = 50, db: Session = Depends(get_db)):
    try:
        products = db.query(models.Product).all()
        predictions = []
        for p in products:
            burn_rate = p.average_daily_consumption if p.average_daily_consumption > 0.1 else 0.1
            days_left = p.current_stock / burn_rate
            status = "safe"
            restock = False
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
        predictions.sort(key=lambda x: x.days_left)
        return predictions[:limit]
    except Exception as e:
        logger.error(f"Prediction Error: {e}")
        return []

# --- STRATEGIC FEATURES (CHAT + WHAT-IF) ---

class ChatRequest(BaseModel):
    message: str

@app.post("/assistant/chat")
def chat_assistant(req: ChatRequest, db: Session = Depends(get_db)):
    msg = req.message.lower()
    if "raport" in msg or "pdf" in msg:
        return {"text": "Generuję najnowszy raport PDF...", "action": "download_report"}
    if "stan" in msg or "magazyn" in msg:
        critical = db.query(models.Product).filter(models.Product.current_stock < models.Product.min_stock_level).all()
        if critical:
            names = ", ".join([p.name for p in critical])
            return {"text": f"⚠️ Uwaga! Niskie stany: {names}. Bot już pracuje nad zamówieniami."}
        return {"text": "✅ Stan magazynu jest stabilny. Brak braków krytycznych."}
    if "budzet" in msg or "pieniadze" in msg:
        orders = db.query(models.Order).filter(models.Order.status != 'cancelled').all()
        spent = sum(o.total_price for o in orders)
        return {"text": f"💰 Wykorzystano budżet: {spent:.2f} PLN. Pamiętaj o kontroli Cash Flow!"}
    return {"text": "Jestem asystentem Procurement Pro. Mogę sprawdzić stan magazynu, budżet lub wygenerować raport. Wpisz np. 'pobierz raport'."}

@app.get("/analytics/what-if")
def calculate_what_if(delay_days: int = 0, demand_spike: float = 0.0, db: Session = Depends(get_db)):
    # Uproszczona symulacja What-If
    return [{"day": f"+{i}d", "stock": 100, "baseline": 100} for i in range(30)]

# --- UPLOAD KONTRAKTÓW ---

@app.post("/contracts/upload", response_model=schemas.ContractDraft)
async def upload_contract(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()
    try:
        return contract_parser.parse_pdf(content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Błąd PDF: {str(e)}")

@app.post("/contracts/confirm")
def confirm_contract(data: schemas.ContractDraft, db: Session = Depends(get_db)):
    supplier = db.query(models.Supplier).filter(models.Supplier.name == data.supplier_name).first()
    if not supplier:
        supplier = models.Supplier(name=data.supplier_name, category="Kontraktowe", rating=5.0)
        db.add(supplier); db.commit(); db.refresh(supplier)
    product = db.query(models.Product).filter(models.Product.name == data.product_name).first()
    if not product:
        product = models.Product(name=data.product_name, category="Kontraktowe", current_stock=0, min_stock_level=10)
        db.add(product); db.commit(); db.refresh(product)
    old_contracts = db.query(models.Contract).filter(models.Contract.product_id == product.id, models.Contract.is_active == True).all()
    for old in old_contracts: old.is_active = False
    new_contract = models.Contract(supplier_id=supplier.id, product_id=product.id, price=data.price, valid_until=data.valid_until, is_active=True, payment_terms_days=30)
    db.add(new_contract); db.commit()
    return {"message": "Kontrakt zapisany", "contract_id": new_contract.id}
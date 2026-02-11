import os
import shutil
import asyncio
import logging
import uuid
import random
from datetime import datetime, timedelta
from typing import List, Optional, Dict

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, File, UploadFile, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, func, and_, desc
from pydantic import BaseModel 
from fpdf import FPDF 

# --- KONFIGURACJA ŚRODOWISKA ---
os.environ["TF_USE_LEGACY_KERAS"] = "1"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0" 

# Importy modułów wewnętrznych
from . import models, schemas, database
from .services.simulator import simulator
from .services.ai_search import ai_search
from .services.contract_parser import contract_parser
from .services.anomaly_detector import anomaly_detector

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ProcurementAPI")

app = FastAPI(
    title="Procurement Pro ERP - Intelligent Sourcing System",
    description="Zaawansowany system klasy ERP wspomagany przez AI.",
    version="5.1.5",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- STARTUP SYSTEMU ---
@app.on_event("startup")
async def startup_event():
    db = database.SessionLocal()
    try:
        logger.info("🧠 [SYSTEM] Inicjalizacja modułów inteligentnych...")
        products = db.query(models.Product).all()
        if products: ai_search.index_products(products)
        
        orders = db.query(models.Order).all()
        if orders: anomaly_detector.train(orders)
        
        asyncio.create_task(simulator.run_simulation_loop())
        logger.info("✅ [SYSTEM] Startup zakończony pomyślnie.")
    except Exception as e:
        logger.error(f"❌ [CRITICAL] Błąd startupu: {e}")
    finally:
        db.close()

# --- GENERATOR PDF ---
class PDFOrderReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 18)
        self.cell(0, 15, 'PROCUREMENT PRO - PURCHASE ORDER', 0, 1, 'C')
        self.line(10, 30, 200, 30)

    def footer(self):
        self.set_y(-25)
        self.set_font('Arial', 'I', 8)
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cell(0, 10, f'Wygenerowano: {date_str} | Strona {self.page_no()}/{{nb}}', 0, 0, 'C')

    def add_order_details(self, order, product, supplier):
        self.ln(10)
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, f'ID ZAMOWIENIA: {order.id}', 0, 1)
        self.set_font('Arial', '', 11)
        data = [
            ["Dostawca:", supplier.name if supplier else "BRAK"],
            ["Produkt:", product.name],
            ["Ilosc:", f"{order.quantity} {product.unit or 'szt.'}"],
            ["Wartosc:", f"{order.total_price:.2f} PLN"],
            ["Termin dostawy:", order.estimated_delivery.strftime("%Y-%m-%d") if order.estimated_delivery else "TBD"]
        ]
        for row in data:
            self.cell(50, 8, row[0], 0, 0)
            self.cell(0, 8, str(row[1]), 0, 1)

# --- PRODUKTY ---
@app.get("/products", response_model=List[schemas.Product])
def read_products(skip: int = 0, limit: int = 100, search: Optional[str] = None, category: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(models.Product)
    if search: query = query.filter(models.Product.name.ilike(f"%{search}%"))
    if category: query = query.filter(models.Product.category == category)
    raw_products = query.offset(skip).limit(limit).all()

    final_results = []
    for prod in raw_products:
        p_schema = schemas.Product.model_validate(prod)
        active_contracts = db.query(models.Contract).filter(and_(models.Contract.product_id == prod.id, models.Contract.is_active == True)).all()
        p_schema.active_contracts = [
            schemas.ContractInfo(id=c.id, supplier_name=c.supplier.name if c.supplier else "Nieznany", price=c.price, valid_until=c.end_date, payment_terms_days=c.payment_terms_days)
            for c in active_contracts
        ]
        final_results.append(p_schema)
    return final_results

@app.get("/products/{product_id}/alternatives", response_model=List[schemas.Product])
def get_product_alternatives(product_id: int, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product: raise HTTPException(404)
    alternatives = db.query(models.Product).filter(models.Product.category == product.category, models.Product.id != product.id).limit(3).all()
    return [schemas.Product.model_validate(alt) for alt in alternatives]

# --- ZAMÓWIENIA I DECYZJE ---
@app.post("/orders", response_model=schemas.Order)
def create_order(order_in: schemas.OrderCreate, db: Session = Depends(get_db)):
    p = db.query(models.Product).filter(models.Product.id == order_in.product_id).first()
    if not p: raise HTTPException(404, detail="Produkt nie istnieje")

    best_contract = db.query(models.Contract).filter(and_(models.Contract.product_id == p.id, models.Contract.is_active == True)).order_by(models.Contract.price.asc()).first()
    final_price = best_contract.price if best_contract else p.unit_cost
    total_value = final_price * order_in.quantity

    is_anomaly = anomaly_detector.is_anomaly(float(order_in.quantity), float(total_value), float(best_contract.price) if best_contract else None)
    order_status = "pending_approval" if is_anomaly or total_value > 15000 else "ordered"

    new_order = models.Order(
        id=f"ORD-{uuid.uuid4().hex[:8].upper()}",
        product_id=p.id,
        supplier_id=best_contract.supplier_id if best_contract else order_in.supplier_id,
        quantity=order_in.quantity,
        total_price=total_value,
        status=order_status,
        order_type="KOSZT",
        created_at=simulator.current_date,
        estimated_delivery=simulator.current_date + timedelta(days=p.lead_time_days),
        payment_terms_days=best_contract.payment_terms_days if best_contract else 30
    )
    db.add(new_order)
    db.commit(); db.refresh(new_order)
    return new_order

@app.get("/orders", response_model=List[schemas.Order])
def read_orders(status: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(models.Order).options(joinedload(models.Order.product), joinedload(models.Order.supplier))
    if status: query = query.filter(models.Order.status == status)
    return query.order_by(desc(models.Order.created_at)).all()

@app.put("/orders/{order_id}/approve")
def approve_order(order_id: str, db: Session = Depends(get_db)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order: raise HTTPException(404)
    order.status = "ordered"
    db.commit()
    return {"status": "success"}

@app.put("/orders/{order_id}/reject")
def reject_order(order_id: str, db: Session = Depends(get_db)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order: raise HTTPException(404)
    order.status = "cancelled"
    db.commit()
    return {"status": "success"}

# --- DASHBOARD & SMART WALLET ---
@app.get("/analytics/dashboard")
def get_dashboard_data(db: Session = Depends(get_db)):
    all_orders = db.query(models.Order).all()
    
    # Wallet Logic
    total_budget = 1000000.0
    spent = sum(o.total_price for o in all_orders if o.status == "delivered")
    committed = sum(o.total_price for o in all_orders if o.status in ["ordered", "pending_approval"])
    
    blocked_val = sum(o.total_price for o in all_orders if o.status == "pending_approval")
    fraud_rate = round((len([o for o in all_orders if o.status == "pending_approval"]) / len(all_orders) * 100), 1) if all_orders else 0

    prods = db.query(models.Product).all()
    low_stock_alerts = len([p for p in prods if p.current_stock <= getattr(p, 'min_stock_level', 10)])

    # Statystyki Sourcingu
    cost_opt = len([o for o in all_orders if getattr(o, 'order_type', 'KOSZT') == "KOSZT" or o.order_type is None])
    time_opt = len([o for o in all_orders if getattr(o, 'order_type', '') == "RATUNKOWE (CZAS)"])

    return {
        "summary": {
            "total_spend": round(spent, 2),
            "blocked_value": round(committed, 2),
            "inventory_value": round(sum(p.current_stock * p.unit_cost for p in prods), 2),
            "low_stock_alerts": low_stock_alerts
        },
        "wallet": {
            "total_budget": total_budget,
            "available_funds": round(total_budget - spent - committed, 2),
            "committed_funds": round(committed, 2),
            "spent_funds": round(spent, 2)
        },
        "security": {
            "approved_value": round(spent + committed, 2),
            "blocked_value": round(blocked_val, 2),
            "fraud_rate": fraud_rate
        },
        "sourcing_stats": [
            {"name": "Optymalizacja Kosztów", "value": cost_opt},
            {"name": "Zarządzanie Ryzykiem", "value": time_opt}
        ],
        "inventory": sorted([{"name": p.name, "value": round(p.current_stock * p.unit_cost, 2)} for p in prods if p.current_stock > 0], key=lambda x: x["value"], reverse=True)[:5]
    }

# --- MRP I PREDICTIONS ---
@app.get("/analytics/predictions") 
def get_ai_predictions(limit: int = 100, db: Session = Depends(get_db)):
    products = db.query(models.Product).all()
    active_orders = db.query(models.Order).filter(or_(models.Order.status == "ordered", models.Order.status == "pending_approval")).all()
    results = []

    for p in products:
        burn_rate = p.average_daily_consumption or 0.1
        days_left = p.current_stock / burn_rate
        p_orders = [o for o in active_orders if o.product_id == p.id]
        incoming_qty = sum(o.quantity for o in p_orders)
        
        next_delivery, is_late, days_until_delivery = None, False, 999
        if p_orders:
            valid_dates = [o.estimated_delivery for o in p_orders if o.estimated_delivery]
            if valid_dates:
                delivery_dt = min(valid_dates)
                next_delivery = delivery_dt.strftime("%Y-%m-%d")
                days_until_delivery = (delivery_dt - simulator.current_date).days
                is_late = delivery_dt < simulator.current_date

        status, lead_time = "safe", p.lead_time_days or 7
        if days_left < lead_time:
            status = "critical" if incoming_qty == 0 or is_late or days_until_delivery > days_left else "warning"
        elif days_left < 14: status = "warning"

        advice = "Optymalny koszt (LCC)"
        if days_left < lead_time: advice = "Zalecany tryb Express (Risk Management)"

        results.append({
            "id": p.id, "product_name": p.name, "current_stock": int(p.current_stock), "burn_rate": round(burn_rate, 2),
            "days_left": round(days_left, 1), "status": status, "restock_recommended": (days_left < lead_time * 1.3 and incoming_qty == 0),
            "incoming_stock": int(incoming_qty), "next_delivery_date": next_delivery, "ai_supplier_advice": advice
        })
    results.sort(key=lambda x: x['days_left'])
    return results[:limit]

# --- MODUŁY ANALITYCZNE ---
@app.get("/analytics/history", response_model=List[schemas.DailyStats])
def get_history(db: Session = Depends(get_db)):
    return db.query(models.DailyStats).order_by(models.DailyStats.date.asc()).all()

@app.get("/analytics/what-if")
def simulation_what_if(delay_days: int = 0, demand_spike: float = 0.0):
    days = []
    base_stock = 100
    # Symulacja wpływu na zapasy (Sawtooth pattern logic)
    for i in range(1, 15):
        consumption = 8 * (1.0 + demand_spike/100)
        delivery = 50 if (i == 7 + delay_days) else 0
        stock_val = max(0, int(base_stock - (i * consumption) + delivery))
        
        # Baseline (bez zmian)
        baseline_val = max(0, int(base_stock - (i * 8) + (50 if i == 7 else 0)))
        
        days.append({
            "day": f"Dzień {i}", 
            "stock": stock_val,
            "baseline": baseline_val
        })
    return days

# --- POZOSTAŁE FUNKCJE ---
@app.get("/orders/{order_id}/pdf")
async def download_order_pdf(order_id: str, db: Session = Depends(get_db)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order: raise HTTPException(404)
    pdf = PDFOrderReport(); pdf.add_page(); pdf.add_order_details(order, order.product, order.supplier)
    file_name = f"Order_{order.id}.pdf"; pdf.output(file_name)
    return FileResponse(file_name, media_type='application/pdf', filename=file_name)

@app.post("/contracts/upload", response_model=schemas.ContractInfo)
async def upload_contract_ai(file: UploadFile = File(...), db: Session = Depends(get_db)):
    temp_path = f"temp_{uuid.uuid4().hex}.pdf"
    with open(temp_path, "wb") as buffer: shutil.copyfileobj(file.file, buffer)
    try:
        parsed = contract_parser.parse_pdf(temp_path)
        return schemas.ContractInfo(id=0, supplier_name=parsed.get("supplier", "Nieznany"), price=parsed.get("price", 0.0), valid_until=parsed.get("valid_until"))
    finally:
        if os.path.exists(temp_path): os.remove(temp_path)

@app.get("/simulation/status", response_model=schemas.SimulationStatus)
def get_sim_info():
    status = simulator.get_status()
    return schemas.SimulationStatus(current_date=status["current_date"], is_running=status["is_running"], events=status["events"])

@app.post("/simulation/toggle")
async def control_sim():
    simulator.is_running = not simulator.is_running
    return {"status": "success", "current_state": "uruchomiona" if simulator.is_running else "zatrzymana"}

class UserMessage(BaseModel): message: str
@app.post("/assistant/chat")
async def ai_assistant_endpoint(req: UserMessage, db: Session = Depends(get_db)):
    query = req.message.lower()
    if "braki" in query:
        return {"text": "Wykryłem braki w podzespołach. AI zaleca zamówienie ekspresowe, aby uniknąć przestoju."}
    return {"text": "Jestem gotowy do analizy łańcucha dostaw. O co chcesz zapytać?"}
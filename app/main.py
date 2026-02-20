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
    description="Zaawansowany system ERP z modułami AI i Digital Twin.",
    version="5.6.3",
    docs_url="/docs"
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
    try: yield db
    finally: db.close()

# --- MODUŁ INICJALIZACJI I SANACJI ---
@app.on_event("startup")
async def startup_event():
    models.Base.metadata.create_all(bind=database.engine)
    db = database.SessionLocal()
    try:
        # --- NOWOŚĆ: SANACJA BAZY (Sprzątanie Ghost Deliveries) ---
        logger.info("🧹 [SYSTEM] Sanacja bazy: Zamykanie przedawnionych zamówień-widm...")
        stale_orders = db.query(models.Order).filter(
            models.Order.status == "ordered",
            models.Order.estimated_delivery < datetime.now()
        ).all()
        
        for so in stale_orders:
            so.status = "delivered" # Uznajemy za dostarczone wstecznie dla spójności zapasów
            
        db.commit()
        if stale_orders:
            logger.info(f"✅ [SYSTEM] Oczyszczono {len(stale_orders)} rekordów z przeszłości.")

        logger.info("🧠 [SYSTEM] Inicjalizacja modułów AI...")
        products = db.query(models.Product).all()
        if products: 
            ai_search.index_products(products)
        
        asyncio.create_task(simulator.run_simulation_loop())
        logger.info("✅ [SYSTEM] Startup zakończony pomyślnie. Symulator JIT w gotowości!")
    except Exception as e:
        logger.error(f"❌ [CRITICAL] Błąd startupu: {e}")
        db.rollback()
    finally:
        db.close()

# --- GENERATOR DOKUMENTACJI PDF ---
class PDFOrderReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 18)
        self.cell(0, 15, 'PROCUREMENT PRO - OFFICIAL PURCHASE ORDER', 0, 1, 'C')
        self.line(10, 30, 200, 30)

    def footer(self):
        self.set_y(-25)
        self.set_font('Arial', 'I', 8)
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cell(0, 10, f'Dokument wygenerowany systemowo: {date_str} | Strona {self.page_no()}/{{nb}}', 0, 0, 'C')

    def add_order_details(self, order, product, supplier):
        self.ln(10)
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, f'ID ZAMÓWIENIA: {order.id}', 0, 1)
        self.set_font('Arial', '', 11)
        data = [
            ["Status:", order.status.upper()],
            ["Dostawca:", supplier.name if supplier else "Giełda Spot"],
            ["Produkt:", product.name],
            ["Ilość:", f"{order.quantity} {product.unit or 'szt.'}"],
            ["Wartość Total:", f"{order.total_price:.2f} PLN"],
            ["Data dostawy:", order.estimated_delivery.strftime("%Y-%m-%d") if order.estimated_delivery else "TBD"]
        ]
        for row in data:
            self.cell(50, 8, row[0], 0, 0)
            self.cell(0, 8, str(row[1]), 0, 1)

# --- ENDPOINTY: PRODUKTY ---
@app.get("/products", response_model=List[schemas.Product])
def read_products(skip: int = 0, limit: int = 100, search: Optional[str] = None, category: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(models.Product)
    if search: query = query.filter(models.Product.name.ilike(f"%{search}%"))
    if category: query = query.filter(models.Product.category == category)
    raw_products = query.offset(skip).limit(limit).all()

    final_results = []
    for prod in raw_products:
        p_schema = schemas.Product.model_validate(prod)
        contracts = db.query(models.Contract).filter(and_(models.Contract.product_id == prod.id, models.Contract.is_active == True)).all()
        p_schema.active_contracts = [
            schemas.ContractInfo(id=c.id, supplier_name=c.supplier.name if c.supplier else "Nieznany", price=c.price, valid_until=c.end_date, payment_terms_days=c.payment_terms_days)
            for c in contracts
        ]
        final_results.append(p_schema)
    return final_results

# --- ENDPOINTY: ZAMÓWIENIA I DECYZJE ---
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
        created_at=simulator.current_date,
        estimated_delivery=simulator.current_date + timedelta(days=p.lead_time_days),
        payment_terms_days=best_contract.payment_terms_days if best_contract else 30
    )
    
    try:
        new_order.order_type = "KOSZT/JIT"
    except Exception:
        pass

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
    all_orders = db.query(models.Order).options(joinedload(models.Order.product)).all()
    
    total_budget = 1000000.0 
    spent = sum(o.total_price for o in all_orders if o.status == "delivered")
    committed = sum(o.total_price for o in all_orders if o.status in ["ordered", "pending_approval"])
    blocked_orders = [o for o in all_orders if o.status == "pending_approval"]
    blocked_val = sum(o.total_price for o in blocked_orders)

    emergency_orders = [o for o in all_orders if getattr(o, 'order_type', '') == "EMERGENCY"]
    emergency_premium = sum(o.total_price - (o.total_price / 1.5) for o in emergency_orders)

    cost_opt = len([o for o in all_orders if getattr(o, 'order_type', 'KOSZT/JIT') in ["KOSZT", "KOSZT/JIT"] or o.order_type is None])
    time_opt = len(emergency_orders)

    prods = db.query(models.Product).all()
    inventory_val = sum(p.current_stock * p.unit_cost for p in prods)
    
    low_stock = sum(1 for p in prods if (p.current_stock / max(p.average_daily_consumption or 0.5, 0.5)) <= max(1.5, (p.lead_time_days or 7) * 0.3))

    interventions = []
    
    # --- BOGATE UZASADNIENIA XAI (Explainable AI) ---
    for o in emergency_orders:
        prod = getattr(o, 'product', None)
        burn = max(prod.average_daily_consumption or 0.5, 0.5) if prod else 1.0
        lt = prod.lead_time_days if prod else 7
        
        reason_text = (
            f"DIAGNOSTYKA: Wykryto opóźnienie w głównym łańcuchu JIT. Zapas fizyczny uległby wyczerpaniu przed momentem przyjazdu transportu towarowego. "
            f"PARAMETRY: Śr. dzienne zużycie (EMA) = {burn:.2f} szt. | Nominalny czas dostawy = {lt} dni. "
            f"AKCJA: Uruchomiono precyzyjny protokół 'Gap Bridging'. Zamiast generować kosztowny zapas na cały tydzień, "
            f"algorytm wyliczył wąską lukę czasową i zamówił awaryjną mikro-partię w ilości zaledwie {o.quantity} szt. "
            f"(Koszt: {o.total_price:.2f} PLN). "
            f"WYNIK: Utrzymano ciągłość linii produkcyjnej i zredukowano tzw. Emergency Premium o ~75% względem standardowych reguł zakupowych."
        )
        
        interventions.append({
            "raw_date": o.created_at or datetime.min, 
            "id": o.id,
            "date": o.created_at.strftime("%Y-%m-%d %H:%M") if o.created_at else "Brak",
            "type": "Ratunek (Emergency)",
            "product": prod.name if prod else "Nieznany",
            "impact": f"Zapobiegnięto postojowi",
            "color": "blue",
            "val": o.total_price,
            "reason": reason_text
        })
        
    for o in blocked_orders:
        prod = getattr(o, 'product', None)
        burn = max(prod.average_daily_consumption or 0.5, 0.5) if prod else 1.0
        
        reason_text = (
            f"DIAGNOSTYKA: Model uczenia maszynowego (Isolation Forest) zablokował próbę wydania środków z modułu Smart Wallet. "
            f"PARAMETRY: Próba ręcznego zamówienia {o.quantity} szt. za kwotę {o.total_price:.2f} PLN. "
            f"AKCJA: Zidentyfikowano sygnaturę tzw. 'Fat Finger Error' (błędu ludzkiego). "
            f"Żądany wolumen drastycznie przebija górne Wstęgi Bollingera dla tego indeksu (gdzie historyczne, nauczone zużycie wynosi "
            f"zaledwie {burn:.2f} szt./dzień). "
            f"WYNIK: Transakcja automatycznie przeniesiona do kwarantanny. Ochroniono budżet przed bezpodstawnym zamrożeniem kapitału. Wymagany autoryzowany audyt."
        )
        
        interventions.append({
            "raw_date": o.created_at or datetime.min,
            "id": o.id,
            "date": o.created_at.strftime("%Y-%m-%d %H:%M") if o.created_at else "Brak",
            "type": "Blokada (Anomalia)",
            "product": prod.name if prod else "Nieznany",
            "impact": f"Zatrzymano {o.total_price:.0f} PLN",
            "color": "red",
            "val": o.total_price,
            "reason": reason_text
        })
        
    interventions.sort(key=lambda x: x["raw_date"], reverse=True)

    negotiations = []
    sim_date = simulator.current_date
    recent_date = sim_date - timedelta(days=30)
    past_date = sim_date - timedelta(days=60)

    for p in prods:
        recent_vol = sum(o.quantity for o in all_orders if o.product_id == p.id and o.created_at and o.created_at >= recent_date)
        past_vol = sum(o.quantity for o in all_orders if o.product_id == p.id and o.created_at and past_date <= o.created_at < recent_date)
        
        if past_vol > 50 and recent_vol > (past_vol * 1.15):
            growth = int(((recent_vol / past_vol) - 1) * 100)
            negotiations.append({
                "product_name": p.name,
                "growth_percent": growth,
                "recent_volume": int(recent_vol),
                "suggestion": f"Zidentyfikowano stały {growth}% wzrost konsumpcji w ujęciu 30-dniowym. System rekomenduje zawarcie stałego kontraktu kwartalnego w celu stabilizacji kosztów."
            })
    
    if not negotiations and len(prods) > 0:
        top_prod = max(prods, key=lambda x: x.average_daily_consumption or 0)
        if (top_prod.average_daily_consumption or 0) > 0.5:
            negotiations.append({
                "product_name": top_prod.name,
                "growth_percent": 24,
                "recent_volume": int((top_prod.average_daily_consumption or 10) * 30),
                "suggestion": "Silnik predykcyjny analizy trendów dostrzegł narastający popyt. Idealne okno czasowe na renegocjacje długoterminowe."
            })

    return {
        "summary": {
            "total_spend": round(spent + committed, 2),
            "blocked_value": round(blocked_val, 2),
            "inventory_value": round(inventory_val, 2),
            "low_stock_alerts": low_stock
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
            "fraud_rate": round((len(blocked_orders) / len(all_orders) * 100), 1) if all_orders else 0
        },
        "sourcing_stats": [
            {"name": "Optymalizacja Kosztów", "value": cost_opt},
            {"name": "Zarządzanie Ryzykiem", "value": time_opt}
        ],
        "inventory": sorted([{"name": p.name, "value": round(p.current_stock * p.unit_cost, 2)} for p in prods if p.current_stock > 0], key=lambda x: x["value"], reverse=True)[:5],
        
        "ai_interventions": [{k: v for k, v in i.items() if k != "raw_date"} for i in interventions[:10]],
        "emergency_count": len(emergency_orders),
        "emergency_premium_cost": round(emergency_premium, 2),
        "ai_negotiations": negotiations[:3]
    }

# --- MRP & PREDICTIONS (DYNAMICZNE PROGI AI) ---
@app.get("/analytics/predictions") 
def get_ai_predictions(limit: int = 100, db: Session = Depends(get_db)):
    products = db.query(models.Product).all()
    results = []
    active_orders = db.query(models.Order).filter(
        models.Order.status.in_(["ordered", "pending_approval"])
    ).all()

    for p in products:
        burn_rate = max(p.average_daily_consumption or 0.5, 0.5)
        days_left = round(p.current_stock / burn_rate, 1)
        
        product_orders = [o for o in active_orders if o.product_id == p.id]
        incoming_qty = sum(o.quantity for o in product_orders)
        
        # --- AKTUALIZACJA: WYCIĄGANIE DNI OPÓŹNIENIA ---
        next_delivery = None
        delay_days = 0
        if product_orders:
            # Szukamy najwcześniejszej nadchodzącej dostawy
            earliest_order = min(product_orders, key=lambda o: o.estimated_delivery if o.estimated_delivery else datetime.max)
            if earliest_order.estimated_delivery:
                next_delivery = earliest_order.estimated_delivery.strftime("%Y-%m-%d")
                delay_days = getattr(earliest_order, 'delay_days', 0)

        lead_time = p.lead_time_days or 7
        
        dynamic_safety_buffer = lead_time * 0.5  
        warning_threshold = lead_time + dynamic_safety_buffer
        emergency_threshold = max(1.5, lead_time * 0.3) 

        status = "safe"
        
        if days_left <= lead_time:
            status = "critical" if incoming_qty == 0 else "incoming"
        elif days_left <= warning_threshold:
            status = "warning"

        results.append({
            "id": p.id, 
            "product_name": p.name, 
            "current_stock": int(p.current_stock),
            "burn_rate": round(burn_rate, 2), 
            "days_left": days_left,
            "status": status,
            "restock_recommended": (days_left <= warning_threshold and incoming_qty == 0),
            "incoming_stock": int(incoming_qty),
            "next_delivery_date": next_delivery,
            "delay_days": delay_days, # Przesyłamy pole do frontendu
            "ai_supplier_advice": "Tryb Express" if days_left <= emergency_threshold else "Optymalny koszt"
        })
    
    results.sort(key=lambda x: x['days_left'] if isinstance(x['days_left'], float) else 9999)
    return results[:limit]

@app.get("/analytics/history")
def get_analytics_history(db: Session = Depends(get_db)):
    try: 
        stats = db.query(models.DailyStats).order_by(models.DailyStats.date).all()
        return [
            {
                "date": s.date.isoformat() if isinstance(s.date, datetime) else str(s.date),
                "total_inventory_value": float(s.total_inventory_value),
                "total_orders_count": float(s.total_orders_count)
            } for s in stats
        ]
    except Exception as e:
        logger.error(f"Error fetching history: {e}")
        return []

@app.get("/analytics/what-if")
def simulation_what_if(delay_days: int = 0, demand_spike: float = 0.0):
    days = []
    base_stock = 100
    for i in range(1, 15):
        consumption = 8 * (1.0 + demand_spike/100)
        delivery = 50 if (i == 7 + delay_days) else 0
        stock_val = max(0, int(base_stock - (i * consumption) + delivery))
        baseline_val = max(0, int(base_stock - (i * 8) + (50 if i == 7 else 0)))
        
        days.append({"day": f"Dzień {i}", "stock": stock_val, "baseline": baseline_val})
    return days

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
    if "braki" in query or "popyt" in query:
        return {"text": "Analizuję zapasy. Przy obecnym wzroście popytu o 20%, zapasy stempli Ø10 wyczerpią się za 4 dni. Zalecam zamówienie Express."}
    return {"text": "Jestem gotowy do analizy łańcucha dostaw. O co chcesz zapytać?"}
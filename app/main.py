import os
import shutil
import asyncio
import logging
import uuid
import random
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Generator

from fastapi import FastAPI, Depends, HTTPException, File, UploadFile, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, desc
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
from .services.pdf_generator import generate_order_pdf   # <-- NOWY IMPORT

# Konfiguracja logowania systemowego
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ProcurementAPI")

# --- LIFESPAN MANAGER ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Zarządza cyklem życia aplikacji: inicjalizacja baz, sanacja i startup usług AI.
    """
    models.Base.metadata.create_all(bind=database.engine)
    db = database.SessionLocal()
    try:
        now = datetime.now()
        logger.info(f"🧹 [SYSTEM] Sanacja bazy ({now.strftime('%Y-%m-%d %H:%M')}): Weryfikacja zaległych dostaw...")

        # FORCE DELIVERY ON STARTUP (STARTUP RECOVERY)
        stale_orders = db.query(models.Order).filter(
            models.Order.status == "ordered",
            models.Order.estimated_delivery < now
        ).all()
        
        delivered_count = 0
        for so in stale_orders:
            if so.product:
                so.product.current_stock += int(so.quantity)
                so.status = "delivered"
                delivered_count += 1
        
        # Anulowanie przeterminowanych blokad (jeśli nikt nie zaakceptował na czas)
        stale_pending = db.query(models.Order).filter(
            models.Order.status == "pending_approval",
            models.Order.estimated_delivery < now
        ).all()
        for sp in stale_pending:
            sp.status = "cancelled"
            
        db.commit()
        
        if delivered_count > 0:
            logger.info(f"🚚 [SYSTEM] Odebrano zaległe dostawy podczas startupu: {delivered_count}.")
        else:
            logger.info("✅ [SYSTEM] Brak zaległych dostaw przy starcie.")

        logger.info("🧠 [SYSTEM] Inicjalizacja modułów AI...")
        products = db.query(models.Product).all()
        if products: 
            ai_search.index_products(products)
        
        simulation_task = asyncio.create_task(simulator.run_simulation_loop())
        logger.info("✅ [SYSTEM] Startup zakończony. Symulator JIT aktywny.")
        
        yield 
        
        simulation_task.cancel()
        logger.info("🛑 [SYSTEM] Wyłączanie usług...")
    except Exception as e:
        logger.error(f"❌ [CRITICAL] Błąd startupu: {e}")
        db.rollback()
    finally:
        db.close()

app = FastAPI(
    title="Procurement Pro ERP - Intelligent Sourcing System",
    description="Zaawansowany system ERP z modułami AI i Digital Twin.",
    version="5.7.0",
    docs_url="/docs",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db() -> Generator[Session, None, None]:
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- ENDPOINTY: PRODUKTY ---
@app.get("/products", response_model=List[schemas.Product])
def read_products(
    skip: int = 0, 
    limit: int = 100, 
    search: Optional[str] = None, 
    category: Optional[str] = None, 
    db: Session = Depends(get_db)
) -> List[schemas.Product]:
    if search:
        ai_response = ai_search.search(query=search, target_category=category, top_k=limit)
        ai_matched_products = ai_response.get("results", [])
        product_ids = [p.id for p in ai_matched_products]
        
        if product_ids:
            db_products = db.query(models.Product).filter(models.Product.id.in_(product_ids)).all()
            raw_products = sorted(db_products, key=lambda x: product_ids.index(x.id))
        else:
            raw_products = []
    else:
        query = db.query(models.Product)
        if category: 
            query = query.filter(models.Product.category == category)
        raw_products = query.offset(skip).limit(limit).all()

    final_results = []
    for prod in raw_products:
        p_schema = schemas.Product.model_validate(prod)
        contracts = db.query(models.Contract).filter(
            and_(models.Contract.product_id == prod.id, models.Contract.is_active == True)
        ).all()
        p_schema.active_contracts = [
            schemas.ContractInfo(
                id=c.id, 
                supplier_name=c.supplier.name if c.supplier else "Nieznany", 
                price=c.price, 
                valid_until=c.end_date, 
                payment_terms_days=c.payment_terms_days
            ) for c in contracts
        ]
        final_results.append(p_schema)
    return final_results

# --- ENDPOINTY: ZAMÓWIENIA I DECYZJE ---
@app.post("/orders", response_model=schemas.Order)
def create_order(order_in: schemas.OrderCreate, db: Session = Depends(get_db)) -> schemas.Order:
    p = db.query(models.Product).filter(models.Product.id == order_in.product_id).first()
    if not p: 
        raise HTTPException(status_code=404, detail="Produkt nie istnieje")

    best_contract = db.query(models.Contract).filter(
        and_(models.Contract.product_id == p.id, models.Contract.is_active == True)
    ).order_by(models.Contract.price.asc()).first()
    
    final_price = best_contract.price if best_contract else p.unit_cost
    total_value = final_price * order_in.quantity

    start_time = time.perf_counter()
    is_anomaly = anomaly_detector.is_anomaly(
        float(order_in.quantity), 
        float(total_value), 
        float(best_contract.price) if best_contract else None
    )
    inference_time_ms = (time.perf_counter() - start_time) * 1000 
    
    raw_score = None
    if anomaly_detector.model and anomaly_detector.is_trained:
        up = total_value / order_in.quantity if order_in.quantity > 0 else 0.0
        cp = float(best_contract.price) if best_contract else 0.0
        price_dev = ((up - cp) / cp) if cp > 0 else 0.0
        features = [[float(order_in.quantity), float(total_value), up, price_dev]]
        raw_score = float(anomaly_detector.model.decision_function(features)[0])

    order_status = "pending_approval" if is_anomaly or total_value > 15000 else "ordered"

    current_op_date = simulator.effective_date

    new_order = models.Order(
        id=f"ORD-{uuid.uuid4().hex[:8].upper()}",
        product_id=p.id,
        supplier_id=best_contract.supplier_id if best_contract else order_in.supplier_id,
        quantity=order_in.quantity,
        total_price=total_value,
        status=order_status,
        created_at=current_op_date,
        estimated_delivery=current_op_date + timedelta(days=p.lead_time_days),
        payment_terms_days=best_contract.payment_terms_days if best_contract else 30,
        order_type="KOSZT/JIT",
        delay_days=0,
        is_anomaly=is_anomaly,
        anomaly_score=raw_score,
        pending_days=0
    )

    db.add(new_order)
    db.commit()
    db.refresh(new_order)
    
    response_order = schemas.Order.model_validate(new_order)
    
    try:
        threshold = getattr(anomaly_detector.model, 'contamination_', "Dynamic")
    except AttributeError:
        threshold = "Dynamic"
        
    response_order.ai_metadata = {
        "engine": "IsolationForest_v2.1",
        "inference_time_ms": round(inference_time_ms, 3),
        "is_flagged": is_anomaly,
        "security_threshold": threshold,
        "xai_audit_required": is_anomaly,
        "db_anomaly_score": round(raw_score, 4) if raw_score is not None else None
    }
    
    return response_order

@app.get("/orders", response_model=List[schemas.Order])
def read_orders(status: Optional[str] = None, db: Session = Depends(get_db)) -> List[models.Order]:
    query = db.query(models.Order).options(joinedload(models.Order.product), joinedload(models.Order.supplier))
    if status: 
        query = query.filter(models.Order.status == status)
    return query.order_by(desc(models.Order.created_at)).all()

@app.put("/orders/{order_id}/approve")
def approve_order(order_id: str, db: Session = Depends(get_db)) -> Dict[str, str]:
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order: 
        raise HTTPException(status_code=404)
    order.status = "ordered"
    order.pending_days = 0
    db.commit()
    return {"status": "success"}

@app.put("/orders/{order_id}/reject")
def reject_order(order_id: str, db: Session = Depends(get_db)) -> Dict[str, str]:
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order: 
        raise HTTPException(status_code=404)
    order.status = "cancelled"
    db.commit()
    return {"status": "success"}

@app.post("/system/ai/retrain")
async def trigger_ai_training(background_tasks: BackgroundTasks, db: Session = Depends(get_db)) -> Dict[str, str]:
    orders = db.query(models.Order).all()
    background_tasks.add_task(anomaly_detector.train, orders)
    return {
        "status": "processing",
        "message": f"Zlecono trening Isolation Forest na {len(orders)} próbkach w tle.",
        "architecture_note": "Wykorzystano FastAPI BackgroundTasks w celu optymalizacji Wymagań Niefunkcjonalnych (WNF)."
    }

@app.get("/analytics/dashboard")
def get_dashboard_data(db: Session = Depends(get_db)) -> Dict[str, Any]:
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
    
    for o in emergency_orders:
        prod = getattr(o, 'product', None)
        burn = max(prod.average_daily_consumption or 0.5, 0.5) if prod else 1.0
        lt = prod.lead_time_days if prod else 7
        
        interventions.append({
            "id": o.id,
            "date": o.created_at.strftime("%Y-%m-%d %H:%M") if o.created_at else "Brak",
            "type": "Ratunek (Emergency)",
            "product": prod.name if prod else "Nieznany",
            "impact": "Zapobiegnięto postojowi",
            "color": "blue",
            "val": o.total_price,
            "reason": f"DIAGNOSTYKA: Przerwanie pętli JIT. Zużycie: {burn:.2f}/d. LT: {lt} dni."
        })
        
    for o in blocked_orders:
        prod = getattr(o, 'product', None)
        interventions.append({
            "id": o.id,
            "date": o.created_at.strftime("%Y-%m-%d %H:%M") if o.created_at else "Brak",
            "type": "Blokada (Anomalia)",
            "product": prod.name if prod else "Nieznany",
            "impact": f"Zatrzymano {o.total_price:.0f} PLN",
            "color": "red",
            "val": o.total_price,
            "reason": "DIAGNOSTYKA: Wykryto błąd proceduralny (Isolation Forest)."
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
        "ai_interventions": interventions[:10],
        "emergency_count": len(emergency_orders),
        "emergency_premium_cost": round(emergency_premium, 2),
        "ai_negotiations": []
    }

# --- MRP & PREDICTIONS ---
@app.get("/analytics/predictions") 
def get_ai_predictions(limit: int = 100, db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    products = db.query(models.Product).all()
    results = []
    active_orders = db.query(models.Order).filter(
        models.Order.status.in_(["ordered", "pending_approval"])
    ).all()

    op_date = simulator.effective_date

    for p in products:
        burn_rate = max(p.average_daily_consumption or 0.5, 0.5)
        days_left = round(p.current_stock / burn_rate, 1)
        
        product_orders = [o for o in active_orders if o.product_id == p.id]
        incoming_qty = sum(o.quantity for o in product_orders)
        
        lead_time = p.lead_time_days or 7
        probabilistic_lead_time = max(float(lead_time), random.gauss(float(lead_time), 1.5))
        
        dynamic_safety_buffer = probabilistic_lead_time * 0.5  
        warning_threshold = lead_time + (probabilistic_lead_time - lead_time) + dynamic_safety_buffer
        emergency_threshold = max(1.5, lead_time * 0.3) 

        status = "safe"
        if days_left <= lead_time:
            status = "critical" if incoming_qty == 0 else "incoming"
        elif days_left <= warning_threshold:
            status = "warning"

        next_delivery = None
        delay_days = 0
        if product_orders:
            earliest_order = min(product_orders, key=lambda o: o.estimated_delivery if o.estimated_delivery else datetime.max)
            if earliest_order.estimated_delivery:
                next_delivery = earliest_order.estimated_delivery.strftime("%Y-%m-%d")
                delay_days = getattr(earliest_order, 'delay_days', 0)

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
            "delay_days": delay_days,
            "ai_supplier_advice": "Tryb Express" if days_left <= emergency_threshold else "Optymalny koszt"
        })
    
    results.sort(key=lambda x: x['days_left'] if isinstance(x['days_left'], float) else 9999)
    return results[:limit]

@app.get("/analytics/history")
def get_analytics_history(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    try: 
        stats = db.query(models.DailyStats).order_by(models.DailyStats.date).all()
        return [
            {
                "date": s.date.isoformat(),
                "total_inventory_value": float(s.total_inventory_value),
                "total_orders_count": int(s.total_orders_count)
            } for s in stats
        ]
    except Exception as e:
        logger.error(f"Error fetching history: {e}")
        return []

@app.get("/analytics/what-if")
def simulation_what_if(delay_days: int = 0, demand_spike: float = 0.0) -> List[Dict[str, Any]]:
    days = []
    base_stock = 100
    for i in range(1, 15):
        consumption = 8 * (1.0 + demand_spike/100)
        delivery = 50 if (i == 7 + delay_days) else 0
        stock_val = max(0, int(base_stock - (i * consumption) + delivery))
        baseline_val = max(0, int(base_stock - (i * 8) + (50 if i == 7 else 0)))
        days.append({"day": f"Dzień {i}", "stock": stock_val, "baseline": baseline_val})
    return days

# --- ULEPSZONY ENDPOINT PDF ---
@app.get("/orders/{order_id}/pdf")
async def download_order_pdf(order_id: str, db: Session = Depends(get_db)) -> FileResponse:
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order: 
        raise HTTPException(status_code=404)
    
    pdf_dir = "generated_orders"
    pdf_path = os.path.join(pdf_dir, f"Order_{order.id}.pdf")
    
    # Jeśli plik nie istnieje, wygeneruj go
    if not os.path.exists(pdf_path):
        try:
            generate_order_pdf(order, output_dir=pdf_dir)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Błąd generowania PDF: {e}")
    
    return FileResponse(pdf_path, media_type='application/pdf', filename=f"Zamowienie_{order.id}.pdf")

@app.post("/contracts/upload", response_model=schemas.ContractInfo)
async def upload_contract_ai(file: UploadFile = File(...), db: Session = Depends(get_db)) -> schemas.ContractInfo:
    temp_path = f"temp_{uuid.uuid4().hex}.pdf"
    with open(temp_path, "wb") as buffer: 
        shutil.copyfileobj(file.file, buffer)
    try:
        parsed = contract_parser.parse_pdf(temp_path)
        return schemas.ContractInfo(
            id=0, 
            supplier_name=parsed.get("supplier", "Nieznany"), 
            price=parsed.get("price", 0.0), 
            valid_until=parsed.get("valid_until")
        )
    finally:
        if os.path.exists(temp_path): 
            os.remove(temp_path)

@app.get("/simulation/status", response_model=schemas.SimulationStatus)
def get_sim_info() -> schemas.SimulationStatus:
    status = simulator.get_status()
    return schemas.SimulationStatus(
        current_date=status["current_date"], 
        is_running=status["is_running"], 
        events=status["events"]
    )

@app.post("/simulation/toggle")
async def control_sim() -> Dict[str, Any]:
    simulator.is_running = not simulator.is_running
    return {"status": "success", "current_state": "uruchomiona" if simulator.is_running else "zatrzymana"}

class UserMessage(BaseModel): 
    message: str

@app.post("/assistant/chat")
async def ai_assistant_endpoint(req: UserMessage, db: Session = Depends(get_db)) -> Dict[str, str]:
    query = req.message.lower()
    if any(k in query for k in ["braki", "popyt", "zapasy"]):
        return {"text": "Analizuję zapasy. Przy obecnym trendzie zapasy krytyczne wyczerpią się wkrótce. Zalecam audyt modułu Predictions."}
    return {"text": "System gotowy do analizy logistycznej. O co chcesz zapytać?"}
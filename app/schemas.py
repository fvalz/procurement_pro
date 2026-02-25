from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Any, Dict
from datetime import datetime

# --- MODELE POMOCNICZE (CONTRACT INFO) ---
class ContractInfo(BaseModel):
    id: int
    supplier_name: Optional[str] = "Nieznany dostawca"
    price: float
    valid_until: Optional[datetime] = None 
    payment_terms_days: int = 30

# --- DOSTAWCY (SUPPLIER) ---
class SupplierBase(BaseModel):
    name: str
    contact_email: Optional[str] = None
    reliability_score: Optional[float] = 1.0
    delivery_speed_rating: Optional[float] = 3.0

class SupplierCreate(SupplierBase):
    pass

class Supplier(SupplierBase):
    id: int
    
    model_config = ConfigDict(from_attributes=True)

# --- PRODUKTY (PRODUCT) ---
class ProductBase(BaseModel):
    name: str
    category: str
    unit_cost: float
    description: Optional[str] = None
    unit: Optional[str] = "szt."
    min_stock_level: Optional[int] = 0
    average_daily_consumption: Optional[float] = 0.0
    lead_time_days: Optional[int] = 7

class ProductCreate(ProductBase):
    current_stock: int = 0

class Product(ProductBase):
    id: int
    current_stock: int 
    supplier_id: Optional[int] = None
    supplier: Optional[Supplier] = None
    active_contracts: List[ContractInfo] = [] 
    
    model_config = ConfigDict(from_attributes=True)

# --- ZAMÓWIENIA (ORDER) ---
class OrderBase(BaseModel):
    product_id: int
    supplier_id: Optional[int] = None
    quantity: int
    total_price: float
    status: str = "pending"
    payment_terms_days: int = 30
    order_type: Optional[str] = "standard"
    delay_days: int = 0

class OrderCreate(OrderBase):
    pass

class Order(OrderBase):
    id: str 
    created_at: datetime
    order_type: Optional[str] = None
    estimated_delivery: Optional[datetime] = None
    product: Optional[Product] = None
    supplier: Optional[Supplier] = None
    
    # --- NOWE POLA ZGODNE Z MODELEM BAZODANOWYM (models.py) ---
    is_anomaly: bool = False
    anomaly_score: Optional[float] = None
    pending_days: Optional[int] = 0   # <-- DODANE
    
    # --- Metadane analityczne AI doczepiane "w locie" do odpowiedzi API ---
    ai_metadata: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="Statystyki i dane diagnostyczne modelu Machine Learning"
    )

    model_config = ConfigDict(from_attributes=True)

# --- KONTRAKTY (CONTRACT) ---
class ContractBase(BaseModel):
    product_id: int
    supplier_id: int
    price: float
    start_date: datetime
    end_date: Optional[datetime] = None
    payment_terms_days: int = 30
    is_active: bool = True

class ContractCreate(ContractBase):
    pass

class Contract(ContractBase):
    id: int
    supplier: Optional[Supplier] = None
    product: Optional[Product] = None

    model_config = ConfigDict(from_attributes=True)

# --- STATYSTYKI I ANALITYKA ---
class DailyStats(BaseModel):
    id: Optional[int] = None
    date: datetime
    total_inventory_value: float
    total_orders_count: int

    model_config = ConfigDict(from_attributes=True)

# --- CYFROWY BLIŹNIAK (SIMULATION) ---
class SimulationEvent(BaseModel):
    id: int
    date: str
    message: str
    type: str
    icon: str

class SimulationStatus(BaseModel):
    current_date: str
    is_running: bool
    events: List[SimulationEvent] = []

# --- MODELE PREDYKCJI (AI) ---
class Prediction(BaseModel):
    id: int
    product_name: str
    current_stock: int
    burn_rate: float
    days_left: Any # Może być float lub str ("Brak Danych")
    status: str 
    restock_recommended: bool
    negotiation_alert: bool = False
    potential_savings: float = 0.0
    incoming_stock: int = 0
    next_delivery_date: Optional[str] = None
    delay_days: int = 0
    ai_supplier_advice: Optional[str] = None

# --- MODELE INTERWENCJI (DLA DASHBOARDU) ---
class AIIntervention(BaseModel):
    id: str
    date: str
    type: str
    product: str
    impact: str
    color: str
    val: float
    reason: str 

class ChartDataPoint(BaseModel):
    name: str
    value: float
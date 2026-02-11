from pydantic import BaseModel, Field
from typing import List, Optional, Any
from datetime import datetime

# --- MODELE POMOCNICZE (CONTRACT INFO) ---
# Używane do wyświetlania skróconych informacji o kontraktach wewnątrz Produktu
class ContractInfo(BaseModel):
    id: int
    supplier_name: Optional[str] = "Nieznany dostawca"
    price: float
    # To pole mapujemy ręcznie w main.py z pola 'end_date' w bazie
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
    
    class Config:
        from_attributes = True

# --- PRODUKTY (PRODUCT) ---
class ProductBase(BaseModel):
    name: str
    category: str
    unit_cost: float
    
    # POLA OPCJONALNE (Zapobiegają błędom walidacji, gdy baza ma braki)
    description: Optional[str] = None
    unit: Optional[str] = "szt."
    min_stock_level: Optional[int] = 0
    
    # Dane symulacyjne
    average_daily_consumption: Optional[float] = 0.0
    lead_time_days: Optional[int] = 7

class ProductCreate(ProductBase):
    current_stock: int = 0

class Product(ProductBase):
    id: int
    current_stock: int # Używamy Integer zgodnie z ustaleniami
    
    # Relacje (opcjonalne)
    supplier_id: Optional[int] = None
    supplier: Optional[Supplier] = None

    # --- KLUCZOWE POLE (Naprawia ValueError w main.py) ---
    active_contracts: List[ContractInfo] = [] 
    
    class Config:
        from_attributes = True

# --- ZAMÓWIENIA (ORDER) ---
class OrderBase(BaseModel):
    product_id: int
    supplier_id: Optional[int] = None
    quantity: int
    total_price: float
    status: str = "pending"
    payment_terms_days: int = 30
    order_type: Optional[str] = "standard"

class OrderCreate(OrderBase):
    pass

class Order(OrderBase):
    id: str # String (np. "ORD-123")
    created_at: datetime
    order_type: Optional[str] = None
    
    # Daty mogą być puste w bazie
    estimated_delivery: Optional[datetime] = None
    
    # Relacje
    product: Optional[Product] = None
    supplier: Optional[Supplier] = None

    class Config:
        from_attributes = True

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

    class Config:
        from_attributes = True

# --- STATYSTYKI I ANALITYKA ---

class DailyStats(BaseModel):
    id: Optional[int] = None
    date: datetime
    total_inventory_value: float
    total_orders_count: int

    class Config:
        from_attributes = True

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
# Niezbędne dla endpointu /analytics/predictions
class Prediction(BaseModel):
    id: int
    product_name: str
    current_stock: int
    burn_rate: float
    days_left: float
    status: str # "ok", "warning", "critical"
    restock_recommended: bool
    negotiation_alert: bool = False
    potential_savings: float = 0.0
    
    # NOWE POLA DO BILANSOWANIA MRP
    incoming_stock: int = 0         # Ile sztuk jest już zamówionych (status 'ordered')
    next_delivery_date: Optional[str] = None # Kiedy spodziewamy się dostawy

# Model do wykresów (opcjonalny, jeśli używany)
class ChartDataPoint(BaseModel):
    name: str
    value: float
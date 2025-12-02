from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# --- MODELE POMOCNICZE ---
class ContractInfo(BaseModel):
    supplier_name: str
    price: float
    valid_until: datetime

# --- PRODUKTY ---
class ProductBase(BaseModel):
    name: str
    category: str
    unit: str
    current_stock: float
    min_stock_level: float
    lead_time_days: int = 7
    average_daily_consumption: float = 1.0 

class ProductCreate(ProductBase):
    pass

class Product(ProductBase):
    id: int
    active_contract: Optional[ContractInfo] = None
    class Config:
        from_attributes = True

class Supplier(BaseModel):
    id: int
    name: str
    category: str
    rating: float
    class Config:
        from_attributes = True

# --- ZAMÓWIENIA ---
class OrderCreate(BaseModel):
    product_id: int
    quantity: float
    supplier_id: Optional[int] = None 
    order_type: str = "standard" 

class Order(BaseModel):
    id: str
    product_id: int
    supplier_id: Optional[int]
    quantity: float
    total_price: float
    status: str
    created_at: datetime
    estimated_delivery: datetime
    product: Optional[Product] = None
    supplier: Optional[Supplier] = None
    class Config:
        from_attributes = True

# --- KONTRAKTY ---
class ContractDraft(BaseModel):
    supplier_name: str
    product_name: str
    price: float
    valid_until: datetime

# --- PREDYKCJA (NOWOŚĆ) ---
class Prediction(BaseModel):
    id: int
    product_name: str
    current_stock: float
    burn_rate: float      # Zużycie na dzień
    days_left: float      # Na ile dni starczy
    status: str           # "safe", "warning", "critical"
    restock_recommended: bool
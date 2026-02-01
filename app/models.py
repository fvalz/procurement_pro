from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class Supplier(Base):
    __tablename__ = "suppliers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    rating = Column(Float, default=0.0)
    category = Column(String)
    contracts = relationship("Contract", back_populates="supplier")
    orders = relationship("Order", back_populates="supplier")

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    category = Column(String, index=True)
    unit = Column(String, default="szt.")
    current_stock = Column(Float, default=0.0)
    min_stock_level = Column(Float, default=10.0)
    lead_time_days = Column(Integer, default=7)
    average_daily_consumption = Column(Float, default=1.0)
    unit_cost = Column(Float, default=50.0)
    contracts = relationship("Contract", back_populates="product")

class Contract(Base):
    __tablename__ = "contracts"
    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    price = Column(Float)
    valid_from = Column(DateTime, default=datetime.now)
    valid_until = Column(DateTime)
    is_active = Column(Boolean, default=True)
    penalty_clause_details = Column(Text, nullable=True)
    termination_period_days = Column(Integer, default=30)
    
    # NOWOŚĆ: Warunki płatności w kontrakcie (np. 30 dni)
    payment_terms_days = Column(Integer, default=30)

    supplier = relationship("Supplier", back_populates="contracts")
    product = relationship("Product", back_populates="contracts")

class Order(Base):
    __tablename__ = "orders"
    id = Column(String, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)
    quantity = Column(Float)
    total_price = Column(Float)
    status = Column(String, default="ordered")
    order_type = Column(String)
    created_at = Column(DateTime, default=datetime.now)
    estimated_delivery = Column(DateTime)
    
    # NOWOŚĆ: Kiedy trzeba zapłacić?
    payment_terms_days = Column(Integer, default=0) # 0 = płatność natychmiastowa
    payment_due_date = Column(DateTime)             # Wyliczona data płatności

    supplier = relationship("Supplier", back_populates="orders")
    product = relationship("Product")

class DailyStats(Base):
    __tablename__ = "daily_stats"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, index=True)
    total_items = Column(Integer)
    low_stock_count = Column(Integer)
    pending_orders = Column(Integer)
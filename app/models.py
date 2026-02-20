from sqlalchemy import Column, Integer, String, Float, ForeignKey, Boolean, DateTime, Date
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    full_name = Column(String)
    role = Column(String)  # "admin", "employee", "bot"

class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    contact_email = Column(String)
    reliability_score = Column(Float, default=1.0)
    delivery_speed_rating = Column(Float, default=3.0)

    products = relationship("Product", back_populates="supplier")
    contracts = relationship("Contract", back_populates="supplier")
    orders = relationship("Order", back_populates="supplier")

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    category = Column(String, index=True)
    unit_cost = Column(Float)
    current_stock = Column(Integer, default=0)
    description = Column(String, nullable=True)
    unit = Column(String, default="szt.") 
    
    # Dane do symulacji / AI - Brak sztywnego min_stock_level (podejście Dynamic ROP)
    average_daily_consumption = Column(Float, default=0.0)
    lead_time_days = Column(Integer, default=7)
    
    supplier_id = Column(Integer, ForeignKey("suppliers.id"))
    supplier = relationship("Supplier", back_populates="products")
    
    contracts = relationship("Contract", back_populates="product")
    orders = relationship("Order", back_populates="product")

class Contract(Base):
    __tablename__ = "contracts"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    supplier_id = Column(Integer, ForeignKey("suppliers.id"))
    
    price = Column(Float)
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime)
    payment_terms_days = Column(Integer, default=30)
    is_active = Column(Boolean, default=True)

    product = relationship("Product", back_populates="contracts")
    supplier = relationship("Supplier", back_populates="contracts")

class Order(Base):
    __tablename__ = "orders"

    id = Column(String, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    supplier_id = Column(Integer, ForeignKey("suppliers.id"))
    
    quantity = Column(Integer)
    total_price = Column(Float)
    status = Column(String, default="pending")  # pending, ordered, delivered, cancelled
    order_type = Column(String, nullable=True, default="KOSZT")

    created_at = Column(DateTime, default=datetime.utcnow)
    estimated_delivery = Column(DateTime, nullable=True)
    
    # Pole do obsługi wizualizacji opóźnień (+X dni)
    delay_days = Column(Integer, default=0) 
    
    payment_terms_days = Column(Integer, default=30)

    product = relationship("Product", back_populates="orders")
    supplier = relationship("Supplier", back_populates="orders")

class DailyStats(Base):
    __tablename__ = "daily_stats"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, index=True)
    total_inventory_value = Column(Float)
    total_orders_count = Column(Integer)
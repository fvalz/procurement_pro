from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# Lokalizacja bazy danych (SQLite)
SQLALCHEMY_DATABASE_URL = "sqlite:///./procurement.db"

# Tworzenie silnika bazy danych
# check_same_thread=False jest wymagane tylko dla SQLite
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# Fabryka sesji - pozwala na tworzenie nowych sesji bazy danych dla każdego żądania
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# NOWY STANDARD SQLALCHEMY 2.0: Definiujemy klasę bazową dla modeli
# Zamiast Base = declarative_base(), używamy dziedziczenia po DeclarativeBase
class Base(DeclarativeBase):
    """Klasa bazowa dla wszystkich modeli systemowych ORM."""
    pass

# Dependency (Wstrzykiwanie zależności) do używania w endpointach FastAPI
def get_db():
    """
    Generator dostarczający sesję bazy danych.
    Zamyka połączenie automatycznie po zakończeniu obsługi żądania HTTP.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
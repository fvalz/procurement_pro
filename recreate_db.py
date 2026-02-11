import os
import sys
import random

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

def reset_db():
    print("--- ROZPOCZĘTO PROCES REKREACJI BAZY DANYCH ---")
    
    try:
        from app.database import engine, SessionLocal
        from app import models
        import pandas as pd
    except ImportError as e:
        print(f"❌ BŁĄD: Nie można załadować modułów aplikacji: {e}")
        return

    db_name = "procurement.db"
    # Zamknięcie wszystkich połączeń silnika przed usunięciem pliku
    engine.dispose()

    if os.path.exists(db_name):
        try:
            os.remove(db_name)
            print(f"🗑️ Usunięto starą bazę danych: {db_name}")
        except Exception as e:
            print(f"❌ BŁĄD: Nie można usunąć bazy (może jest otwarta w innym programie?): {e}")
            return

    try:
        models.Base.metadata.create_all(bind=engine)
        print("🏗️ Utworzono nową strukturę tabel.")
    except Exception as e:
        print(f"❌ BŁĄD podczas tworzenia tabel: {e}")
        return

    db = SessionLocal()
    csv_path = os.path.join("data", "products_v2.csv")
    
    if not os.path.exists(csv_path):
        print(f"❌ BŁĄD: Brak pliku {csv_path}. Najpierw wygeneruj dane!")
        return

    try:
        print(f"📑 Importowanie danych produktów...")
        df = pd.read_csv(csv_path)
        
        for _, row in df.iterrows():
            new_product = models.Product(
                name=row['Product_Name'],
                description=row.get('Product_Description', ''),
                category=row['Category'],
                subcategory=row.get('Subcategory', ''),
                unit=row['Unit'],
                current_stock=float(random.randint(30, 100)), # Startujemy z bezpiecznym zapasem
                min_stock_level=float(row['Min_Stock_Level']),
                lead_time_days=int(row['Average_Lead_Time_Days']),
                unit_cost=float(row['Unit_Cost']),
                average_daily_consumption=random.uniform(1.0, 3.0)
            )
            db.add(new_product)
        
        print("🚚 Inicjalizacja dostawców strategicznych...")
        suppliers = [
            models.Supplier(name="IT Global Systems", rating=4.9, category="IT"),
            models.Supplier(name="Euro-Office Hub", rating=4.2, category="Office"),
            models.Supplier(name="Industrial Parts Pro", rating=4.6, category="Production"),
            models.Supplier(name="SafeWork Solutions", rating=4.8, category="BHP")
        ]
        db.add_all(suppliers)
        
        db.commit()
        print(f"🚀 SUKCES: Baza gotowa. Zaimportowano {len(df)} produktów.")
        
    except Exception as e:
        db.rollback()
        print(f"❌ BŁĄD podczas zasilania bazy: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    reset_db()
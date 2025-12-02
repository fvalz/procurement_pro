import pandas as pd
import os
from app.database import SessionLocal, engine, Base
from app.models import Product, Supplier, Contract
from datetime import datetime, timedelta
from sqlalchemy import text

# --- KONFIGURACJA ŚCIEŻKI ---
DATA_DIR = r"C:\Users\Damian\inzynierka\procurement_mvp\data"

def migrate():
    print("🚀 Rozpoczynam migrację danych...")
    print(f"📂 Katalog danych: {DATA_DIR}")
    
    # 0. CLEAN SLATE
    print("🧹 Czyszczenie starej bazy danych...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("✨ Utworzono puste tabele.")

    db = SessionLocal()

    if not os.path.exists(DATA_DIR):
        print(f"❌ BŁĄD KRYTYCZNY: Nie znaleziono katalogu: {DATA_DIR}")
        return

    # --- 1. MIGRACJA DOSTAWCÓW (POPRAWIONA) ---
    try:
        file_path = os.path.join(DATA_DIR, 'suppliers.csv')
        if os.path.exists(file_path):
            suppliers_df = pd.read_csv(file_path)
            
            # === FIX: USUWANIE DUPLIKATÓW Z CSV ===
            # To naprawi błąd "UNIQUE constraint failed"
            initial_count = len(suppliers_df)
            suppliers_df = suppliers_df.drop_duplicates(subset=['Supplier_Name'])
            if len(suppliers_df) < initial_count:
                print(f"ℹ️ Znaleziono i usunięto {initial_count - len(suppliers_df)} duplikatów w pliku suppliers.csv")

            count = 0
            for _, row in suppliers_df.iterrows():
                sup = Supplier(
                    name=row['Supplier_Name'],
                    category=row['Category'],
                    rating=row.get('Rating', 4.5)
                )
                db.add(sup)
                count += 1
            db.commit()
            print(f"✅ Dostawcy zaimportowani (dodano: {count}).")
        else:
            print(f"⚠️ Brak pliku suppliers.csv")
    except Exception as e:
        db.rollback()
        print(f"⚠️ Błąd importu dostawców: {e}")

    # --- 2. MIGRACJA PRODUKTÓW I INVENTORY ---
    try:
        inv_path = os.path.join(DATA_DIR, 'inventory.csv')
        prod_path = os.path.join(DATA_DIR, 'products.csv')
        
        if os.path.exists(inv_path) and os.path.exists(prod_path):
            inventory_df = pd.read_csv(inv_path)
            products_df = pd.read_csv(prod_path)
            
            prod_info = {}
            for _, row in products_df.iterrows():
                prod_info[row['Product_ID']] = row

            count = 0
            added_products = set()

            for _, row in inventory_df.iterrows():
                p_id = row['Product_ID']
                p_name = row.get('Product_Name', 'Unknown Product')
                
                if p_id in prod_info:
                    p_name = prod_info[p_id]['Product_Name']
                    p_cat = prod_info[p_id]['Category']
                else:
                    p_cat = "Unknown"

                if p_name in added_products:
                    continue

                prod = Product(
                    name=p_name,
                    category=p_cat,
                    current_stock=float(row['Stock']),
                    min_stock_level=float(row['Min_stock_level']),
                    unit=str(row['Unit'])
                )
                db.add(prod)
                added_products.add(p_name)
                count += 1
                
            db.commit()
            print(f"✅ Produkty i stany magazynowe zaimportowane (dodano: {count}).")
        else:
            print("⚠️ Brak plików inventory.csv lub products.csv")
    except Exception as e:
        db.rollback()
        print(f"⚠️ Błąd importu produktów: {e}")

    # --- 3. GENEROWANIE KONTRAKTÓW ---
    try:
        suppliers = db.query(Supplier).all()
        products = db.query(Product).all()
        
        count = 0
        if suppliers and products:
            for sup in suppliers:
                matching_products = [p for p in products if p.category == sup.category]
                
                for prod in matching_products:
                    contract = Contract(
                        supplier_id=sup.id,
                        product_id=prod.id,
                        price=100.0, 
                        valid_until=datetime.now() + timedelta(days=365),
                        is_active=True
                    )
                    db.add(contract)
                    count += 1
            
            db.commit()
            print(f"✅ Wygenerowano {count} aktywnych umów.")
        else:
            print("⚠️ Nie wygenerowano umów (brak dostawców lub produktów w bazie).")
        
    except Exception as e:
        db.rollback()
        print(f"⚠️ Błąd generowania kontraktów: {e}")

    db.close()
    print("🎉 Migracja zakończona sukcesem!")

if __name__ == "__main__":
    migrate()
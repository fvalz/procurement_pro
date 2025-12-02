from app.database import SessionLocal
from app.models import Contract
from sqlalchemy import text

def clear_contracts():
    db = SessionLocal()
    try:
        print("🧹 Usuwanie wszystkich istniejących kontraktów...")
        
        # Usuwamy wszystkie rekordy z tabeli contracts
        num_deleted = db.query(Contract).delete()
        db.commit()
        
        print(f"✅ Usunięto {num_deleted} umów.")
        print("Teraz system jest 'czysty'. Wszystkie produkty będą 'Spot' (Giełdowe),")
        print("dopóki nie wgrasz umowy PDF w zakładce Smart Wallet.")
        
    except Exception as e:
        print(f"❌ Błąd: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    clear_contracts()
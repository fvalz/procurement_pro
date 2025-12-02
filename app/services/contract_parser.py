import fitz  # PyMuPDF
import re
from datetime import datetime, timedelta
from app import schemas

class ContractParserService:
    def parse_pdf(self, file_content: bytes) -> schemas.ContractDraft:
        """Analizuje treść PDF i zwraca wyciągnięte dane"""
        
        # 1. Otwórz PDF z bajtów
        doc = fitz.open(stream=file_content, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
            
        # Logowanie dla debugowania (widoczne w konsoli)
        print("📄 [PDF] Analiza tekstu...")
        
        extracted_data = {
            "supplier_name": "Nieznany Dostawca",
            "product_name": "Nieznany Produkt",
            "price": 0.0,
            "valid_until": None
        }

        # --- POPRAWIONA LOGIKA EKSTRAKCJI (REGEX) ---
        
        # 1. SZUKANIE DOSTAWCY
        # Szukamy linii: "Dostawca: Nazwa Firmy"
        supplier_match = re.search(r"Dostawca:\s*(.+)", text)
        if supplier_match:
            extracted_data["supplier_name"] = supplier_match.group(1).strip()

        # 2. SZUKANIE PRODUKTU (FIX!)
        # Szukamy linii: "Produkt: Nazwa Produktu"
        # Wcześniej tego brakowało, dlatego miałeś "Nieznany Produkt"
        product_match = re.search(r"Produkt:\s*(.+)", text)
        if product_match:
            extracted_data["product_name"] = product_match.group(1).strip()

        # 3. SZUKANIE CENY
        # Szukamy wzorca liczbowego przed "PLN" lub "zł"
        price_match = re.search(r"(\d+[.,]\d{2})\s*(?:PLN|zł)", text)
        if price_match:
            # Zamiana przecinka na kropkę dla float
            price_str = price_match.group(1).replace(',', '.')
            extracted_data["price"] = float(price_str)

        # 4. SZUKANIE DATY I USTALANIE WAŻNOŚCI
        # W dokumencie masz "Data: YYYY-MM-DD" (data zamówienia)
        # Inteligentny kontrakt powinien być ważny np. ROK od tej daty
        date_match = re.search(r"Data:\s*(\d{4}-\d{2}-\d{2})", text)
        if date_match:
            try:
                doc_date = datetime.strptime(date_match.group(1), "%Y-%m-%d")
                # Ustawiamy ważność umowy na rok do przodu od daty dokumentu
                extracted_data["valid_until"] = doc_date.replace(year=doc_date.year + 1)
            except:
                pass
        
        # Zabezpieczenie: Jeśli nie znaleziono daty, ustaw rok od dzisiaj
        if not extracted_data["valid_until"]:
            extracted_data["valid_until"] = datetime.now().replace(year=datetime.now().year + 1)

        print(f"✅ [PDF SUCCESS] Zinterpretowano: {extracted_data['product_name']} od {extracted_data['supplier_name']}")
        return extracted_data

contract_parser = ContractParserService()
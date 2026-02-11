import pandas as pd
import random
import os

def generate_data():
    print("--- GENEROWANIE TECHNICZNEJ BAZY PRODUKTÓW ---")
    
    if not os.path.exists("data"):
        os.makedirs("data")

    # Dane do generowania unikalnych opisów
    tech_data = {
        "Laptopy": {
            "features": ["matryca IPS z powłoką antyrefleksyjną", "moduł TPM 2.0", "podświetlana klawiatura odporna na zachlapanie", "złącze Thunderbolt 4"],
            "usage": "Zoptymalizowany pod kątem wielozadaniowości i bezpiecznej pracy w środowisku korporacyjnym.",
            "cert": ["MIL-STD 810H", "Energy Star", "TCO Certified"]
        },
        "Silniki": {
            "features": ["wysoka sprawność IE3", "izolacja klasy F", "stopień ochrony IP55", "łożyska o wydłużonej żywotności"],
            "usage": "Przeznaczony do pracy ciągłej S1 w układach napędowych i wentylacyjnych.",
            "cert": ["Zgodność z normą IEC 60034", "Certyfikat CE"]
        },
        "Czujniki": {
            "features": ["wyjście PNP/NPN", "częstotliwość przełączania do 2kHz", "złącze M12 4-pin", "odporność na zakłócenia EMC"],
            "usage": "Idealny do precyzyjnej detekcji obiektów w szybkich liniach pakujących i montażowych.",
            "cert": ["Stopień ochrony IP67", "Certyfikat UL"]
        },
        "Papier": {
            "features": ["technologia ColorLok", "wysoki stopień białości CIE 160", "bezkwasowy skład", "minimalne pylenie"],
            "usage": "Zapewnia doskonały kontrast i ostrość wydruku w wysokonakładowych systemach laserowych.",
            "cert": ["Certyfikat FSC", "ISO 9706"]
        }
    }

    categories = {
        "IT": ["Laptopy", "Monitory", "Drukarki", "Oprogramowanie"],
        "Office": ["Papier", "Artykuły biurowe", "Meble", "Toners"],
        "Production": ["Narzędzia", "Czujniki", "Silniki", "Łożyska"],
        "BHP": ["Okulary ochronne", "Rękawice", "Kaski", "Odzież robocza"]
    }

    brands = {
        "IT": ["Dell", "HP", "Lenovo", "Samsung"],
        "Office": ["Navigator", "Xerox", "Nowy Styl", "Brother"],
        "Production": ["Bosch", "Siemens", "SICK", "SKF", "ABB"],
        "BHP": ["Uvex", "3M", "Ansell", "Honeywell"]
    }

    def get_technical_description(sub):
        data = tech_data.get(sub, {
            "features": ["wysoka jakość wykonania", "trwałość materiałowa", "ergonomiczny kształt"],
            "usage": "Uniwersalne rozwiązanie wspierające bieżące procesy operacyjne w przedsiębiorstwie.",
            "cert": ["Zgodność z normami UE"]
        })
        
        # Losowanie elementów opisu, aby każdy był inny
        feature = random.choice(data["features"])
        usage = data["usage"]
        cert = random.choice(data["cert"])
        
        return f"{usage} Kluczowe cechy: {feature}. Standard: {cert}."

    def get_real_name(cat, sub):
        brand = random.choice(brands[cat])
        if sub == "Laptopy":
            return f"Laptop {brand} {random.choice(['Latitude', 'ThinkPad'])} {random.choice(['i5/16GB', 'i7/32GB'])}"
        if sub == "Silniki":
            return f"Silnik {brand} {random.randint(1, 11)}kW {random.choice(['AC', 'DC'])}"
        return f"{sub[:-1] if sub.endswith('y') else sub} {brand} Professional Series"

    data = []
    for i in range(1, 151):
        cat = random.choice(list(categories.keys()))
        sub = random.choice(categories[cat])
        name = get_real_name(cat, sub)
        description = get_technical_description(sub)
        
        cost = random.uniform(800, 9000) if cat == "IT" else random.uniform(20, 1500)

        data.append({
            "Product_ID": f"P-{i:04d}",
            "Product_Name": name,
            "Product_Description": description,
            "Category": cat,
            "Subcategory": sub,
            "Unit": "szt.",
            "Min_Stock_Level": random.randint(5, 15),
            "Average_Lead_Time_Days": random.randint(2, 8),
            "Unit_Cost": round(cost, 2),
            "Currency": "PLN"
        })
    
    df = pd.DataFrame(data)
    df.to_csv("data/products_v2.csv", index=False)
    print(f"✅ SUKCES: Wygenerowano {len(df)} profesjonalnych produktów w 'data/products_v2.csv'.")

if __name__ == "__main__":
    generate_data()
import numpy as np
import logging
import os
import joblib
from sklearn.ensemble import IsolationForest
from app import models
from typing import Optional

# Konfiguracja logowania
logger = logging.getLogger(__name__)

# Stałe konfiguracyjne
MODEL_PATH = "anomaly_model.pkl"
MIN_SAMPLES_FOR_TRAINING = 10
ANOMALY_CONTAMINATION = 0.05 

class AnomalyDetector:
    """
    Serwis realizujący audyt bezpieczeństwa procesów zakupowych przy użyciu Isolation Forest.
    """

    def __init__(self):
        self.model = IsolationForest(
            contamination=ANOMALY_CONTAMINATION,
            random_state=42,
            n_jobs=-1
        )
        self.is_trained = False
        self._load_model_if_exists()

    def _load_model_if_exists(self):
        """Ładowanie modelu z dysku."""
        if os.path.exists(MODEL_PATH):
            try:
                self.model = joblib.load(MODEL_PATH)
                self.is_trained = True
                logger.info(f"✅ [AI SECURITY] Model detekcji załadowany.")
            except Exception as e:
                logger.error(f"❌ [AI SECURITY] Błąd ładowania: {e}")
        else:
            logger.warning("⚠️ [AI SECURITY] Brak modelu. Wymagany trening.")

    def train(self, orders: list[models.Order]):
        """
        Trenuje model na danych historycznych.
        Cechy: [Ilość, Cena Całkowita, Cena Jednostkowa]
        """
        if not orders or len(orders) < MIN_SAMPLES_FOR_TRAINING:
            logger.warning(f"⚠️ [AI SECURITY] Za mało danych ({len(orders)}).")
            return

        try:
            data = []
            for o in orders:
                # Obliczanie ceny jednostkowej jako kluczowej cechy
                unit_price = float(o.total_price / o.quantity) if o.quantity and o.quantity > 0 else 0.0
                data.append([float(o.quantity), float(o.total_price), unit_price])
            
            X = np.array(data)

            logger.info(f"🔄 [AI SECURITY] Trening na {len(X)} próbkach...")
            self.model.fit(X)
            self.is_trained = True

            joblib.dump(self.model, MODEL_PATH)
            logger.info(f"✅ [AI SECURITY] Trening zakończony.")

        except Exception as e:
            logger.error(f"❌ [AI SECURITY] Błąd treningu: {e}")

    def is_anomaly(self, quantity: float, total_price: float, contract_price: Optional[float] = None) -> bool:
        """
        Weryfikacja zamówienia. 
        UWAGA: Argumenty muszą być przekazywane zgodnie z sygnaturą w main.py.
        """
        try:
            # 1. Konwersja na float, aby uniknąć błędów typów
            q = float(quantity)
            tp = float(total_price)
            up = q / tp if q > 0 else 0.0

            # 2. Walidacja Kontraktowa (Deterministyczna)
            if contract_price is not None:
                cp = float(contract_price)
                if up > (cp * 1.15):
                    logger.warning(f"🚨 [AI SECURITY] PRZEPŁACENIE: {up:.2f} vs Kontrakt: {cp:.2f}")
                    return True

            # 3. Analiza Statystyczna (Isolation Forest)
            if not self.is_trained:
                return False

            # Przygotowanie danych (reshape(-1, 3) gwarantuje poprawny format macierzy)
            features = np.array([[q, tp, up]]).reshape(1, -1)
            
            prediction = self.model.predict(features)
            
            if prediction[0] == -1:
                score = self.model.decision_function(features)[0]
                logger.warning(f"🚨 [AI SECURITY] ANOMALIA STATYSTYCZNA! Score: {score:.4f}")
                return True
            
            return False

        except Exception as e:
            logger.error(f"❌ [AI SECURITY] Błąd inferencji: {e}")
            return False

# Singleton
anomaly_detector = AnomalyDetector()
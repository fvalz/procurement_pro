import numpy as np
import logging
import os
import joblib
from sklearn.ensemble import IsolationForest
from app import models

# Konfiguracja logowania - kluczowa dla śledzenia decyzji AI w systemach Enterprise
logger = logging.getLogger(__name__)

# Stałe konfiguracyjne algorytmu
MODEL_PATH = "anomaly_model.pkl"
MIN_SAMPLES_FOR_TRAINING = 10
ANOMALY_CONTAMINATION = 0.05  # Oczekiwany % anomalii w danych (5%)

class AnomalyDetector:
    """
    Serwis odpowiedzialny za wykrywanie anomalii w zamówieniach przy użyciu
    uczenia nienadzorowanego (Unsupervised Learning).
    
    Wykorzystuje algorytm Isolation Forest (Liu et al., 2008) do identyfikacji
    odchyleń (outliers) w wielowymiarowej przestrzeni cech [Ilość, Cena].
    """

    def __init__(self):
        self.model = IsolationForest(
            contamination=ANOMALY_CONTAMINATION,
            random_state=42,  # Zapewnia powtarzalność wyników (dobre do testów)
            n_jobs=-1         # Wykorzystuje wszystkie rdzenie procesora
        )
        self.is_trained = False
        self._load_model_if_exists()

    def _load_model_if_exists(self):
        """Próba załadowania wcześniej wytrenowanego modelu z dysku."""
        if os.path.exists(MODEL_PATH):
            try:
                self.model = joblib.load(MODEL_PATH)
                self.is_trained = True
                logger.info(f"✅ [AI SECURITY] Załadowano wytrenowany model z: {MODEL_PATH}")
            except Exception as e:
                logger.error(f"❌ [AI SECURITY] Błąd ładowania modelu: {e}")
        else:
            logger.warning("⚠️ [AI SECURITY] Brak zapisanego modelu. System wymaga treningu.")

    def train(self, orders: list[models.Order]):
        """
        Trenuje model na podstawie historycznych danych zamówień.
        
        Args:
            orders: Lista obiektów zamówień z bazy danych.
        """
        if not orders or len(orders) < MIN_SAMPLES_FOR_TRAINING:
            logger.warning(f"⚠️ [AI SECURITY] Zbyt mało danych do treningu ({len(orders)}). Wymagane: {MIN_SAMPLES_FOR_TRAINING}")
            return

        try:
            # Feature Engineering: Wyciąganie cech numerycznych [Ilość, Cena całkowita]
            # W przyszłości można dodać: [Godzina zamówienia, ID Dostawcy]
            data = np.array([[o.quantity, o.total_price] for o in orders])

            logger.info(f"🔄 [AI SECURITY] Rozpoczynanie treningu na {len(data)} próbkach...")
            
            self.model.fit(data)
            self.is_trained = True

            # Persystencja: Zapis modelu na dysk
            joblib.dump(self.model, MODEL_PATH)
            logger.info(f"✅ [AI SECURITY] Model wytrenowany i zapisany w {MODEL_PATH}")

        except Exception as e:
            logger.error(f"❌ [AI SECURITY] Krytyczny błąd podczas treningu: {e}")

    def is_anomaly(self, quantity: float, total_price: float) -> bool:
        """
        Dokonuje inferencji (predykcji) dla nowego zamówienia.
        
        Returns:
            bool: True jeśli wykryto anomalię (próba oszustwa/błąd), False jeśli norma.
        """
        if not self.is_trained:
            logger.warning("⚠️ [AI SECURITY] Próba detekcji na niewytrenowanym modelu. Przepuszczam transakcję.")
            return False

        try:
            # Formatowanie danych wejściowych do postaci macierzy 2D (wymóg Scikit-learn)
            features = np.array([[quantity, total_price]])
            
            # Predykcja: 1 = inlier (norma), -1 = outlier (anomalia)
            prediction = self.model.predict(features)
            score = self.model.decision_function(features)[0] # Wynik liczbowy (dla celów analitycznych)

            if prediction[0] == -1:
                logger.warning(f"🚨 [AI SECURITY] WYKRYTO ANOMALIĘ! Ilość: {quantity}, Cena: {total_price}, Score: {score:.4f}")
                return True
            
            logger.info(f"ok [AI SECURITY] Transakcja w normie. Score: {score:.4f}")
            return False

        except Exception as e:
            logger.error(f"❌ [AI SECURITY] Błąd podczas predykcji: {e}")
            return False # Fail-open: W razie błędu kodu nie blokuj biznesu

# Singleton - jedna instancja detektora na całą aplikację
anomaly_detector = AnomalyDetector()
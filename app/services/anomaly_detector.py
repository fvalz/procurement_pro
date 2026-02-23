import numpy as np
import logging
import os
import joblib
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import RobustScaler
from typing import Optional, List, Dict, Any
from app import models

# Konfiguracja logowania
logger = logging.getLogger(__name__)

# Stałe konfiguracyjne
MODEL_PATH = "anomaly_model.pkl"
MIN_SAMPLES_FOR_TRAINING = 10

class AnomalyDetector:
    """
    Zaawansowany detektor anomalii zakupowych.
    Wykorzystuje Isolation Forest wspierany przez RobustScaler oraz mechanizmy XAI.
    """

    def __init__(self) -> None:
        self.model: Optional[IsolationForest] = None
        self.scaler: Optional[RobustScaler] = None
        self.is_trained: bool = False
        
        # Nazwy cech do celów XAI
        self.feature_names: List[str] = [
            "Ilość", 
            "Cena Całkowita", 
            "Cena Jednostkowa", 
            "Odchylenie od Kontraktu"
        ]
        
        # Statystyki do wyliczania Z-score (wyjaśnialność modelu)
        self.training_stats: Dict[int, Dict[str, float]] = {}
        
        self._load_model_if_exists()

    def _load_model_if_exists(self) -> None:
        """Wczytuje model, scaler oraz statystyki z dysku."""
        if os.path.exists(MODEL_PATH):
            try:
                data = joblib.load(MODEL_PATH)
                if isinstance(data, dict) and "model" in data:
                    self.model = data.get("model")
                    self.scaler = data.get("scaler")
                    self.training_stats = data.get("stats", {})
                    self.is_trained = True
                    logger.info("✅ [AI SECURITY] Model i Scaler zostały załadowane.")
                else:
                    logger.warning("⚠️ [AI SECURITY] Niekompatybilny format modelu. Wymagany retrain.")
            except Exception as e:
                logger.error(f"❌ [AI SECURITY] Błąd wczytywania modelu: {e}")

    def train(self, orders: list[models.Order]) -> None:
        """
        Uczy model na podstawie 'czystych' danych historycznych.
        """
        # POPRAWKA: Używamy is_anomaly zamiast nieistniejącego pola notes
        valid_orders = [o for o in orders if not o.is_anomaly]

        if len(valid_orders) < MIN_SAMPLES_FOR_TRAINING:
            logger.warning(f"⚠️ [AI SECURITY] Za mało czystych danych do treningu ({len(valid_orders)}).")
            return

        try:
            data = []
            for o in valid_orders:
                q = float(o.quantity) if o.quantity else 0.0
                tp = float(o.total_price) if o.total_price else 0.0
                up = tp / q if q > 0 else 0.0
                
                # POPRAWKA: Pobieranie ceny kontraktowej przez relację Product -> Contracts
                cp = 0.0
                if o.product and o.product.contracts:
                    active_contract = next((c for c in o.product.contracts if c.is_active), None)
                    if active_contract:
                        cp = float(active_contract.price)
                
                price_dev = ((up - cp) / cp) if cp > 0 else 0.0
                data.append([q, tp, up, price_dev])
            
            X = np.array(data)

            # SKALOWANIE: RobustScaler jest odporny na wartości odstające
            self.scaler = RobustScaler()
            X_scaled = self.scaler.fit_transform(X)

            # Wyliczanie statystyk dla modułu XAI
            self.training_stats = {}
            for i in range(X.shape[1]):
                self.training_stats[i] = {
                    "mean": float(np.mean(X[:, i])),
                    "std": float(np.std(X[:, i]))
                }

            # MODEL: Zwiększona liczba drzew dla lepszej stabilności
            self.model = IsolationForest(
                contamination=0.05,
                random_state=42,
                n_estimators=200,
                n_jobs=-1
            )
            
            self.model.fit(X_scaled)
            self.is_trained = True

            # Zapis pełnego stanu
            joblib.dump({
                "model": self.model, 
                "scaler": self.scaler, 
                "stats": self.training_stats
            }, MODEL_PATH)
            
            logger.info(f"✅ [AI SECURITY] Trening zakończony na {len(valid_orders)} rekordach.")

        except Exception as e:
            logger.error(f"❌ [AI SECURITY] Błąd w fazie uczenia: {e}")

    def is_anomaly(self, quantity: float, total_price: float, contract_price: Optional[float] = None) -> bool:
        """
        Ocenia czy transakcja jest anomalią przy użyciu AI i reguł biznesowych.
        """
        try:
            q, tp = float(quantity), float(total_price)
            cp = float(contract_price) if contract_price is not None else 0.0
            up = tp / q if q > 0 else 0.0
            price_dev = ((up - cp) / cp) if cp > 0 else 0.0

            # 1. Twarda reguła biznesowa (Safety Net)
            if cp > 0 and up > (cp * 1.20):
                logger.warning(f"🚨 [AI SECURITY] ODRZUCONO: Cena {up:.2f} przekracza limit kontraktu o >20%.")
                return True

            # 2. Analiza AI
            if not self.is_trained or self.model is None or self.scaler is None:
                return False

            features = np.array([[q, tp, up, price_dev]])
            features_scaled = self.scaler.transform(features)
            
            prediction = self.model.predict(features_scaled)
            score = self.model.decision_function(features_scaled)[0]

            if prediction[0] == -1 or score < -0.05:
                xai_reason = self._get_feature_importance(features)
                logger.warning(f"🚨 [AI SECURITY] Anomalia wykryta (Score: {score:.3f})! Powód: {xai_reason}")
                return True
            
            return False

        except Exception as e:
            logger.error(f"❌ [AI SECURITY] Błąd podczas inferencji: {e}")
            return False

    def _get_feature_importance(self, features: np.ndarray) -> str:
        if not self.training_stats:
            return "Wykryto nietypowy wzorzec danych (brak statystyk XAI)."

        deviations = []
        for i, val in enumerate(features[0]):
            mean = self.training_stats[i]["mean"]
            std = self.training_stats[i]["std"]
            z_score = abs(val - mean) / (std if std > 0 else 1e-5)
            deviations.append(z_score)

        total_dev = sum(deviations)
        if total_dev == 0: return "Minimalne odchylenie od normy."

        explanation = []
        for i, z_val in enumerate(deviations):
            impact = (z_val / total_dev) * 100
            if impact > 20.0:
                explanation.append(f"{self.feature_names[i]} (odchylenie {z_val:.1f}σ)")

        return "Główne czynniki: " + ", ".join(explanation)

anomaly_detector = AnomalyDetector()
import numpy as np
import logging
import os
import joblib
from sklearn.ensemble import IsolationForest
from typing import Optional, List, Dict, Any
from app import models

# Konfiguracja logowania
logger = logging.getLogger(__name__)

# Stałe konfiguracyjne
MODEL_PATH = "anomaly_model.pkl"
MIN_SAMPLES_FOR_TRAINING = 10

class AnomalyDetector:
    """
    Inteligentny Strażnik Budżetu (Anomaly Detector).
    Realizuje audyt bezpieczeństwa procesów zakupowych przy użyciu Isolation Forest.
    Rozbudowany o dynamiczną estymację progu odcięcia, Feature Engineering
    oraz moduł XAI (Explainable AI) do analitycznego uzasadniania blokad.
    """

    def __init__(self) -> None:
        self.model: Optional[IsolationForest] = None
        self.is_trained: bool = False
        
        # Nazwy cech (Feature Names) do celów modułu wyjaśnialności XAI
        self.feature_names: List[str] = [
            "Ilość", 
            "Cena Całkowita", 
            "Cena Jednostkowa", 
            "Odchylenie od Kontraktu"
        ]
        # Statystyki historyczne do wyliczania Z-score (średnia i odchylenie std)
        self.training_stats: Dict[int, Dict[str, float]] = {}
        
        self._load_model_if_exists()

    def _load_model_if_exists(self) -> None:
        """Pobiera model oraz historyczne wagi statystyczne z dysku."""
        if os.path.exists(MODEL_PATH):
            try:
                data = joblib.load(MODEL_PATH)
                # Zabezpieczenie na wypadek starej wersji pliku .pkl (bez słownika XAI)
                if isinstance(data, dict) and "model" in data:
                    self.model = data.get("model")
                    self.training_stats = data.get("stats", {})
                else:
                    self.model = data
                    self.training_stats = {}
                    
                self.is_trained = True
                logger.info("✅ [AI SECURITY] Model detekcji oraz macierz XAI załadowane.")
            except Exception as e:
                logger.error(f"❌ [AI SECURITY] Błąd wczytywania modelu: {e}")
        else:
            logger.warning("⚠️ [AI SECURITY] Brak modelu na dysku. Wymagany trening wektora.")

    def _calculate_dynamic_contamination(self, X: np.ndarray) -> float:
        """
        Dynamicznie wylicza współczynnik zanieczyszczenia (contamination)
        bazując na analizie wariancji (reguła trzech sigm dla ceny jednostkowej).
        """
        unit_prices = X[:, 2]
        mean_up = np.mean(unit_prices)
        std_up = np.std(unit_prices)
        
        if std_up == 0:
            return 0.01 
            
        # Wyodrębnienie transakcji wykraczających poza 3 odchylenia standardowe
        outliers_count = np.sum(np.abs(unit_prices - mean_up) > 3 * std_up)
        contamination = float(outliers_count / len(X))
        
        # Hard-clipping progu do bezpiecznego przedziału [0.01, 0.1]
        return float(np.clip(contamination, 0.01, 0.1))

    def _get_feature_importance(self, features: np.ndarray) -> str:
        """
        Mechanizm Explainable AI (XAI).
        Normalizuje odchylenia (Z-score) i zwraca tekstowe uzasadnienie flagowania.
        """
        if not self.training_stats:
            return "Brak danych historycznych do analizy wielowymiarowej."

        deviations = []
        for i, val in enumerate(features[0]):
            if i not in self.training_stats:
                deviations.append(0.0)
                continue
                
            mean = self.training_stats[i]["mean"]
            std = self.training_stats[i]["std"]
            
            # Ewaluacja Z-score z zabezpieczeniem dzielenia przez zero (epsilon)
            z_score = abs(val - mean) / (std if std > 0 else 1e-5)
            deviations.append(z_score)

        total_dev = sum(deviations)
        if total_dev == 0:
            return "Odchylenia są statystycznie nieistotne."

        explanation = []
        for i, z_val in enumerate(deviations):
            impact_percent = (z_val / total_dev) * 100
            # Redukcja szumu: logujemy tylko cechy o decydującym znaczeniu (>15%)
            if impact_percent > 15.0:  
                explanation.append(
                    f"{self.feature_names[i]} ma {impact_percent:.0f}% wpływu "
                    f"(odchylenie: {z_val:.1f} odchylenia standardowego)"
                )

        return " | ".join(explanation)

    def train(self, orders: list[models.Order]) -> None:
        """
        Agreguje i trenuje model na podstawie danych historycznych (Feature Engineering).
        """
        if not orders or len(orders) < MIN_SAMPLES_FOR_TRAINING:
            logger.warning(f"⚠️ [AI SECURITY] Zbyt mała próba badawcza do treningu ({len(orders)}).")
            return

        try:
            data = []
            for o in orders:
                q = float(o.quantity) if o.quantity else 0.0
                tp = float(o.total_price) if o.total_price else 0.0
                
                # Naprawiony błąd arytmetyczny (wcześniej było q / tp)
                up = tp / q if q > 0 else 0.0
                
                # Symulacja Feature Engineering dla starszych danych
                cp = float(getattr(o, 'contract_price', 0.0))
                price_dev = ((up - cp) / cp) if cp > 0 else 0.0
                
                data.append([q, tp, up, price_dev])
            
            X = np.array(data)

            # Ekstrakcja statystyk na potrzeby modułu Explainable AI
            self.training_stats = {}
            for i in range(X.shape[1]):
                self.training_stats[i] = {
                    "mean": float(np.mean(X[:, i])),
                    "std": float(np.std(X[:, i]))
                }

            # Wyliczenie stochastycznego progu odcięcia
            dynamic_cont = self._calculate_dynamic_contamination(X)
            logger.info(f"🔄 [AI SECURITY] Optymalizacja z dynamicznym progiem odcięcia: {dynamic_cont:.4f}")

            self.model = IsolationForest(
                contamination=dynamic_cont,
                random_state=42,
                n_jobs=-1
            )
            
            self.model.fit(X)
            self.is_trained = True

            joblib.dump({"model": self.model, "stats": self.training_stats}, MODEL_PATH)
            logger.info("✅ [AI SECURITY] Proces uczenia maszynowego sfinalizowany.")

        except Exception as e:
            logger.error(f"❌ [AI SECURITY] Krytyczny błąd w fazie uczenia: {e}")

    def is_anomaly(self, quantity: float, total_price: float, contract_price: Optional[float] = None) -> bool:
        """
        Pipeline inferencyjny z warstwową weryfikacją (Deterministyczna + Stochastyczna).
        """
        try:
            q = float(quantity)
            tp = float(total_price)
            cp = float(contract_price) if contract_price is not None else 0.0
            
            # Właściwa kalkulacja i wymiarowanie wektora cech
            up = tp / q if q > 0 else 0.0
            price_dev = ((up - cp) / cp) if cp > 0 else 0.0

            # 1. Walidacja Kontraktowa (Reguła twarda)
            if contract_price is not None:
                if up > (cp * 1.15):
                    logger.warning(f"🚨 [AI SECURITY] ODRZUCONO: Cena {up:.2f} PLN przekracza limit kontraktowy ({cp:.2f} PLN).")
                    return True

            # 2. Analiza Statystyczna (Reguła miękka / Isolation Forest)
            if not self.is_trained or self.model is None:
                return False

            features = np.array([[q, tp, up, price_dev]])
            prediction = self.model.predict(features)
            
            if prediction[0] == -1:
                # Odkodowanie i wyjaśnienie decyzji (XAI)
                xai_reason = self._get_feature_importance(features)
                logger.warning(f"🚨 [AI SECURITY] Zablokowano transakcję! Uzasadnienie modelu: {xai_reason}")
                return True
            
            return False

        except Exception as e:
            logger.error(f"❌ [AI SECURITY] Błąd wykonania inferencji przestrzennej: {e}")
            return False

# Inicjalizacja instancji
anomaly_detector = AnomalyDetector()
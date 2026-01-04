import numpy as np
from sklearn.ensemble import IsolationForest
from app import models, schemas

class AnomalyDetector:
    def __init__(self):
        self.model = IsolationForest(contamination=0.05) # Zakładamy, że 5% to anomalie
        self.is_trained = False

    def train(self, orders: list[models.Order]):
        """Uczy się 'normalności' na podstawie historii zamówień"""
        if len(orders) < 10: return # Za mało danych do nauki

        # Cechy do analizy: [Ilość, Cena Całkowita]
        # Można dodać: Dzień tygodnia, Godzina itp.
        data = np.array([[o.quantity, o.total_price] for o in orders])
        
        self.model.fit(data)
        self.is_trained = True
        print("🕵️‍♂️ [AI AUDITOR] Model anomalii wytrenowany na", len(orders), "zamówieniach.")

    def is_anomaly(self, quantity: float, total_price: float) -> bool:
        """Ocenia, czy nowe zamówienie jest podejrzane"""
        if not self.is_trained: return False # Jak nie umiemy, to przepuszczamy

        # Isolation Forest zwraca -1 dla anomalii, 1 dla normy
        prediction = self.model.predict([[quantity, total_price]])
        return prediction[0] == -1

anomaly_detector = AnomalyDetector()
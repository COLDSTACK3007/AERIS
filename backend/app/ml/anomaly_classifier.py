import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional
from sklearn.ensemble import IsolationForest
try:
    import torch
    import torch.nn as nn
    HAS_TORCH = True
except ImportError:
    torch = None
    nn = None
    HAS_TORCH = False

if HAS_TORCH:
    class LSTMAutoencoder(nn.Module):
        """LSTM Autoencoder for sequence-based anomaly detection."""
        def __init__(self, input_dim: int = 1, hidden_dim: int = 32):
            super(LSTMAutoencoder, self).__init__()
            self.encoder = nn.LSTM(input_dim, hidden_dim, batch_first=True)
            self.decoder = nn.LSTM(hidden_dim, input_dim, batch_first=True)

        def forward(self, x):
            encoded, (hn, cn) = self.encoder(x)
            decoded, _ = self.decoder(encoded)
            return decoded
else:
    class LSTMAutoencoder:
        pass

class MLAnomalyDetector:
    def __init__(self, contamination: float = 0.01):
        self.contamination = contamination

    def detect_isolation_forest_anomalies(self, df: pd.DataFrame, parameter: str) -> np.ndarray:
        """Detects point anomalies using Isolation Forest on a single parameter."""
        if parameter not in df.columns:
            return np.zeros(len(df), dtype=bool)

        valid_idx = df[parameter].dropna().index
        vals = df.loc[valid_idx, parameter].values.reshape(-1, 1)
        if len(vals) < 20:
            return np.zeros(len(df), dtype=bool)
        
        clf = IsolationForest(contamination=self.contamination, random_state=42)
        preds = clf.fit_predict(vals)
        # -1 indicates anomaly
        anomaly_mask_clean = (preds == -1)
        
        full_mask = np.zeros(len(df), dtype=bool)
        full_mask[valid_idx] = anomaly_mask_clean
        return full_mask

    def detect_multivariate_ml_anomalies(
        self, df: pd.DataFrame, parameters: List[str]
    ) -> List[Dict[str, Any]]:
        """Detects multi-variate vector anomalies across selected parameters using IsolationForest."""
        available_params = [p for p in parameters if p in df.columns]
        if len(available_params) < 2 or len(df) < 30:
            return []

        feat_df = df[available_params].fillna(df[available_params].median()).fillna(0.0)
        clf = IsolationForest(contamination=0.01, random_state=42)
        preds = clf.fit_predict(feat_df)
        scores = clf.decision_function(feat_df)

        ml_anomalies = []
        # Filter for true statistical outliers (score < -0.15) to avoid ignition ramp false positives
        anomaly_indices = np.where((preds == -1) & (scores < -0.15))[0]

        for idx in anomaly_indices:
            t = float(df.loc[idx, "timestamp"])
            phase = str(df.loc[idx, "flight_phase"]) if "flight_phase" in df.columns else "UNKNOWN"
            score = float(scores[idx])
            
            # Skip normal startup zero values during PRE_LAUNCH ignition
            if t < 5.0 and phase in ["PRE_LAUNCH", "LIFTOFF"]:
                continue

            # Find parameter with largest normalized deviation from median
            diffs = (feat_df.iloc[idx] - feat_df.median()).abs() / (feat_df.std() + 1e-6)
            top_param = str(diffs.idxmax())

            ml_anomalies.append({
                "timestamp": t,
                "parameter": top_param,
                "anomaly_type": "NOISE" if "vib" in top_param else "SPIKE",
                "severity": "CRITICAL" if score < -0.22 else "WARNING",
                "description": f"Unsupervised ML (IsolationForest) point anomaly detected in {top_param} (anomaly score: {score:.3f})",
                "value_observed": float(feat_df.loc[idx, top_param]),
                "confidence": round(float(np.clip(0.75 + abs(score), 0.75, 0.99)), 2),
                "flight_phase": phase,
                "method": "ISOLATION_FOREST"
            })

        return ml_anomalies

ml_detector = MLAnomalyDetector()

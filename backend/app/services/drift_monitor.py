"""
Predictive Drift Monitor Service

Detects sustained trends in telemetry parameters using linear regression over
rolling windows. Estimates threshold crossing times where applicable.

Limitations are explicitly exposed: crossing time is only reported when the
trend is statistically meaningful (R² > threshold) and the prediction horizon
is defensible.
"""
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional
from app.services.synthetic_data import PARAM_METADATA


# Rolling window for drift analysis (seconds of data)
DRIFT_WINDOW_SEC = 30.0
# Minimum R² to consider a trend statistically meaningful
MIN_R_SQUARED = 0.60
# Maximum prediction horizon (seconds) beyond which we don't extrapolate
MAX_PREDICTION_HORIZON = 120.0
# Minimum number of data points in window
MIN_POINTS = 20


class DriftMonitorService:
    """Detects predictive drifts and estimates threshold crossing times."""

    def analyze_drift(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Analyzes all relevant parameters for drift trends.
        
        Returns a list of drift analysis results, one per parameter.
        """
        if df.empty or "timestamp" not in df.columns:
            return []

        results = []
        timestamps = df["timestamp"].values

        for param, meta in PARAM_METADATA.items():
            if param not in df.columns:
                continue

            series = df[param].values
            result = self._analyze_single_param(
                timestamps, series, param, meta
            )
            if result is not None:
                results.append(result)

        return results

    def _analyze_single_param(
        self, timestamps: np.ndarray, values: np.ndarray,
        param: str, meta: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Analyzes a single parameter for drift using the most recent window."""
        # Use the last DRIFT_WINDOW_SEC of data
        max_t = timestamps[-1]
        window_mask = timestamps >= (max_t - DRIFT_WINDOW_SEC)
        t_window = timestamps[window_mask]
        v_window = values[window_mask]

        # Remove NaN
        valid_mask = ~np.isnan(v_window)
        t_valid = t_window[valid_mask]
        v_valid = v_window[valid_mask]

        if len(v_valid) < MIN_POINTS:
            return None

        # Fit linear regression: v = slope * t + intercept
        t_centered = t_valid - t_valid[0]
        try:
            coeffs = np.polyfit(t_centered, v_valid, 1)
        except (np.linalg.LinAlgError, ValueError):
            return None

        slope = float(coeffs[0])
        intercept = float(coeffs[1])

        # Calculate R²
        predicted = slope * t_centered + intercept
        ss_res = np.sum((v_valid - predicted) ** 2)
        ss_tot = np.sum((v_valid - np.mean(v_valid)) ** 2)
        r_squared = 1.0 - (ss_res / (ss_tot + 1e-12))

        current_value = float(v_valid[-1])
        param_min = meta.get("min", None)
        param_max = meta.get("max", None)

        # Determine if trend is statistically meaningful
        is_meaningful = bool(r_squared >= MIN_R_SQUARED and abs(slope) > 1e-8)

        # Estimate crossing time if trend is meaningful and thresholds exist
        crossing_time_upper = None
        crossing_time_lower = None
        time_to_crossing = None
        crossing_threshold = None
        crossing_direction = None

        if is_meaningful and param_max is not None and slope > 0:
            # Drifting upward toward max
            if current_value < param_max:
                dt = (param_max - current_value) / slope
                if 0 < dt <= MAX_PREDICTION_HORIZON:
                    crossing_time_upper = round(float(max_t + dt), 2)
                    time_to_crossing = round(float(dt), 2)
                    crossing_threshold = param_max
                    crossing_direction = "upper"

        if is_meaningful and param_min is not None and slope < 0:
            # Drifting downward toward min
            if current_value > param_min:
                dt = (param_min - current_value) / slope
                if 0 < dt <= MAX_PREDICTION_HORIZON:
                    crossing_time_lower = round(float(max_t + dt), 2)
                    if time_to_crossing is None or dt < time_to_crossing:
                        time_to_crossing = round(float(dt), 2)
                        crossing_threshold = param_min
                        crossing_direction = "lower"

        # Trend strength classification
        if not is_meaningful:
            trend_status = "stable"
        elif abs(slope) * DRIFT_WINDOW_SEC < 0.01 * (abs(current_value) + 1e-6):
            trend_status = "negligible"
        elif time_to_crossing is not None:
            trend_status = "approaching_threshold"
        else:
            trend_status = "trending"

        return {
            "parameter": param,
            "unit": meta.get("unit", ""),
            "current_value": round(current_value, 4),
            "slope_per_second": round(slope, 6),
            "intercept": round(intercept, 4),
            "r_squared": round(float(r_squared), 4),
            "is_meaningful": is_meaningful,
            "trend_status": trend_status,
            "window_seconds": round(float(t_valid[-1] - t_valid[0]), 2),
            "data_points": int(len(v_valid)),
            "threshold_min": param_min,
            "threshold_max": param_max,
            "crossing_time_upper": crossing_time_upper,
            "crossing_time_lower": crossing_time_lower,
            "time_to_crossing": time_to_crossing,
            "crossing_threshold": crossing_threshold,
            "crossing_direction": crossing_direction,
            "analysis_timestamp": round(float(max_t), 2),
        }

    def get_drift_for_parameter(
        self, df: pd.DataFrame, param: str
    ) -> Optional[Dict[str, Any]]:
        """Analyzes drift for a single specific parameter."""
        if param not in PARAM_METADATA or param not in df.columns:
            return None
        return self._analyze_single_param(
            df["timestamp"].values, df[param].values,
            param, PARAM_METADATA[param]
        )


# Module-level singleton
drift_monitor = DriftMonitorService()

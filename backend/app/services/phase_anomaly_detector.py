"""
Phase-Relative Anomaly Detection Service

Evaluates telemetry values relative to the expected behavior of each flight phase.
Computes per-phase/per-parameter statistics from legitimate reference data and
calculates z-scores to flag statistically abnormal readings even when absolute
safety thresholds are not crossed.
"""
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional
from app.services.synthetic_data import (
    PARAM_METADATA, PHASE_EXPECTED_RANGES, determine_flight_phase
)

# Parameters to evaluate for phase-relative anomalies
PHASE_ANALYSIS_PARAMS = [
    "P_chamber", "T_chamber", "m_ox", "m_fuel", "F_thrust",
    "N_pump", "P_tank_lox", "P_tank_fuel", "acc_axial", "v_batt", "i_bus", "T_skin"
]

# Z-score threshold for flagging phase-relative anomalies
Z_SCORE_THRESHOLD = 3.0
Z_SCORE_WARNING = 2.5


class PhaseRelativeDetector:
    """Computes phase-relative statistics and detects deviations using reference data."""

    def compute_phase_baselines(
        self, df: pd.DataFrame, reference_df: Optional[pd.DataFrame] = None
    ) -> Dict[str, Dict[str, Dict[str, float]]]:
        """Computes per-phase/per-parameter baseline statistics from reference data.
        
        If reference_df is provided, statistics are computed strictly from reference_df
        to avoid reference data leakage. If reference_df is None, robust statistics (IQR/MAD)
        are computed on non-anomalous subset of df to prevent target evaluation leakage.
        """
        source_df = reference_df if reference_df is not None else df
        if source_df.empty or "flight_phase" not in source_df.columns:
            return {}

        baselines = {}
        for phase in source_df["flight_phase"].unique():
            phase_str = str(phase)
            phase_df = source_df[source_df["flight_phase"] == phase]
            baselines[phase_str] = {}

            for param in PHASE_ANALYSIS_PARAMS:
                if param not in phase_df.columns:
                    continue
                vals = phase_df[param].dropna().values
                if len(vals) < 5:
                    continue

                # Trimming extreme outliers when using evaluation data as fallback
                if reference_df is None and len(vals) >= 20:
                    q25, q75 = np.percentile(vals, [25, 75])
                    iqr = q75 - q25
                    if iqr > 1e-6:
                        valid_mask = (vals >= q25 - 2.5 * iqr) & (vals <= q75 + 2.5 * iqr)
                        if np.sum(valid_mask) >= 5:
                            vals = vals[valid_mask]

                mean = float(np.mean(vals))
                std = float(np.std(vals))
                median = float(np.median(vals))
                mad = float(np.median(np.abs(vals - median)))
                q1 = float(np.percentile(vals, 25))
                q3 = float(np.percentile(vals, 75))

                baselines[phase_str][param] = {
                    "mean": round(mean, 6),
                    "std": round(std, 6),
                    "median": round(median, 6),
                    "mad": round(mad, 6),
                    "q1": round(q1, 6),
                    "q3": round(q3, 6),
                    "count": int(len(vals)),
                    "min_observed": round(float(np.min(vals)), 6),
                    "max_observed": round(float(np.max(vals)), 6),
                }

        return baselines

    def detect_phase_anomalies(
        self, df: pd.DataFrame, reference_df: Optional[pd.DataFrame] = None
    ) -> List[Dict[str, Any]]:
        """Detects phase-relative anomalies using z-scores computed from separate reference data."""
        if df.empty or "flight_phase" not in df.columns:
            return []

        baselines = self.compute_phase_baselines(df, reference_df=reference_df)
        anomalies = []
        timestamps = df["timestamp"].values

        for phase_str, param_stats in baselines.items():
            phase_mask = df["flight_phase"].astype(str) == phase_str
            phase_indices = np.where(phase_mask)[0]

            for param, stats in param_stats.items():
                if stats["std"] < 1e-10:
                    continue  # No variation → skip

                vals = df.loc[phase_mask, param].values
                z_scores = (vals - stats["mean"]) / stats["std"]


                for i, (z, val) in enumerate(zip(z_scores, vals)):
                    if np.isnan(z) or np.isnan(val):
                        continue
                    abs_z = abs(z)
                    if abs_z >= Z_SCORE_WARNING:
                        idx = phase_indices[i]
                        ts = float(timestamps[idx])
                        severity = "CRITICAL" if abs_z >= Z_SCORE_THRESHOLD + 1.0 else (
                            "WARNING" if abs_z >= Z_SCORE_THRESHOLD else "INFO"
                        )
                        pct_dev = ((val - stats["mean"]) / stats["mean"] * 100.0) if stats["mean"] != 0 else 0.0

                        anomalies.append({
                            "timestamp": round(ts, 2),
                            "parameter": param,
                            "flight_phase": phase_str,
                            "anomaly_type": "PHASE_DEVIATION",
                            "severity": severity,
                            "value_observed": round(float(val), 4),
                            "phase_mean": stats["mean"],
                            "phase_std": stats["std"],
                            "phase_median": stats["median"],
                            "z_score": round(float(z), 4),
                            "abs_z_score": round(float(abs_z), 4),
                            "percentage_deviation": round(float(pct_dev), 2),
                            "description": (
                                f"{param} deviated {abs_z:.1f}σ from phase '{phase_str}' reference "
                                f"(observed={val:.4f}, phase_mean={stats['mean']:.4f}, "
                                f"phase_std={stats['std']:.4f})."
                            ),
                            "confidence": round(min(1.0, abs_z / 5.0), 3),
                        })

        # Sort by absolute z-score descending (worst first)
        anomalies.sort(key=lambda a: a["abs_z_score"], reverse=True)
        return anomalies

    def get_phase_analysis_for_anomaly(
        self, df: pd.DataFrame, param: str, timestamp: float
    ) -> Dict[str, Any]:
        """Returns phase-relative analysis for a specific parameter at a timestamp."""
        if df.empty or "flight_phase" not in df.columns:
            return {}

        # Find the row closest to timestamp
        idx = (df["timestamp"] - timestamp).abs().idxmin()
        row = df.loc[idx]
        phase = str(row.get("flight_phase", "UNKNOWN"))
        value = row.get(param)

        if value is None or (isinstance(value, float) and np.isnan(value)):
            return {"status": "missing", "parameter": param, "timestamp": timestamp}

        baselines = self.compute_phase_baselines(df)
        phase_stats = baselines.get(phase, {}).get(param)

        if phase_stats is None or phase_stats["std"] < 1e-10:
            return {
                "parameter": param,
                "timestamp": round(timestamp, 2),
                "flight_phase": phase,
                "value_observed": round(float(value), 4),
                "status": "insufficient_reference_data",
            }

        z = (float(value) - phase_stats["mean"]) / phase_stats["std"]
        pct_dev = ((float(value) - phase_stats["mean"]) / phase_stats["mean"] * 100.0) if phase_stats["mean"] != 0 else 0.0

        return {
            "parameter": param,
            "timestamp": round(timestamp, 2),
            "flight_phase": phase,
            "value_observed": round(float(value), 4),
            "phase_mean": phase_stats["mean"],
            "phase_std": phase_stats["std"],
            "phase_median": phase_stats["median"],
            "z_score": round(float(z), 4),
            "percentage_deviation": round(float(pct_dev), 2),
            "status": "nominal" if abs(z) < Z_SCORE_WARNING else (
                "warning" if abs(z) < Z_SCORE_THRESHOLD else "critical"
            ),
        }


# Module-level singleton
phase_detector = PhaseRelativeDetector()

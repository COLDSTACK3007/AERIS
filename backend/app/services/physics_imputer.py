import numpy as np
import pandas as pd
from scipy.interpolate import CubicSpline
from typing import Dict, List, Tuple, Any
from app.services.synthetic_data import PARAM_METADATA, ISP, G0, K_CHAMBER, RESIDUAL_TOLERANCES
from app.ml.pinn_model import pinn_predictor



class ExtendedKalmanFilter:
    """Extended Kalman Filter (EKF) for 1D telemetry state trajectory tracking [x, dx/dt].
    
    State model:
        x(k+1) = F * x(k) + process_noise
        z(k)   = H * x(k) + measurement_noise
    
    where:
        x = [value, velocity]^T
        F = [[1, dt], [0, 1]]  (constant velocity model)
        H = [1, 0]
    
    Limitation: This is a simplified constant-velocity model. It will lag
    during rapid transients but provides smooth interpolation for gaps.
    """
    def __init__(self, init_val: float, dt: float = 0.1, 
                 process_noise: float = 1e-3, measurement_noise: float = 1e-2,
                 init_velocity: float = 0.0):
        self.dt = dt
        # State vector: [value, velocity] — velocity initialized from data if available
        self.x = np.array([[init_val], [init_velocity]])
        # State transition matrix F
        self.F = np.array([[1.0, dt], [0.0, 1.0]])
        # Measurement matrix H
        self.H = np.array([[1.0, 0.0]])
        # Covariance matrix P
        self.P = np.eye(2) * 0.1
        # Process noise Q
        self.Q = np.eye(2) * process_noise
        # Measurement noise R
        self.R = np.array([[measurement_noise]])

    def predict(self):
        self.x = np.dot(self.F, self.x)
        self.P = np.dot(np.dot(self.F, self.P), self.F.T) + self.Q
        return float(self.x[0, 0])

    def update(self, z: float):
        y = np.array([[z]]) - np.dot(self.H, self.x)
        S = np.dot(np.dot(self.H, self.P), self.H.T) + self.R
        K = np.dot(np.dot(self.P, self.H.T), np.linalg.inv(S))
        self.x = self.x + np.dot(K, y)
        self.P = self.P - np.dot(np.dot(K, self.H), self.P)
        return float(self.x[0, 0])


class PhysicsImputerService:
    def impute_telemetry_dataset(
        self, df: pd.DataFrame, anomalies: List[Dict[str, Any]]
    ) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
        """Performs physics-constrained data imputation across all missing telemetry values.
        
        Strategy by gap duration:
            Short gap  (≤1s):  Cubic spline interpolation
            Medium gap (1-5s): Physics-based reconstruction where equations available
            Long gap   (>5s):  Ensemble (physics + EKF state estimator)
        
        Every imputed value includes:
            - imputation_method
            - confidence score
            - physics_residual (normalized by parameter-specific tolerance)
            - original_missing = True
        """
        df_imputed = df.copy()
        imputation_records = []
        
        for param in PARAM_METADATA.keys():
            if param not in df_imputed.columns:
                continue
                
            series = df_imputed[param]
            if not series.isna().any():
                continue
                
            timestamps = df_imputed["timestamp"].values
            is_nan = series.isna().values
            nan_indices = np.where(is_nan)[0]
            if len(nan_indices) == 0:
                continue
                
            groups = np.split(nan_indices, np.where(np.diff(nan_indices) != 1)[0] + 1)
            
            for group in groups:
                if len(group) == 0:
                    continue
                    
                start_idx = group[0]
                end_idx = group[-1]
                
                t_start = timestamps[max(0, start_idx - 1)]
                t_end = timestamps[min(len(timestamps) - 1, end_idx + 1)]
                gap_duration = float(t_end - t_start)
                
                # Select strategy by gap duration
                if gap_duration <= 1.0:
                    imputed_vals, method, base_conf = self._impute_short_gap(df_imputed, param, group)
                elif gap_duration <= 5.0:
                    imputed_vals, method, base_conf = self._impute_medium_gap(df_imputed, param, group)
                else:
                    imputed_vals, method, base_conf = self._impute_long_gap(df_imputed, param, group)
                    
                # Apply imputed values to dataset
                df_imputed.loc[group, param] = imputed_vals
                
                # Compute physics residuals and confidence scores
                tolerance = RESIDUAL_TOLERANCES.get(param, 1.0)
                for idx_i, g_idx in enumerate(group):
                    t_g = float(timestamps[g_idx])
                    val_imp = float(imputed_vals[idx_i])
                    
                    phys_res = self._compute_point_physics_residual(df_imputed, param, g_idx, val_imp)
                    # Normalize residual by parameter-specific tolerance
                    normalized_res = phys_res / tolerance if tolerance > 0 else phys_res
                    conf_score = round(float(np.clip(base_conf - normalized_res * 0.1, 0.60, 0.99)), 2)
                    
                    imputation_records.append({
                        "timestamp": t_g,
                        "parameter": param,
                        "original_value": None,
                        "original_missing": True,
                        "imputed_value": val_imp,
                        "confidence_score": conf_score,
                        "gap_duration": round(gap_duration, 2),
                        "method_used": method,
                        "physics_residual": round(float(phys_res), 4),
                        "normalized_residual": round(float(normalized_res), 4)
                    })
                    
        # Apply physical bounds enforcement pass
        df_imputed = self._apply_physical_bounds_pass(df_imputed)
        
        return df_imputed, imputation_records

    def _impute_short_gap(
        self, df: pd.DataFrame, param: str, group: np.ndarray
    ) -> Tuple[np.ndarray, str, float]:
        """Short gaps (≤1s): Cubic spline interpolation with boundary continuity."""
        valid_mask = ~df[param].isna()
        x_valid = df.loc[valid_mask, "timestamp"].values
        y_valid = df.loc[valid_mask, param].values
        
        target_t = df.loc[group, "timestamp"].values
        
        if len(x_valid) >= 4:
            cs = CubicSpline(x_valid, y_valid)
            imputed = cs(target_t)
        else:
            imputed = np.interp(target_t, x_valid, y_valid)
            
        return imputed, "Cubic Spline Interpolation", 0.96

    def _impute_medium_gap(
        self, df: pd.DataFrame, param: str, group: np.ndarray
    ) -> Tuple[np.ndarray, str, float]:
        """Medium gaps (1-5s): Physics-based reconstruction where equations are
        available, otherwise falls back to spline interpolation."""
        target_t = df.loc[group, "timestamp"].values
        
        # Physics-based: Thrust from flow rates
        if param == "F_thrust" and "m_ox" in df.columns and "m_fuel" in df.columns:
            m_ox = df.loc[group, "m_ox"].fillna(240.0).values
            m_fuel = df.loc[group, "m_fuel"].fillna(96.0).values
            imputed = (m_ox + m_fuel) * ISP * G0 / 1000.0
            method = "Physics (Rocket Thrust Equation)"
        # Physics-based: Chamber pressure from flow rates
        elif param == "P_chamber" and "m_ox" in df.columns:
            m_ox = df.loc[group, "m_ox"].fillna(240.0).values
            m_fuel = df.loc[group, "m_fuel"].fillna(96.0).values
            imputed = K_CHAMBER * (m_ox + m_fuel)
            method = "Physics (Empirical Chamber Pressure)"
        else:
            # Neural network model prediction (PINN Reconstruction)
            preds = pinn_predictor.predict_parameters(target_t, telemetry_df=df, target_param=param)
            if param in preds and not np.isnan(preds[param]).any():
                imputed = preds[param]
                method = f"PINN {'Reconstruction' if pinn_predictor.status == 'TRAINED' else 'Prototype'} (Neural Net Prediction)"
            else:
                imputed, _, _ = self._impute_short_gap(df, param, group)
                method = "Cubic Spline (Fallback)"
            
        return imputed, method, 0.89

    def _impute_long_gap(
        self, df: pd.DataFrame, param: str, group: np.ndarray
    ) -> Tuple[np.ndarray, str, float]:
        """Long gaps (>5s): Ensemble of physics/PINN prediction + EKF state estimator."""
        target_t = df.loc[group, "timestamp"].values
        valid_before = df.loc[:group[0]-1, param].dropna()
        
        init_val = float(valid_before.iloc[-1]) if not valid_before.empty else PARAM_METADATA.get(param, {}).get("nominal", 1.0)
        dt = float(np.median(np.diff(target_t))) if len(target_t) > 1 else 0.1
        
        # Estimate initial velocity from last known data
        init_velocity = 0.0
        if len(valid_before) >= 3:
            recent = valid_before.iloc[-3:]
            recent_t = df.loc[recent.index, "timestamp"].values
            if len(recent_t) >= 2 and (recent_t[-1] - recent_t[0]) > 0:
                init_velocity = float((recent.iloc[-1] - recent.iloc[0]) / (recent_t[-1] - recent_t[0]))
        
        # 1. Extended Kalman Filter Trajectory (with estimated initial velocity)
        ekf = ExtendedKalmanFilter(init_val=init_val, dt=dt, init_velocity=init_velocity)
        ekf_preds = [ekf.predict() for _ in range(len(group))]
        ekf_vals = np.array(ekf_preds)
        
        # 2. Physics / PINN prediction
        pinn_vals, _, _ = self._impute_medium_gap(df, param, group)
        
        # 3. Ensemble blending: 50% physics/PINN, 50% EKF
        imputed = 0.5 * pinn_vals + 0.5 * ekf_vals
        
        return imputed, "Ensemble (Physics + Extended Kalman Filter)", 0.78

    def _compute_point_physics_residual(
        self, df: pd.DataFrame, param: str, idx: int, val_imp: float
    ) -> float:
        """Calculates physics residual at a specific point. Returns raw residual
        in the parameter's native units."""
        try:
            if param == "F_thrust" and "m_ox" in df.columns and "m_fuel" in df.columns:
                m_ox = float(df.loc[idx, "m_ox"]) if pd.notna(df.loc[idx, "m_ox"]) else 240.0
                m_fuel = float(df.loc[idx, "m_fuel"]) if pd.notna(df.loc[idx, "m_fuel"]) else 96.0
                expected_f = (m_ox + m_fuel) * ISP * G0 / 1000.0
                return abs(val_imp - expected_f)
            elif param == "P_chamber" and "m_ox" in df.columns:
                m_ox = float(df.loc[idx, "m_ox"]) if pd.notna(df.loc[idx, "m_ox"]) else 240.0
                m_fuel = float(df.loc[idx, "m_fuel"]) if pd.notna(df.loc[idx, "m_fuel"]) else 96.0
                expected_p = K_CHAMBER * (m_ox + m_fuel)
                return abs(val_imp - expected_p)
            else:
                # For parameters without physics equations, compute deviation
                # from the parameter's nominal value
                meta = PARAM_METADATA.get(param, {"nominal": 1.0})
                nominal = meta.get("nominal", 1.0)
                if nominal == 0.0:
                    return abs(val_imp)
                return abs(val_imp - nominal) * 0.01  # Scale down non-physics residuals
        except Exception:
            return 0.05

    def _apply_physical_bounds_pass(self, df: pd.DataFrame) -> pd.DataFrame:
        """Enforces hard physical bounds (non-negative constraints) on imputed values.
        
        NOTE: This is a physical BOUNDS enforcement, not conservation law enforcement.
        It clamps values to physically meaningful ranges (e.g., pressure >= 0).
        """
        for param in ["P_chamber", "T_chamber", "m_ox", "m_fuel", "F_thrust", "N_pump", "P_tank_lox", "P_tank_fuel"]:
            if param in df.columns:
                df[param] = np.maximum(0.0, df[param].values)
                
        return df

physics_imputer = PhysicsImputerService()

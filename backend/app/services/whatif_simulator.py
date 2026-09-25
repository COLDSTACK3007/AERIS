"""
Mission What-If Simulator Service

Allows the user to modify a telemetry parameter and calculates downstream
effects using the project's actual physics equations. This is a simulation
tool and does not alter the original telemetry dataset.
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from app.services.synthetic_data import (
    ISP, G0, K_CHAMBER, PARAM_METADATA, THRUST_TOLERANCE_KN, PRESSURE_TOLERANCE_MPA
)


class WhatIfSimulator:
    """Simulates the downstream physical effects of modifying telemetry parameters."""

    def simulate(
        self, df: pd.DataFrame, param: str,
        modification_pct: float = 0.0,
        modification_abs: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Simulates the effect of modifying a parameter.
        
        Args:
            df: Original telemetry DataFrame
            param: Parameter to modify (e.g., "m_ox")
            modification_pct: Percentage change (e.g., -5.0 for -5%)
            modification_abs: Absolute change (overrides pct if given)
            
        Returns:
            Dictionary with original vs simulated values and downstream effects.
        """
        if df.empty or param not in df.columns:
            return {"error": f"Parameter '{param}' not found in telemetry data."}

        original = df.copy()
        simulated = df.copy()

        # Apply modification
        orig_vals = original[param].values.copy()
        if modification_abs is not None:
            sim_vals = orig_vals + modification_abs
            mod_description = f"{param} {'+'if modification_abs>=0 else ''}{modification_abs:.4f} {PARAM_METADATA.get(param, {}).get('unit', '')}"
        else:
            sim_vals = orig_vals * (1.0 + modification_pct / 100.0)
            mod_description = f"{param} {'+'if modification_pct>=0 else ''}{modification_pct:.1f}%"

        simulated[param] = sim_vals

        # Calculate downstream physics effects
        effects = self._calculate_downstream_effects(original, simulated, param)

        # Calculate health impact
        health_impact = self._estimate_health_impact(original, simulated)

        # Physics consistency check
        physics_check = self._check_physics_consistency(simulated)

        return {
            "simulation_label": f"SIMULATION: {mod_description}",
            "modified_parameter": param,
            "modification_percent": round(modification_pct, 2),
            "modification_absolute": modification_abs,
            "original_mean": round(float(np.nanmean(orig_vals)), 4),
            "simulated_mean": round(float(np.nanmean(sim_vals)), 4),
            "downstream_effects": effects,
            "health_impact": health_impact,
            "physics_consistency": physics_check,
            "is_simulation": True,
            "warning": "This is a simulation. Original telemetry data is unchanged.",
        }

    def _calculate_downstream_effects(
        self, original: pd.DataFrame, simulated: pd.DataFrame, modified_param: str
    ) -> List[Dict[str, Any]]:
        """Calculates downstream effects using actual physics equations."""
        effects = []

        # Get available parameters
        has_mox = "m_ox" in original.columns
        has_mfuel = "m_fuel" in original.columns
        has_fthrust = "F_thrust" in original.columns
        has_pchamber = "P_chamber" in original.columns

        # Physics relationship: F_thrust = (m_ox + m_fuel) * ISP * G0 / 1000
        if modified_param in ("m_ox", "m_fuel") and has_mox and has_mfuel:
            mox_sim = simulated["m_ox"].values
            mfuel_sim = simulated["m_fuel"].values
            mox_orig = original["m_ox"].values
            mfuel_orig = original["m_fuel"].values

            # Simulated thrust
            f_sim = (mox_sim + mfuel_sim) * ISP * G0 / 1000.0
            f_orig = (mox_orig + mfuel_orig) * ISP * G0 / 1000.0

            effects.append({
                "parameter": "F_thrust",
                "equation": "F = (m_ox + m_fuel) × ISP × g₀ / 1000",
                "original_mean": round(float(np.nanmean(f_orig)), 4),
                "simulated_mean": round(float(np.nanmean(f_sim)), 4),
                "change_percent": round(float((np.nanmean(f_sim) - np.nanmean(f_orig)) / (np.nanmean(f_orig) + 1e-12) * 100), 2),
                "unit": "kN",
            })

            # Simulated chamber pressure
            p_sim = K_CHAMBER * (mox_sim + mfuel_sim)
            p_orig = K_CHAMBER * (mox_orig + mfuel_orig)
            effects.append({
                "parameter": "P_chamber",
                "equation": "P = K_CHAMBER × (m_ox + m_fuel)",
                "original_mean": round(float(np.nanmean(p_orig)), 4),
                "simulated_mean": round(float(np.nanmean(p_sim)), 4),
                "change_percent": round(float((np.nanmean(p_sim) - np.nanmean(p_orig)) / (np.nanmean(p_orig) + 1e-12) * 100), 2),
                "unit": "MPa",
            })

            # O/F ratio
            of_orig = mox_orig / (mfuel_orig + 1e-6)
            of_sim = mox_sim / (mfuel_sim + 1e-6)
            # Only report meaningful phases (non-zero flow)
            active_mask = (mfuel_orig > 1.0)
            if np.any(active_mask):
                effects.append({
                    "parameter": "O/F_ratio",
                    "equation": "O/F = m_ox / m_fuel",
                    "original_mean": round(float(np.nanmean(of_orig[active_mask])), 4),
                    "simulated_mean": round(float(np.nanmean(of_sim[active_mask])), 4),
                    "change_percent": round(float((np.nanmean(of_sim[active_mask]) - np.nanmean(of_orig[active_mask])) / (np.nanmean(of_orig[active_mask]) + 1e-12) * 100), 2),
                    "unit": "ratio",
                })

        elif modified_param == "F_thrust" and has_mox and has_mfuel:
            # Inverse: if thrust changed, what mass flow ratio implies?
            mox_orig = original["m_ox"].values
            mfuel_orig = original["m_fuel"].values
            f_orig = (mox_orig + mfuel_orig) * ISP * G0 / 1000.0
            f_sim = simulated["F_thrust"].values

            implied_total_flow = f_sim * 1000.0 / (ISP * G0)
            orig_total_flow = mox_orig + mfuel_orig

            effects.append({
                "parameter": "total_mass_flow",
                "equation": "m_total = F × 1000 / (ISP × g₀)",
                "original_mean": round(float(np.nanmean(orig_total_flow)), 4),
                "simulated_mean": round(float(np.nanmean(implied_total_flow)), 4),
                "change_percent": round(float((np.nanmean(implied_total_flow) - np.nanmean(orig_total_flow)) / (np.nanmean(orig_total_flow) + 1e-12) * 100), 2),
                "unit": "kg/s",
            })

        elif modified_param == "P_chamber" and has_mox and has_mfuel:
            p_sim = simulated["P_chamber"].values
            implied_total_flow = p_sim / K_CHAMBER
            orig_total_flow = original["m_ox"].values + original["m_fuel"].values

            effects.append({
                "parameter": "total_mass_flow",
                "equation": "m_total = P_chamber / K_CHAMBER",
                "original_mean": round(float(np.nanmean(orig_total_flow)), 4),
                "simulated_mean": round(float(np.nanmean(implied_total_flow)), 4),
                "change_percent": round(float((np.nanmean(implied_total_flow) - np.nanmean(orig_total_flow)) / (np.nanmean(orig_total_flow) + 1e-12) * 100), 2),
                "unit": "kg/s",
            })

        return effects

    def _estimate_health_impact(
        self, original: pd.DataFrame, simulated: pd.DataFrame
    ) -> Dict[str, Any]:
        """Estimates the health impact of the simulation based on threshold exceedances."""
        violations = []
        for param, meta in PARAM_METADATA.items():
            if param not in simulated.columns:
                continue
            vals = simulated[param].dropna().values
            if len(vals) == 0:
                continue

            above_max = float(np.sum(vals > meta["max"])) / len(vals) * 100
            below_min = float(np.sum(vals < meta["min"])) / len(vals) * 100

            if above_max > 0 or below_min > 0:
                violations.append({
                    "parameter": param,
                    "above_max_pct": round(above_max, 2),
                    "below_min_pct": round(below_min, 2),
                    "threshold_min": meta["min"],
                    "threshold_max": meta["max"],
                })

        return {
            "threshold_violations": violations,
            "total_violations": len(violations),
            "assessment": "NOMINAL" if len(violations) == 0 else (
                "WARNING" if len(violations) <= 2 else "CRITICAL"
            ),
        }

    def _check_physics_consistency(self, simulated: pd.DataFrame) -> Dict[str, Any]:
        """Checks physics consistency of the simulated data."""
        checks = []

        if all(c in simulated.columns for c in ["m_ox", "m_fuel", "F_thrust"]):
            valid_thrust = simulated.dropna(subset=["m_ox", "m_fuel", "F_thrust"])
            if not valid_thrust.empty:
                mox = valid_thrust["m_ox"].values
                mfuel = valid_thrust["m_fuel"].values
                fthrust = valid_thrust["F_thrust"].values
                expected_f = (mox + mfuel) * ISP * G0 / 1000.0
                active = expected_f > 10.0  # Only check during active phases
                if np.any(active):
                    residuals = np.abs(fthrust[active] - expected_f[active])
                    checks.append({
                        "relationship": "F = (m_ox + m_fuel) × ISP × g₀ / 1000",
                        "mean_residual": round(float(np.mean(residuals)), 4),
                        "max_residual": round(float(np.max(residuals)), 4),
                        "unit": "kN",
                        "consistent": bool(np.mean(residuals) < THRUST_TOLERANCE_KN),
                    })

        if all(c in simulated.columns for c in ["m_ox", "m_fuel", "P_chamber"]):
            valid_press = simulated.dropna(subset=["m_ox", "m_fuel", "P_chamber"])
            if not valid_press.empty:
                mox = valid_press["m_ox"].values
                mfuel = valid_press["m_fuel"].values
                pcham = valid_press["P_chamber"].values
                expected_p = K_CHAMBER * (mox + mfuel)
                active = expected_p > 0.1
                if np.any(active):
                    residuals = np.abs(pcham[active] - expected_p[active])
                    checks.append({
                        "relationship": "P = K_CHAMBER × (m_ox + m_fuel)",
                        "mean_residual": round(float(np.mean(residuals)), 4),
                        "max_residual": round(float(np.max(residuals)), 4),
                        "unit": "MPa",
                        "consistent": bool(np.mean(residuals) < PRESSURE_TOLERANCE_MPA),
                    })

        return {
            "checks": checks,
            "overall_consistent": all(c["consistent"] for c in checks) if checks else True,
        }


# Module-level singleton
whatif_simulator = WhatIfSimulator()

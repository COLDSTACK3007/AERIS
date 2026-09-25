import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from collections import deque
from app.services.synthetic_data import PARAM_METADATA

class RingBuffer:
    def __init__(self, capacity: int = 1000):
        self.capacity = capacity
        self.buffer = deque(maxlen=capacity)

    def append(self, item: Dict[str, Any]):
        self.buffer.append(item)

    def get_all(self) -> List[Dict[str, Any]]:
        return list(self.buffer)

    def get_as_dataframe(self) -> pd.DataFrame:
        if not self.buffer:
            return pd.DataFrame()
        return pd.DataFrame(self.buffer)

class TelemetryIngestionService:
    def __init__(self):
        self.ring_buffer = RingBuffer(capacity=5000)

    def parse_csv_telemetry(self, file_content: bytes) -> pd.DataFrame:
        """Parses CSV bytes and standardizes headers and data types."""
        import io
        df = pd.read_csv(io.BytesIO(file_content))
        
        # Clean column names (strip spaces)
        df.columns = [str(c).strip() for c in df.columns]
        
        # Header mapping dictionary for common aliases
        column_mapping = {
            "Time": "timestamp", "time": "timestamp", "t": "timestamp", "Timestamp": "timestamp",
            "Time (s)": "timestamp", "time_sec": "timestamp", "T+": "timestamp",
            "p_chamber": "P_chamber", "P_Chamber": "P_chamber",
            "t_chamber": "T_chamber", "T_Chamber": "T_chamber",
            "M_ox": "m_ox", "M_fuel": "m_fuel",
            "f_thrust": "F_thrust", "Thrust": "F_thrust",
            "n_pump": "N_pump", "Pump_RPM": "N_pump",
            "Vib_X": "vib_x", "Vib_Y": "vib_y", "Vib_Z": "vib_z",
            "Acc_axial": "acc_axial", "V_batt": "v_batt", "I_bus": "i_bus", "T_Skin": "T_skin"
        }
        df.rename(columns=column_mapping, inplace=True)

        # Ensure timestamp column exists
        if "timestamp" not in df.columns:
            df["timestamp"] = np.arange(len(df)) * 0.1
        else:
            df["timestamp"] = pd.to_numeric(df["timestamp"], errors="coerce")
            df.dropna(subset=["timestamp"], inplace=True)

        df = df.sort_values("timestamp").reset_index(drop=True)
        return df

    def resample_multi_rate_data(self, df: pd.DataFrame, target_dt: float = 0.1) -> pd.DataFrame:
        """Resamples multi-rate telemetry data onto a unified time grid using linear interpolation."""
        if df.empty or "timestamp" not in df.columns:
            return df
        
        t_min = float(df["timestamp"].min())
        t_max = float(df["timestamp"].max())
        if t_min == t_max:
            unified_timestamps = np.array([t_min])
        else:
            unified_timestamps = np.arange(t_min, t_max + target_dt/2.0, target_dt)
        
        resampled_data = {"timestamp": unified_timestamps}
        
        for col in df.columns:
            if col in ["timestamp", "flight_phase"]:
                continue
            if pd.api.types.is_numeric_dtype(df[col]):
                # Group by timestamp to eliminate duplicates before interpolation
                s = df.groupby("timestamp")[col].mean().dropna()
                if len(s) > 1:
                    interp_vals = np.interp(unified_timestamps, s.index.values, s.values, left=np.nan, right=np.nan)
                    resampled_data[col] = interp_vals
                elif len(s) == 1:
                    resampled_data[col] = np.full(len(unified_timestamps), s.values[0])
                else:
                    resampled_data[col] = np.nan

        resampled_df = pd.DataFrame(resampled_data)
        
        # Preserve or determine flight phases
        from app.services.synthetic_data import determine_flight_phase
        resampled_df["flight_phase"] = [determine_flight_phase(t) for t in unified_timestamps]
            
        return resampled_df

    def validate_record_ranges(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Validates telemetry fields against PARAM_METADATA constraints."""
        validated = record.copy()
        out_of_bounds = []
        for param, meta in PARAM_METADATA.items():
            if param in validated and validated[param] is not None:
                val = validated[param]
                if not np.isnan(val):
                    if val < meta["min"] or val > meta["max"]:
                        out_of_bounds.append(param)
        validated["_out_of_bounds_params"] = out_of_bounds
        return validated

    def ingest_single_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Ingests a single streaming telemetry record into the ring buffer."""
        validated = self.validate_record_ranges(record)
        self.ring_buffer.append(validated)
        return validated

    def get_recent_buffer_dataframe(self) -> pd.DataFrame:
        """Returns the current contents of the ring buffer as a pandas DataFrame."""
        return self.ring_buffer.get_as_dataframe()

ingestion_service = TelemetryIngestionService()


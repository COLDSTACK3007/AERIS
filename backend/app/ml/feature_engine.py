import numpy as np
import pandas as pd
from typing import Tuple

def extract_time_series_features(
    series: pd.Series, 
    window_size: int = 10
) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    """Calculates rolling mean, rolling std, rate of change (derivative), and z-score."""
    rolling_mean = series.rolling(window=window_size, min_periods=1).mean()
    rolling_std = series.rolling(window=window_size, min_periods=1).std().fillna(1e-5)
    rate_of_change = series.diff().fillna(0.0)
    z_score = (series - rolling_mean) / (rolling_std + 1e-6)
    
    return rolling_mean, rolling_std, rate_of_change, z_score

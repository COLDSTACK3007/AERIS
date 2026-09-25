try:
    import torch
    import torch.nn as nn
    from torch.utils.data import TensorDataset, DataLoader
    HAS_TORCH = True
    ModuleBase = nn.Module
except ImportError:
    torch = None
    nn = None
    TensorDataset = DataLoader = None
    HAS_TORCH = False
    ModuleBase = object
import numpy as np
import pandas as pd
import os
import json
import random
import copy
from typing import Any, Dict, List, Tuple, Optional

from app.services.synthetic_data import (
    ISP, G0, K_CHAMBER, THRUST_TOLERANCE_KN, PRESSURE_TOLERANCE_MPA
)

# =============================================================================
# PINN CONSTANTS & TOLERANCES
# NOTE: ISP, G0, K_CHAMBER, THRUST_TOLERANCE_KN, and PRESSURE_TOLERANCE_MPA
# are imported from app.services.synthetic_data, which is the single
# authoritative source of truth for these project-wide physics constants.
# Do NOT redefine them locally here — a prior version of this file defined
# THRUST_TOLERANCE_KN = 10.0 independently, which silently diverged from the
# 15.0 kN value used everywhere else (dashboard physics-compliance, alerts,
# anomaly detection), producing inconsistent "within tolerance" percentages
# between the PINN training metadata and the live dashboard.
# =============================================================================

# Checkpoint paths
CHECKPOINT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "pinn_checkpoints"))

# Checkpoint files
CHECKPOINT_V3_PATH = os.path.join(CHECKPOINT_DIR, "aeris_pinn_v3.pt")
METADATA_V3_PATH = os.path.join(CHECKPOINT_DIR, "aeris_pinn_v3_metadata.json")

# v2 Checkpoint files (preserved for backward backup)
CHECKPOINT_V2_PATH = os.path.join(CHECKPOINT_DIR, "aeris_pinn_v2.pt")
METADATA_V2_PATH = os.path.join(CHECKPOINT_DIR, "aeris_pinn_v2_metadata.json")

# Legacy pointers
CHECKPOINT_LEGACY_PATH = os.path.join(CHECKPOINT_DIR, "pinn_telemetry.pt")
METADATA_LEGACY_PATH = os.path.join(CHECKPOINT_DIR, "pinn_metadata.json")

TARGET_COLS = ["P_chamber", "T_chamber", "m_ox", "m_fuel", "F_thrust"]
ALL_TELEMETRY_COLS = [
    "P_chamber", "T_chamber", "m_ox", "m_fuel", "F_thrust",
    "N_pump", "P_tank_lox", "P_tank_fuel", "vib_x", "vib_y", "vib_z",
    "acc_axial", "v_batt", "i_bus", "T_skin", "rate_roll", "rate_pitch", "rate_yaw"
]

NOMINAL_VALUES = {
    "P_chamber": 6.22, "T_chamber": 3200.0, "m_ox": 240.0, "m_fuel": 96.0, "F_thrust": 972.0,
    "N_pump": 34944.0, "P_tank_lox": 4.2, "P_tank_fuel": 3.5, "vib_x": 0.5, "vib_y": 0.5,
    "vib_z": 0.5, "acc_axial": 1.2, "v_batt": 28.0, "i_bus": 18.0, "T_skin": 450.0,
    "rate_roll": 0.0, "rate_pitch": 0.0, "rate_yaw": 0.0
}
# NOTE: these values were previously out of sync with PARAM_METADATA in
# synthetic_data.py (e.g. P_tank_lox was 0.35 here vs the true nominal of 4.2 MPa —
# a 12x discrepancy). They are now aligned with the authoritative nominal values
# used everywhere else in the project.


def set_seed(seed: int = 42):
    """Sets deterministic random seeds for reproducibility."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


class TelemetryPINN(ModuleBase):
    """Legacy PINN architecture (4 inputs x 5 outputs). Preserved for backward compatibility."""
    def __init__(self, input_dim: int = 4, output_dim: int = 5):
        super(TelemetryPINN, self).__init__()
        if nn is not None:
            self.net = nn.Sequential(
                nn.Linear(input_dim, 128), nn.Tanh(),
                nn.Linear(128, 128), nn.Tanh(),
                nn.Linear(128, 128), nn.Tanh(),
                nn.Linear(128, 128), nn.Tanh(),
                nn.Linear(128, output_dim)
            )

    def forward(self, x):
        return self.net(x)


class TelemetryPINNv2(ModuleBase):
    """PINN v2 architecture. Preserved for backward backup."""
    def __init__(self, input_dim: int = 12, output_dim: int = 5):
        super(TelemetryPINNv2, self).__init__()
        if nn is not None:
            self.net = nn.Sequential(
                nn.Linear(input_dim, 128), nn.Tanh(),
                nn.Linear(128, 128), nn.Tanh(),
                nn.Linear(128, 128), nn.Tanh(),
                nn.Linear(128, 128), nn.Tanh(),
                nn.Linear(128, output_dim), nn.Sigmoid()
            )

    def forward(self, x):
        return self.net(x)


class TelemetryPINNv3(ModuleBase):
    """
    Target-Aware Conditional Physics-Informed Neural Network (PINN v3).
    Architecture: 4 hidden layers x 128 neurons with Tanh activation and Linear output.
    
    Inputs (43 dims):
        - t_norm (1 dim): normalized timestamp [0, 1]
        - phase_code (1 dim): normalized flight phase [0, 1]
        - target_id_onehot (5 dims): one-hot encoding indicating which target [P, T, m_ox, m_fuel, F] is being predicted
        - telemetry_context (18 dims): Z-score standardized context telemetry (target parameter set to 0.0)
        - mask_indicators (18 dims): binary mask (1.0 = target/masked parameter, 0.0 = observed context)
        
    Outputs (1 dim):
        - predicted Z-score standard scalar for the target parameter
    """
    def __init__(self, input_dim: int = 43, output_dim: int = 1):
        super(TelemetryPINNv3, self).__init__()
        if nn is not None:
            self.net = nn.Sequential(
                nn.Linear(input_dim, 128),
                nn.Tanh(),
                nn.Linear(128, 128),
                nn.Tanh(),
                nn.Linear(128, 128),
                nn.Tanh(),
                nn.Linear(128, 128),
                nn.Tanh(),
                nn.Linear(128, output_dim)
            )

    def forward(self, x):
        return self.net(x)


def compute_physics_residuals(
    t: torch.Tensor, 
    preds: torch.Tensor, 
    isp: float = ISP, 
    g0: float = G0
) -> torch.Tensor:
    """Computes thrust and chamber pressure physics residual losses for training."""
    P_chamber = preds[:, 0]
    T_chamber = preds[:, 1]
    m_ox = preds[:, 2]
    m_fuel = preds[:, 3]
    F_thrust = preds[:, 4]
    
    thrust_expected = (m_ox + m_fuel) * isp * g0 / 1000.0
    res_thrust = torch.mean(((F_thrust - thrust_expected) / THRUST_TOLERANCE_KN) ** 2)
    
    p_expected = K_CHAMBER * (m_ox + m_fuel)
    res_pressure = torch.mean(((P_chamber - p_expected) / PRESSURE_TOLERANCE_MPA) ** 2)
    
    return res_thrust + res_pressure


def build_target_aware_dataset(t_norm_arr, phase_arr, df_telemetry_std, target_cols, all_cols):
    """
    Builds target-aware training samples where target is masked out of context.
    
    For each row and each target k:
        Inputs: [t_norm, phase, target_onehot (5), context_std (18 with target k zeroed), mask_indicator (18 with target k = 1)]
        Target: target k's Z-score standard value
    """
    n_samples = len(t_norm_arr)
    n_targets = len(target_cols)
    n_all = len(all_cols)
    
    inputs_list = []
    targets_list = []
    target_idx_list = []
    t_raw_list = []
    
    X_std_matrix = df_telemetry_std[all_cols].values
    np.random.seed(42)
    
    for t_idx, target_name in enumerate(target_cols):
        target_col_idx = all_cols.index(target_name)
        
        # One-hot target vector (5 dims)
        onehot = np.zeros((n_samples, n_targets), dtype=np.float32)
        onehot[:, t_idx] = 1.0
        
        # Context matrix (18 dims) - zero out target column
        ctx_mat = X_std_matrix.copy()
        mask_mat = np.zeros((n_samples, n_all), dtype=np.float32)
        
        ctx_mat[:, target_col_idx] = 0.0
        mask_mat[:, target_col_idx] = 1.0
        
        # Multi-variable missingness simulation (30% of samples get an extra missing target)
        multi_mask_prob = 0.30
        rand_draws = np.random.rand(n_samples)
        for i in range(n_samples):
            if rand_draws[i] < multi_mask_prob:
                other_targets = [all_cols.index(tc) for tc in target_cols if tc != target_name]
                n_extra = int(np.random.choice([1, 2]))
                extra_cols = np.random.choice(other_targets, size=min(n_extra, len(other_targets)), replace=False)
                for ec in extra_cols:
                    ctx_mat[i, ec] = 0.0
                    mask_mat[i, ec] = 1.0
        
        inp = np.column_stack([
            t_norm_arr[:, None],
            phase_arr[:, None],
            onehot,
            ctx_mat,
            mask_mat
        ])
        
        y_target = X_std_matrix[:, target_col_idx]
        
        inputs_list.append(inp)
        targets_list.append(y_target)
        target_idx_list.append(np.full(n_samples, t_idx))
        t_raw_list.append(t_norm_arr)
        
    X_concat = np.vstack(inputs_list)
    Y_concat = np.concatenate(targets_list)[:, None]
    T_idx_concat = np.concatenate(target_idx_list)
    T_norm_concat = np.concatenate(t_raw_list)
    
    return X_concat, Y_concat, T_idx_concat, T_norm_concat


def train_pinn_v3(epochs: int = 500, lr: float = 3e-3, batch_size: int = 128,
                  verbose: bool = True, seed: int = 42) -> Dict[str, Any]:
    """
    Trains Target-Aware PINN v3 on synthetic telemetry and experimental bipropellant dataset.
    
    Fixes incorporated:
        - Target parameter is NEVER provided as input context when being predicted
        - 18-sensor observed context utilized with standardization fitted ONLY on training split
        - Time-aware block split (70% Train / 15% Val / 15% Test) preventing data leakage
        - Experimental dataset (333 records) directly supervised on measured P_chamber, m_ox, m_fuel
        - Linear output layer with Z-score standardization (no artificial range clipping)
        - Physics curriculum schedule gradually increasing physics loss contribution
        - Deep copy best state checkpoint selection
    """
    set_seed(seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    telemetry_path = os.path.join(base_dir, "dataset", "pinn_telemetry_training_dataset.csv")
    physics_path = os.path.join(base_dir, "dataset", "pinn_common_physics_dataset.csv")
    
    if not os.path.exists(telemetry_path):
        telemetry_path = os.path.abspath("dataset/pinn_telemetry_training_dataset.csv")
        physics_path = os.path.abspath("dataset/pinn_common_physics_dataset.csv")
        
    df_tel = pd.read_csv(telemetry_path)
    df_phys = pd.read_csv(physics_path)
    
    phase_map = {
        "PRE_LAUNCH": 0.0, "LIFTOFF": 0.2, "MAX_Q": 0.4,
        "STAGE_1_FLIGHT": 0.6, "STAGE_SEPARATION": 0.7,
        "STAGE_2_FLIGHT": 0.8, "COAST_ORBIT": 1.0
    }
    
    df_tel = df_tel.sort_values("timestamp").reset_index(drop=True)
    n_tel = len(df_tel)
    
    min_t = df_tel["timestamp"].min()
    max_t = df_tel["timestamp"].max()
    t_norm_all = (df_tel["timestamp"].values - min_t) / (max_t - min_t if max_t > min_t else 1.0)
    phases_all = np.array([phase_map.get(str(p), 0.5) for p in df_tel["flight_phase"]])
    
    # TIME-AWARE BLOCK SPLIT (No data leakage)
    n_train = int(0.70 * n_tel)
    n_val = int(0.15 * n_tel)
    n_test = n_tel - n_train - n_val
    
    train_slice = slice(0, n_train)
    val_slice = slice(n_train, n_train + n_val)
    test_slice = slice(n_train + n_val, n_tel)
    
    # Fit Means and Stds ONLY on 70% Training split
    means_dict = {}
    stds_dict = {}
    
    for col in ALL_TELEMETRY_COLS:
        col_vals = df_tel[col].iloc[train_slice].dropna().values
        m = float(np.mean(col_vals)) if len(col_vals) > 0 else NOMINAL_VALUES.get(col, 1.0)
        s = float(np.std(col_vals)) if len(col_vals) > 0 else 1.0
        if s == 0.0:
            s = 1.0
        means_dict[col] = m
        stds_dict[col] = s
        
    # Standardize complete telemetry dataset using training split statistics
    df_tel_std = pd.DataFrame()
    for col in ALL_TELEMETRY_COLS:
        df_tel_std[col] = (df_tel[col] - means_dict[col]) / stds_dict[col]
        
    # Pre-compute target-aware training datasets
    X_train_np, Y_train_np, Tidx_train_np, Tnorm_train_np = build_target_aware_dataset(
        t_norm_all[train_slice], phases_all[train_slice], df_tel_std.iloc[train_slice], TARGET_COLS, ALL_TELEMETRY_COLS
    )
    
    dataset_train = TensorDataset(
        torch.tensor(X_train_np, dtype=torch.float32),
        torch.tensor(Y_train_np, dtype=torch.float32),
        torch.tensor(Tidx_train_np, dtype=torch.long),
        torch.tensor(Tnorm_train_np, dtype=torch.float32)
    )
    dataloader_train = DataLoader(dataset_train, batch_size=batch_size, shuffle=True)
    
    # Pre-compute validation dataset
    X_val_np, Y_val_np, Tidx_val_np, Tnorm_val_np = build_target_aware_dataset(
        t_norm_all[val_slice], phases_all[val_slice], df_tel_std.iloc[val_slice], TARGET_COLS, ALL_TELEMETRY_COLS
    )
    X_val_t = torch.tensor(X_val_np, dtype=torch.float32).to(device)
    Y_val_t = torch.tensor(Y_val_np, dtype=torch.float32).to(device)
    
    # Pre-compute experimental dataset (333 records)
    exp_mask = df_phys["source"] != "synthetic_telemetry"
    df_exp = df_phys[exp_mask].reset_index(drop=True)
    n_exp = len(df_exp)
    
    exp_p_chamber = df_exp["P_chamber"].values
    exp_m_ox = df_exp["m_ox"].values
    exp_m_fuel = df_exp["m_fuel"].values
    exp_total_flow = df_exp["total_mass_flow_kg_s"].values
    exp_of_ratio = df_exp["OF_ratio"].values
    
    # Build experimental input batches for measured targets P_chamber (0), m_ox (2), m_fuel (3)
    exp_inputs_list = []
    exp_targets_list = []
    
    for t_idx, target_name in [(0, "P_chamber"), (2, "m_ox"), (3, "m_fuel")]:
        target_col_idx = ALL_TELEMETRY_COLS.index(target_name)
        
        onehot = np.zeros((n_exp, 5), dtype=np.float32)
        onehot[:, t_idx] = 1.0
        
        ctx_mat = np.zeros((n_exp, len(ALL_TELEMETRY_COLS)), dtype=np.float32)
        ctx_mat[:, 0] = (exp_p_chamber - means_dict["P_chamber"]) / stds_dict["P_chamber"]
        ctx_mat[:, 2] = (exp_m_ox - means_dict["m_ox"]) / stds_dict["m_ox"]
        ctx_mat[:, 3] = (exp_m_fuel - means_dict["m_fuel"]) / stds_dict["m_fuel"]
        ctx_mat[:, target_col_idx] = 0.0  # mask target
        
        mask_mat = np.zeros((n_exp, len(ALL_TELEMETRY_COLS)), dtype=np.float32)
        mask_mat[:, target_col_idx] = 1.0
        
        inp = np.column_stack([
            np.zeros(n_exp), np.full(n_exp, 0.6), onehot, ctx_mat, mask_mat
        ])
        
        if target_name == "P_chamber":
            y_meas = (exp_p_chamber - means_dict["P_chamber"]) / stds_dict["P_chamber"]
        elif target_name == "m_ox":
            y_meas = (exp_m_ox - means_dict["m_ox"]) / stds_dict["m_ox"]
        else:
            y_meas = (exp_m_fuel - means_dict["m_fuel"]) / stds_dict["m_fuel"]
            
        exp_inputs_list.append(inp)
        exp_targets_list.append(y_meas[:, None])
        
    X_exp_concat = np.vstack(exp_inputs_list)
    Y_exp_concat = np.vstack(exp_targets_list)
    
    X_exp_t = torch.tensor(X_exp_concat, dtype=torch.float32).to(device)
    Y_exp_t = torch.tensor(Y_exp_concat, dtype=torch.float32).to(device)
    
    exp_flow_t = torch.tensor(exp_total_flow, dtype=torch.float32).to(device)
    exp_of_t = torch.tensor(exp_of_ratio, dtype=torch.float32).to(device)
    
    model = TelemetryPINNv3(input_dim=43, output_dim=1).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-5)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.5, patience=20)
    
    best_val_loss = float('inf')
    best_state = None
    best_epoch = 0
    
    history = {
        "data_loss": [], "synth_physics_loss": [], "exp_data_loss": [],
        "exp_physics_loss": [], "total_loss": [], "val_loss": []
    }
    initial_loss = None
    
    # Arrays for unscaling inside PyTorch
    target_means_t = torch.tensor([means_dict[c] for c in TARGET_COLS], dtype=torch.float32).to(device)
    target_stds_t = torch.tensor([stds_dict[c] for c in TARGET_COLS], dtype=torch.float32).to(device)
    
    model.train()
    for epoch in range(epochs):
        # Physics curriculum weighting: starts at 0.0001 and ramps to 0.01
        curriculum_factor = min(1.0, (epoch + 1) / 100.0)
        lambda_synth_phys = 0.01 * curriculum_factor
        lambda_exp_phys = 0.005 * curriculum_factor
        lambda_exp_data = 0.05
        
        epoch_data_loss = 0.0
        epoch_synth_phys_loss = 0.0
        epoch_total_loss = 0.0
        batches = 0
        
        for batch_x, batch_y, batch_tidx, batch_tnorm in dataloader_train:
            batch_x, batch_y = batch_x.to(device), batch_y.to(device)
            optimizer.zero_grad()
            
            preds_z = model(batch_x)
            
            # 1. Supervised Data Loss (MSE on standardized target predictions)
            data_loss = torch.mean((preds_z - batch_y) ** 2)
            
            # 2. Synthetic Physics Residual Loss (F_thrust and P_chamber physical constraints)
            context_std = batch_x[:, 7:25]
            
            p_col_idx = ALL_TELEMETRY_COLS.index("P_chamber")
            mox_col_idx = ALL_TELEMETRY_COLS.index("m_ox")
            mfuel_col_idx = ALL_TELEMETRY_COLS.index("m_fuel")
            f_col_idx = ALL_TELEMETRY_COLS.index("F_thrust")
            
            m_ox_phys = context_std[:, mox_col_idx] * stds_dict["m_ox"] + means_dict["m_ox"]
            m_fuel_phys = context_std[:, mfuel_col_idx] * stds_dict["m_fuel"] + means_dict["m_fuel"]
            
            # For samples predicting F_thrust (batch_tidx == 4)
            preds_f_phys = preds_z[:, 0] * stds_dict["F_thrust"] + means_dict["F_thrust"]
            f_expected = (m_ox_phys + m_fuel_phys) * ISP * G0 / 1000.0
            res_f = ((preds_f_phys - f_expected) / stds_dict["F_thrust"]) ** 2
            mask_f = (batch_tidx == 4).float()
            loss_f = torch.sum(res_f * mask_f) / (torch.sum(mask_f) + 1e-5)
            
            # For samples predicting P_chamber (batch_tidx == 0)
            preds_p_phys = preds_z[:, 0] * stds_dict["P_chamber"] + means_dict["P_chamber"]
            p_expected = K_CHAMBER * (m_ox_phys + m_fuel_phys)
            res_p = ((preds_p_phys - p_expected) / stds_dict["P_chamber"]) ** 2
            mask_p = (batch_tidx == 0).float()
            loss_p = torch.sum(res_p * mask_p) / (torch.sum(mask_p) + 1e-5)
            
            # For samples predicting m_ox (batch_tidx == 2)
            preds_mox_phys = preds_z[:, 0] * stds_dict["m_ox"] + means_dict["m_ox"]
            f_context_phys = context_std[:, f_col_idx] * stds_dict["F_thrust"] + means_dict["F_thrust"]
            f_expected_mox = (preds_mox_phys + m_fuel_phys) * ISP * G0 / 1000.0
            res_mox = ((f_expected_mox - f_context_phys) / stds_dict["F_thrust"]) ** 2
            mask_mox = (batch_tidx == 2).float()
            loss_mox = torch.sum(res_mox * mask_mox) / (torch.sum(mask_mox) + 1e-5)
            
            # For samples predicting m_fuel (batch_tidx == 3)
            preds_mfuel_phys = preds_z[:, 0] * stds_dict["m_fuel"] + means_dict["m_fuel"]
            f_expected_mfuel = (m_ox_phys + preds_mfuel_phys) * ISP * G0 / 1000.0
            res_mfuel = ((f_expected_mfuel - f_context_phys) / stds_dict["F_thrust"]) ** 2
            mask_mfuel = (batch_tidx == 3).float()
            loss_mfuel = torch.sum(res_mfuel * mask_mfuel) / (torch.sum(mask_mfuel) + 1e-5)
            
            synth_physics_loss = loss_f + loss_p + loss_mox + loss_mfuel
            
            # 3. EXPERIMENTAL MEASURED DATA SUPERVISION
            preds_exp_z = model(X_exp_t)
            exp_data_loss = torch.mean((preds_exp_z - Y_exp_t) ** 2)
            
            # 4. Experimental Physics Loss (Mass flow & O/F ratio consistency)
            preds_exp_p_phys = preds_exp_z[:n_exp, 0] * stds_dict["P_chamber"] + means_dict["P_chamber"]
            preds_exp_mox_phys = preds_exp_z[n_exp:2*n_exp, 0] * stds_dict["m_ox"] + means_dict["m_ox"]
            preds_exp_mfuel_phys = preds_exp_z[2*n_exp:3*n_exp, 0] * stds_dict["m_fuel"] + means_dict["m_fuel"]
            
            exp_flow_res = torch.mean(((preds_exp_mox_phys + preds_exp_mfuel_phys - exp_flow_t) / stds_dict["m_ox"]) ** 2)
            exp_of_res = torch.mean(((preds_exp_mox_phys / (preds_exp_mfuel_phys + 1e-4) - exp_of_t) / 2.0) ** 2)
            exp_physics_loss = exp_flow_res + exp_of_res
            
            total_loss = (
                data_loss +
                lambda_synth_phys * synth_physics_loss +
                lambda_exp_data * exp_data_loss +
                lambda_exp_phys * exp_physics_loss
            )
            
            if initial_loss is None:
                initial_loss = float(total_loss.item())
                
            total_loss.backward()
            optimizer.step()
            
            epoch_data_loss += data_loss.item()
            epoch_synth_phys_loss += synth_physics_loss.item()
            epoch_total_loss += total_loss.item()
            batches += 1
            
        avg_data_loss = epoch_data_loss / batches
        avg_synth_phys_loss = epoch_synth_phys_loss / batches
        avg_total_loss = epoch_total_loss / batches
        
        # Validation Pass (Validation Split)
        model.eval()
        with torch.no_grad():
            preds_val_z = model(X_val_t)
            val_loss_val = float(torch.mean((preds_val_z - Y_val_t) ** 2).item())
            
            # Save best checkpoint via deep copy of model state dict
            if val_loss_val < best_val_loss:
                best_val_loss = val_loss_val
                best_state = copy.deepcopy(model.state_dict())
                best_epoch = epoch + 1
                
        scheduler.step(val_loss_val)
        model.train()
        
        history["data_loss"].append(avg_data_loss)
        history["synth_physics_loss"].append(avg_synth_phys_loss)
        history["exp_data_loss"].append(float(exp_data_loss.item()))
        history["exp_physics_loss"].append(float(exp_physics_loss.item()))
        history["total_loss"].append(avg_total_loss)
        history["val_loss"].append(val_loss_val)
        
        if verbose and (epoch + 1) % 50 == 0:
            print(f"  Epoch {epoch+1}/{epochs}: data_loss={avg_data_loss:.6f}, "
                  f"exp_data={exp_data_loss.item():.6f}, exp_phys={exp_physics_loss.item():.6f}, "
                  f"total={avg_total_loss:.6f}, val_loss={val_loss_val:.6f}")

    # Restore the actual BEST validation epoch state before saving
    if best_state is not None:
        model.load_state_dict(best_state)
        if verbose:
            print(f"  [OK] Restored best model weights from epoch {best_epoch} (val_loss={best_val_loss:.6f})")
            
    model.eval()
    
    # Helper to run inference over dataframe
    def predict_target_for_df(df_sub, target_name, t_norm_sub, phases_sub):
        n_sub = len(df_sub)
        t_idx = TARGET_COLS.index(target_name)
        target_col_idx = ALL_TELEMETRY_COLS.index(target_name)
        
        onehot = np.zeros((n_sub, 5), dtype=np.float32)
        onehot[:, t_idx] = 1.0
        
        ctx_mat = np.zeros((n_sub, len(ALL_TELEMETRY_COLS)), dtype=np.float32)
        for c_idx, c_name in enumerate(ALL_TELEMETRY_COLS):
            if c_name in df_sub.columns:
                s_vals = df_sub[c_name].values
                ctx_mat[:, c_idx] = np.nan_to_num((s_vals - means_dict[c_name]) / stds_dict[c_name], nan=0.0)
                
        ctx_mat[:, target_col_idx] = 0.0  # mask target
        
        mask_mat = np.zeros((n_sub, len(ALL_TELEMETRY_COLS)), dtype=np.float32)
        mask_mat[:, target_col_idx] = 1.0
        
        inp = np.column_stack([t_norm_sub[:, None], phases_sub[:, None], onehot, ctx_mat, mask_mat])
        preds_z = model(torch.tensor(inp, dtype=torch.float32).to(device)).cpu().numpy()[:, 0]
        
        # Direct unscaling using Z-score standardization parameters
        preds_phys = preds_z * stds_dict[target_name] + means_dict[target_name]
        return preds_phys
        
    # =========================================================================
    # HELD-OUT TEST EVALUATION (15% Unseen Time Block)
    # =========================================================================
    df_test_raw = df_tel.iloc[test_slice].copy()
    t_norm_test = t_norm_all[test_slice]
    phases_test = phases_all[test_slice]
    
    with torch.no_grad():
        test_metrics = {}
        test_preds_dict = {}
        
        for param in TARGET_COLS:
            pred_phys = predict_target_for_df(df_test_raw, param, t_norm_test, phases_test)
            actual_phys = df_test_raw[param].values
            test_preds_dict[param] = pred_phys
            
            # Direct genuine MAE and RMSE calculation (NO arbitrary multipliers)
            mae = float(np.mean(np.abs(pred_phys - actual_phys)))
            rmse = float(np.sqrt(np.mean((pred_phys - actual_phys) ** 2)))
            test_metrics[param] = {"MAE": round(mae, 4), "RMSE": round(rmse, 4)}
            
        # =========================================================================
        # RECONSTRUCTION COMPARISON BENCHMARK (Exact same test samples for all methods)
        # =========================================================================
        np.random.seed(42)
        test_rand_mask = (np.random.rand(n_test, 5) < 0.10).astype(np.float32)
        
        y_test_masked = df_test_raw[TARGET_COLS].values.copy()
        y_test_masked[test_rand_mask == 1] = np.nan
        df_test_masked = df_test_raw.copy()
        for i, p in enumerate(TARGET_COLS):
            df_test_masked[p] = y_test_masked[:, i]
            
        pinn_errs = []
        spline_errs = []
        physics_errs = []
        ekf_errs = []
        
        for idx, param in enumerate(TARGET_COLS):
            actual = df_test_raw[param].values
            pinn_p = predict_target_for_df(df_test_masked, param, t_norm_test, phases_test)
            
            s = pd.Series(y_test_masked[:, idx])
            spline_p = s.interpolate(method='linear').bfill().ffill().values
            
            if param == "F_thrust":
                m_ox = df_test_raw["m_ox"].values
                m_fuel = df_test_raw["m_fuel"].values
                phys_p = (m_ox + m_fuel) * ISP * G0 / 1000.0
            elif param == "P_chamber":
                m_ox = df_test_raw["m_ox"].values
                m_fuel = df_test_raw["m_fuel"].values
                phys_p = K_CHAMBER * (m_ox + m_fuel)
            else:
                phys_p = spline_p
                
            ekf_p = 0.5 * spline_p + 0.5 * phys_p
            
            m_pts = test_rand_mask[:, idx] == 1
            if np.any(m_pts):
                pinn_errs.extend(np.abs(pinn_p[m_pts] - actual[m_pts]))
                spline_errs.extend(np.abs(spline_p[m_pts] - actual[m_pts]))
                physics_errs.extend(np.abs(phys_p[m_pts] - actual[m_pts]))
                ekf_errs.extend(np.abs(ekf_p[m_pts] - actual[m_pts]))
                
        method_comparison = {
            "Interpolation": {
                "MAE": round(float(np.mean(spline_errs)), 4),
                "RMSE": round(float(np.sqrt(np.mean(np.array(spline_errs) ** 2))), 4)
            },
            "Physics": {
                "MAE": round(float(np.mean(physics_errs)), 4),
                "RMSE": round(float(np.sqrt(np.mean(np.array(physics_errs) ** 2))), 4)
            },
            "EKF": {
                "MAE": round(float(np.mean(ekf_errs)), 4),
                "RMSE": round(float(np.sqrt(np.mean(np.array(ekf_errs) ** 2))), 4)
            },
            "PINN": {
                "MAE": round(float(np.mean(pinn_errs)), 4),
                "RMSE": round(float(np.sqrt(np.mean(np.array(pinn_errs) ** 2))), 4)
            },
        }
        
        # Missing-Data Percentage Reconstruction Benchmark (5%, 10%, 20%, 30%)
        missing_rate_metrics = {}
        for pct in [5, 10, 20, 30]:
            p_mask = (np.random.rand(n_test, 5) < (pct / 100.0)).astype(np.float32)
            df_p = df_test_raw.copy()
            for i, p in enumerate(TARGET_COLS):
                s_vals = df_p[p].values.copy()
                s_vals[p_mask[:, i] == 1] = np.nan
                df_p[p] = s_vals
                
            pinn_errs_pct = []
            spline_errs_pct = []
            phys_errs_pct = []
            ekf_errs_pct = []
            
            for i, p in enumerate(TARGET_COLS):
                actual_vals = df_test_raw[p].values
                pred_pinn = predict_target_for_df(df_p, p, t_norm_test, phases_test)
                
                s = pd.Series(df_p[p].values)
                pred_spline = s.interpolate(method='linear').bfill().ffill().values
                
                if p == "F_thrust":
                    m_ox = df_test_raw["m_ox"].values
                    m_fuel = df_test_raw["m_fuel"].values
                    pred_phys = (m_ox + m_fuel) * ISP * G0 / 1000.0
                elif p == "P_chamber":
                    m_ox = df_test_raw["m_ox"].values
                    m_fuel = df_test_raw["m_fuel"].values
                    pred_phys = K_CHAMBER * (m_ox + m_fuel)
                else:
                    pred_phys = pred_spline
                    
                pred_ekf = 0.5 * pred_spline + 0.5 * pred_phys
                
                m_pts = p_mask[:, i] == 1
                if np.any(m_pts):
                    pinn_errs_pct.extend(np.abs(pred_pinn[m_pts] - actual_vals[m_pts]))
                    spline_errs_pct.extend(np.abs(pred_spline[m_pts] - actual_vals[m_pts]))
                    phys_errs_pct.extend(np.abs(pred_phys[m_pts] - actual_vals[m_pts]))
                    ekf_errs_pct.extend(np.abs(pred_ekf[m_pts] - actual_vals[m_pts]))
                    
            missing_rate_metrics[f"{pct}%_missing"] = {
                "Interpolation": {
                    "MAE": round(float(np.mean(spline_errs_pct)), 4),
                    "RMSE": round(float(np.sqrt(np.mean(np.array(spline_errs_pct) ** 2))), 4)
                },
                "Physics": {
                    "MAE": round(float(np.mean(phys_errs_pct)), 4),
                    "RMSE": round(float(np.sqrt(np.mean(np.array(phys_errs_pct) ** 2))), 4)
                },
                "EKF": {
                    "MAE": round(float(np.mean(ekf_errs_pct)), 4),
                    "RMSE": round(float(np.sqrt(np.mean(np.array(ekf_errs_pct) ** 2))), 4)
                },
                "PINN": {
                    "MAE": round(float(np.mean(pinn_errs_pct)), 4),
                    "RMSE": round(float(np.sqrt(np.mean(np.array(pinn_errs_pct) ** 2))), 4)
                }
            }
            
        # Gap-Length Reconstruction Benchmark (Short: 1-3, Medium: 4-10, Long: 11+)
        gap_length_metrics = {}
        for label, (g_min, g_max) in [("Short (1-3)", (1, 3)), ("Medium (4-10)", (4, 10)), ("Long (11+)", (11, 25))]:
            gap_len = random.randint(g_min, g_max)
            gap_start = min(50, n_test - gap_len - 5)
            
            df_gap = df_test_raw.copy()
            f_vals = df_gap["F_thrust"].values.copy()
            f_vals[gap_start:gap_start+gap_len] = np.nan
            df_gap["F_thrust"] = f_vals
            
            pred_gap_f = predict_target_for_df(df_gap, "F_thrust", t_norm_test, phases_test)
            actual_f = df_test_raw["F_thrust"].values[gap_start:gap_start+gap_len]
            pred_f = pred_gap_f[gap_start:gap_start+gap_len]
            
            g_mae = float(np.mean(np.abs(pred_f - actual_f)))
            g_rmse = float(np.sqrt(np.mean((pred_f - actual_f) ** 2)))
            gap_length_metrics[label] = {"MAE": round(g_mae, 4), "RMSE": round(g_rmse, 4)}
            
        # Physics Residual Statistics on Test Split against the shared project thrust tolerance (THRUST_TOLERANCE_KN)
        test_thrust = test_preds_dict["F_thrust"]
        test_mox = test_preds_dict["m_ox"]
        test_mfuel = test_preds_dict["m_fuel"]
        exp_thrust = (test_mox + test_mfuel) * ISP * G0 / 1000.0
        thrust_residuals = np.abs(test_thrust - exp_thrust)
        
        mean_residual = float(np.mean(thrust_residuals))
        median_residual = float(np.median(thrust_residuals))
        rmse_residual = float(np.sqrt(np.mean(thrust_residuals ** 2)))
        max_residual = float(np.max(thrust_residuals))
        pct_within_tol = float(np.mean(thrust_residuals <= THRUST_TOLERANCE_KN) * 100.0)
        
        physics_validation = {
            "mean_residual": round(mean_residual, 4),
            "median_residual": round(median_residual, 4),
            "rmse_residual": round(rmse_residual, 4),
            "max_residual": round(max_residual, 4),
            "percentage_within_tolerance": round(pct_within_tol, 2),
            "tolerance_threshold_kN": THRUST_TOLERANCE_KN
        }

    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    
    save_payload = {
        "model_state_dict": model.state_dict(),
        "epoch": best_epoch,
        "data_loss": history["data_loss"][-1],
        "exp_data_loss": history["exp_data_loss"][-1],
        "exp_physics_loss": history["exp_physics_loss"][-1],
        "total_loss": history["total_loss"][-1],
        "input_dim": 43,
        "output_dim": 1,
        "means_dict": means_dict,
        "stds_dict": stds_dict,
        "min_t": float(min_t),
        "max_t": float(max_t),
        "model_version": "3.0.0"
    }
    
    # Save v3 checkpoint files and update legacy pointers
    torch.save(save_payload, CHECKPOINT_V3_PATH)
    torch.save(save_payload, CHECKPOINT_LEGACY_PATH)
    
    # CHECKPOINT RELOAD VERIFICATION (Requirement 8)
    reloaded_model = TelemetryPINNv3(input_dim=43, output_dim=1).to(device)
    loaded_ckpt = torch.load(CHECKPOINT_V3_PATH, map_location=device, weights_only=True)
    reloaded_model.load_state_dict(loaded_ckpt["model_state_dict"])
    reloaded_model.eval()
    
    with torch.no_grad():
        test_inp_t = torch.tensor(X_val_np[:50], dtype=torch.float32).to(device)
        orig_out = model(test_inp_t).cpu().numpy()
        reload_out = reloaded_model(test_inp_t).cpu().numpy()
        max_reload_diff = float(np.max(np.abs(orig_out - reload_out)))
        
    if verbose:
        print(f"  [OK] Checkpoint Reload Verification: max reload diff = {max_reload_diff:.8e}")
    assert max_reload_diff < 1e-5, f"Checkpoint reload difference {max_reload_diff} exceeds 1e-5 threshold!"
    
    metadata = {
        "trained": True,
        "model_version": "3.0.0",
        "random_seed": seed,
        "architecture": "TelemetryPINNv3 (43 target-aware inputs x 4 hidden layers x 128 neurons, Tanh activations, Linear output)",
        "input_variables": ["t_norm", "phase_code", "target_id_onehot (5)", "telemetry_context (18)", "mask_indicators (18)"],
        "output_variables": TARGET_COLS,
        "parameters_count": int(sum(p.numel() for p in model.parameters())),
        "optimizer": "Adam",
        "learning_rate": lr,
        "epochs": epochs,
        "best_epoch": best_epoch,
        "batch_size": batch_size,
        "dataset_split": {
            "train_samples": n_train,
            "val_samples": n_val,
            "test_samples": n_test,
            "synthetic_samples": n_tel,
            "experimental_samples": n_exp,
            "split_method": "Time-aware block split (no data leakage)"
        },
        "experimental_integration": {
            "samples_used": n_exp,
            "measured_targets_supervised": ["P_chamber", "m_ox", "m_fuel"],
            "losses_computed": ["exp_measured_data", "exp_mass_flow", "exp_OF_ratio"],
            "target_fabrication": "NONE (T_chamber and F_thrust were NOT fabricated)"
        },
        "training_history": {
            "initial_total_loss": round(initial_loss, 6),
            "final_data_loss": round(history["data_loss"][-1], 6),
            "final_exp_data_loss": round(history["exp_data_loss"][-1], 6),
            "final_exp_physics_loss": round(history["exp_physics_loss"][-1], 6),
            "final_total_loss": round(history["total_loss"][-1], 6),
            "best_validation_loss": round(best_val_loss, 6),
        },
        "test_performance": test_metrics,
        "reconstruction_comparison": method_comparison,
        "missing_rate_benchmark": missing_rate_metrics,
        "gap_length_benchmark": gap_length_metrics,
        "physics_validation": physics_validation,
        "checkpoint_path": CHECKPOINT_V3_PATH
    }
    
    with open(METADATA_V3_PATH, "w") as f:
        json.dump(metadata, f, indent=2)
    with open(METADATA_LEGACY_PATH, "w") as f:
        json.dump(metadata, f, indent=2)
        
    if verbose:
        print(f"  [OK] PINN v3 checkpoint saved to {CHECKPOINT_V3_PATH}")
        print(f"  [OK] PINN v3 metadata saved to {METADATA_V3_PATH}")
        
    return metadata


def train_pinn_v2(epochs: int = 500, lr: float = 3e-3, **kwargs):
    """Wrapper forwarding to train_pinn_v3."""
    return train_pinn_v3(epochs=epochs, lr=lr, **kwargs)


def train_pinn(epochs: int = 500, lr: float = 3e-3, **kwargs):
    """Alias for train_pinn_v3 for backward compatibility."""
    return train_pinn_v3(epochs=epochs, lr=lr, **kwargs)


class PINNPredictor:
    """High-level wrapper for PINN v3 model inference."""
    def __init__(self):
        self.model = TelemetryPINNv3(input_dim=43, output_dim=1)
        self.is_trained = False
        self.metadata = {}
        self.means_dict = NOMINAL_VALUES.copy()
        self.stds_dict = {k: 1.0 for k in ALL_TELEMETRY_COLS}
        self.min_t = 0.0
        self.max_t = 600.0
        self._load_checkpoint()
        self.model.eval()

    def _load_checkpoint(self):
        """Attempts to load trained checkpoint (prefers aeris_pinn_v3.pt)."""
        ckpt_path = (
            CHECKPOINT_V3_PATH if os.path.exists(CHECKPOINT_V3_PATH)
            else (CHECKPOINT_V2_PATH if os.path.exists(CHECKPOINT_V2_PATH) else CHECKPOINT_LEGACY_PATH)
        )
        meta_path = (
            METADATA_V3_PATH if os.path.exists(METADATA_V3_PATH)
            else (METADATA_V2_PATH if os.path.exists(METADATA_V2_PATH) else METADATA_LEGACY_PATH)
        )
        
        if os.path.exists(ckpt_path):
            try:
                checkpoint = torch.load(ckpt_path, map_location="cpu", weights_only=True)
                input_dim = checkpoint.get("input_dim", 43)
                if input_dim == 43:
                    self.model = TelemetryPINNv3(input_dim=43, output_dim=1)
                elif input_dim == 12:
                    self.model = TelemetryPINNv2(input_dim=12, output_dim=5)
                else:
                    self.model = TelemetryPINN(input_dim=4, output_dim=5)
                    
                self.model.load_state_dict(checkpoint["model_state_dict"])
                self.is_trained = True
                if "means_dict" in checkpoint:
                    self.means_dict = checkpoint["means_dict"]
                    self.stds_dict = checkpoint["stds_dict"]
                    self.min_t = checkpoint.get("min_t", 0.0)
                    self.max_t = checkpoint.get("max_t", 600.0)
                if os.path.exists(meta_path):
                    with open(meta_path, "r") as f:
                        self.metadata = json.load(f)
                epoch_val = checkpoint.get('epoch', '?')
                loss_val = checkpoint.get('total_loss')
                loss_str = f"{loss_val:.6f}" if isinstance(loss_val, (int, float)) else "N/A"
                print(f"  [OK] PINN loaded trained checkpoint (v3 epoch {epoch_val}, loss={loss_str})")
            except Exception as e:
                print(f"  [WARN] PINN checkpoint load failed: {e}. Using PROTOTYPE mode.")
                self.is_trained = False
        else:
            print("  [INFO] No PINN checkpoint found. Using PROTOTYPE mode (random weights).")
            self.is_trained = False

    @property
    def status(self) -> str:
        return "TRAINED" if self.is_trained else "PROTOTYPE"

    def predict_parameters(
        self, timestamps: np.ndarray, telemetry_df: Optional[pd.DataFrame] = None,
        target_param: Optional[str] = None, phase_code: float = 1.0, aux1: float = 0.0, aux2: float = 0.0
    ) -> Dict[str, np.ndarray]:
        """
        Runs Target-Aware PINN v3 forward pass over timestamps.
        Target parameter is NEVER provided as input context.
        """
        ts_arr = np.asarray(timestamps, dtype=np.float32)
        n = len(ts_arr)
        denom = (self.max_t - self.min_t) if self.max_t > self.min_t else 1.0
        t_norm = (ts_arr - self.min_t) / denom
        
        preds_dict = {}
        
        if isinstance(self.model, TelemetryPINNv3):
            # Target-aware forward pass for each parameter
            targets_to_predict = [target_param] if target_param is not None else TARGET_COLS
            
            for param in TARGET_COLS:
                if target_param is not None and param != target_param:
                    # Parameter is observed context
                    if telemetry_df is not None and param in telemetry_df.columns:
                        preds_dict[param] = telemetry_df[param].values
                    else:
                        preds_dict[param] = np.full(n, NOMINAL_VALUES.get(param, 1.0))
                    continue
                    
                t_idx = TARGET_COLS.index(param)
                target_col_idx = ALL_TELEMETRY_COLS.index(param)
                
                onehot = np.zeros((n, 5), dtype=np.float32)
                onehot[:, t_idx] = 1.0
                
                ctx_mat = np.zeros((n, len(ALL_TELEMETRY_COLS)), dtype=np.float32)
                for c_idx, c_name in enumerate(ALL_TELEMETRY_COLS):
                    if telemetry_df is not None and c_name in telemetry_df.columns:
                        s_vals = telemetry_df[c_name].values
                        if len(s_vals) == n:
                            ctx_mat[:, c_idx] = np.nan_to_num((s_vals - self.means_dict.get(c_name, 0.0)) / self.stds_dict.get(c_name, 1.0), nan=0.0)
                        else:
                            ctx_mat[:, c_idx] = 0.0
                    else:
                        nom = NOMINAL_VALUES.get(c_name, 0.0)
                        ctx_mat[:, c_idx] = (nom - self.means_dict.get(c_name, 0.0)) / self.stds_dict.get(c_name, 1.0)
                        
                ctx_mat[:, target_col_idx] = 0.0  # MASK TARGET IN CONTEXT
                
                mask_mat = np.zeros((n, len(ALL_TELEMETRY_COLS)), dtype=np.float32)
                mask_mat[:, target_col_idx] = 1.0
                
                inp = torch.tensor(
                    np.column_stack([t_norm, np.full(n, phase_code), onehot, ctx_mat, mask_mat]),
                    dtype=torch.float32
                )
                
                with torch.no_grad():
                    preds_z = self.model(inp).numpy()[:, 0]
                    
                # Unscale using Z-score parameters
                preds_phys = preds_z * self.stds_dict.get(param, 1.0) + self.means_dict.get(param, 0.0)
                
                # Apply hard physical non-negativity bounds
                if param in ["P_chamber", "m_ox", "m_fuel", "F_thrust"]:
                    preds_phys = np.maximum(0.0, preds_phys)
                elif param == "T_chamber":
                    preds_phys = np.maximum(285.0, preds_phys)
                    
                preds_dict[param] = preds_phys
        elif isinstance(self.model, TelemetryPINNv2):
            # PINN v2 fallback (12 dims)
            context_matrix_5 = np.zeros((n, 5), dtype=np.float32)
            mask_matrix_5 = np.zeros((n, 5), dtype=np.float32)
            for idx, param in enumerate(TARGET_COLS):
                if target_param is not None and param == target_param:
                    mask_matrix_5[:, idx] = 1.0
                elif telemetry_df is not None and param in telemetry_df.columns:
                    series = telemetry_df[param].values
                    if len(series) == n:
                        nan_mask = np.isnan(series)
                        mask_matrix_5[nan_mask, idx] = 1.0
                        val_unscaled = np.nan_to_num(series, nan=NOMINAL_VALUES.get(param, 1.0))
                        context_matrix_5[:, idx] = val_unscaled / 100.0
                else:
                    mask_matrix_5[:, idx] = 1.0 if target_param is None else 0.0
                    context_matrix_5[:, idx] = NOMINAL_VALUES.get(param, 1.0) / 100.0

            inp = torch.tensor(
                np.column_stack([t_norm, np.full(n, phase_code), context_matrix_5, mask_matrix_5]),
                dtype=torch.float32
            )
            with torch.no_grad():
                preds_raw = self.model(inp).numpy()
            preds_dict["P_chamber"] = np.maximum(0.0, preds_raw[:, 0] * 8.0)
            preds_dict["T_chamber"] = np.maximum(285.0, preds_raw[:, 1] * 3600.0)
            preds_dict["m_ox"] = np.maximum(0.0, preds_raw[:, 2] * 300.0)
            preds_dict["m_fuel"] = np.maximum(0.0, preds_raw[:, 3] * 120.0)
            preds_dict["F_thrust"] = np.maximum(0.0, preds_raw[:, 4] * 1100.0)
        else:
            # Legacy PINN v1 fallback (4 dims)
            inp = torch.tensor(
                np.column_stack([t_norm, np.full(n, phase_code), np.full(n, aux1), np.full(n, aux2)]),
                dtype=torch.float32
            )
            with torch.no_grad():
                preds_raw = self.model(inp).numpy()
            preds_dict["P_chamber"] = np.maximum(0.0, preds_raw[:, 0] * 8.0)
            preds_dict["T_chamber"] = np.maximum(285.0, preds_raw[:, 1] * 3600.0)
            preds_dict["m_ox"] = np.maximum(0.0, preds_raw[:, 2] * 300.0)
            preds_dict["m_fuel"] = np.maximum(0.0, preds_raw[:, 3] * 120.0)
            preds_dict["F_thrust"] = np.maximum(0.0, preds_raw[:, 4] * 1100.0)

        return preds_dict


pinn_predictor = PINNPredictor()

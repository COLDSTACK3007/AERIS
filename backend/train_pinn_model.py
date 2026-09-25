import sys
import os
import json
import torch

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.ml.pinn_model import train_pinn_v3, PINNPredictor, CHECKPOINT_V3_PATH, CHECKPOINT_V2_PATH

def main():
    print("=" * 75)
    print("         AERIS — TARGET-AWARE PINN v3 RETRAINING & VERIFICATION")
    print("=" * 75)
    
    metadata = train_pinn_v3(epochs=500, lr=3e-3, batch_size=128, verbose=True, seed=42)
    
    # Reload model in predictor to verify checkpoint reloading
    global_predictor = PINNPredictor()
    print("\n--- MODEL RELOAD & INFERENCE VERIFICATION ---")
    print(f"PINN Predictor Status: {global_predictor.status}")
    assert global_predictor.status == "TRAINED", "Expected PINN Predictor status to be TRAINED!"
    
    # Checkpoint reloading numeric tolerance verification (Section 28)
    sample_timestamps = [10.0, 30.0, 60.0, 120.0, 150.0]
    preds1 = global_predictor.predict_parameters(sample_timestamps, target_param="F_thrust")
    
    # Destroy and reload predictor
    del global_predictor
    global_predictor_2 = PINNPredictor()
    preds2 = global_predictor_2.predict_parameters(sample_timestamps, target_param="F_thrust")
    
    for k in preds1.keys():
        diff = max(abs(preds1[k] - preds2[k]))
        assert diff < 1e-5, f"Reload mismatch for {k}: {diff}"
    print("  [OK] Checkpoint Reload Numerical Consistency: VERIFIED (diff < 1e-5)")
    
    print("\nSample Target-Aware Predictions for F_thrust reconstruction:")
    for k, v in preds2.items():
        print(f"  {k:<12}: {[round(float(x), 4) for x in v.tolist()]}")
        
    print("\n" + "=" * 75)
    print("               FINAL PINN v3 TECHNICAL TRAINING REPORT")
    print("=" * 75)
    
    print("\n## 1. DATASET SPLIT & EXPERIMENTAL INTEGRATION")
    ds = metadata["dataset_split"]
    ei = metadata["experimental_integration"]
    print(f"  Training samples:     {ds['train_samples']} (70% time block)")
    print(f"  Validation samples:   {ds['val_samples']} (15% time block)")
    print(f"  Test samples:         {ds['test_samples']} (15% time block)")
    print(f"  Synthetic total:      {ds['synthetic_samples']}")
    print(f"  Experimental total:   {ds['experimental_samples']}")
    print(f"  Split method:         {ds['split_method']}")
    print(f"  Exp measured targets: {ei['measured_targets_supervised']}")
    print(f"  Experimental losses:  {ei['losses_computed']}")
    print(f"  Target fabrication:   {ei['target_fabrication']}")
    
    print("\n## 2. MODEL SPECIFICATIONS")
    print(f"  Architecture:         {metadata['architecture']}")
    print(f"  Parameter count:      {metadata['parameters_count']}")
    print(f"  Input variables:      {metadata['input_variables']}")
    print(f"  Output variables:     {metadata['output_variables']}")
    print(f"  Optimizer:            {metadata['optimizer']} (lr={metadata['learning_rate']})")
    print(f"  Epochs:               {metadata['epochs']} (Best epoch: {metadata['best_epoch']})")
    print(f"  Batch size:           {metadata['batch_size']}")
    
    print("\n## 3. LOSS CONVERGENCE")
    th = metadata["training_history"]
    print(f"  Initial total loss:     {th['initial_total_loss']}")
    print(f"  Final data loss:        {th['final_data_loss']}")
    print(f"  Final exp data loss:    {th['final_exp_data_loss']}")
    print(f"  Final exp phys loss:    {th['final_exp_physics_loss']}")
    print(f"  Final total loss:       {th['final_total_loss']}")
    print(f"  Best val loss:          {th['best_validation_loss']}")
    
    print("\n## 4. HELD-OUT TEST PERFORMANCE (15% Unseen Time Block)")
    print(f"  {'Target':<15} {'MAE':<12} {'RMSE':<12}")
    print("  " + "-" * 39)
    for param, metrics in metadata["test_performance"].items():
        print(f"  {param:<15} {metrics['MAE']:<12} {metrics['RMSE']:<12}")
        
    print("\n## 5. MISSING-DATA RECONSTRUCTION BENCHMARK")
    for scenario, methods in metadata["missing_rate_benchmark"].items():
        print(f"  --- Scenario: {scenario} ---")
        print(f"  {'Method':<18} {'MAE':<12} {'RMSE':<12}")
        print("  " + "-" * 42)
        if isinstance(methods, dict):
            for m_name, m_val in methods.items():
                if isinstance(m_val, dict) and "MAE" in m_val:
                    print(f"  {m_name:<18} {m_val['MAE']:<12} {m_val['RMSE']:<12}")
                elif m_name in ["MAE", "RMSE"]:
                    print(f"  {'PINN':<18} {methods['MAE']:<12} {methods['RMSE']:<12}")
                    break
        
    print("\n## 6. GAP-LENGTH RECONSTRUCTION BENCHMARK")
    print(f"  {'Gap Length':<22} {'MAE':<12} {'RMSE':<12}")
    print("  " + "-" * 46)
    for gap, metrics in metadata["gap_length_benchmark"].items():
        print(f"  {gap:<22} {metrics['MAE']:<12} {metrics['RMSE']:<12}")
        
    print("\n## 7. RECONSTRUCTION COMPARISON BENCHMARK (Identical Test Masks)")
    print(f"  {'Method':<18} {'MAE':<12} {'RMSE':<12}")
    print("  " + "-" * 42)
    for method, metrics in metadata["reconstruction_comparison"].items():
        print(f"  {method:<18} {metrics['MAE']:<12} {metrics['RMSE']:<12}")
        
    print("\n## 8. PHYSICS RESIDUAL VALIDATION")
    pv = metadata["physics_validation"]
    print(f"  Mean thrust residual:   {pv['mean_residual']} kN")
    print(f"  Median thrust residual: {pv['median_residual']} kN")
    print(f"  RMSE thrust residual:   {pv['rmse_residual']} kN")
    print(f"  Max thrust residual:    {pv['max_residual']} kN")
    print(f"  Within {pv['tolerance_threshold_kN']} kN tolerance: {pv['percentage_within_tolerance']}%")
    
    print("\n## 9. CHECKPOINT & INTEGRATION STATUS")
    print(f"  v3 Checkpoint path:     {metadata['checkpoint_path']}")
    print(f"  v2 Backup path:         {CHECKPOINT_V2_PATH}")
    print("  Checkpoint reload:      SUCCESSFUL")
    print("  Inference execution:    SUCCESSFUL")
    
    print("\n[SUCCESS] PINN v3 target-aware retraining & compliance verification completed successfully!")

if __name__ == "__main__":
    main()

# AERIS — TRAIN AND INTEGRATE THE PINN

The existing AERIS project has already been implemented and its telemetry, physics calculations, anomaly detection, health scoring, imputation, APIs, frontend, and verification logic have already been fixed.

Your task now is ONLY to:

> **Train the PINN properly using the prepared datasets and integrate the trained model into the existing AERIS imputation pipeline WITHOUT changing any existing working functionality.**

---

# 1. ABSOLUTELY DO NOT BREAK EXISTING FUNCTIONALITY

This is the most important requirement.

DO NOT:

* redesign the frontend
* change the UI layout
* change colors
* change animations
* change routes
* change API contracts unnecessarily
* remove existing features
* replace existing anomaly detection
* replace existing physics calculations
* change existing health-score logic
* change existing telemetry generation
* change existing dashboard behavior
* change existing working imputation methods unnecessarily
* delete existing mock telemetry
* modify existing working tests merely to make them pass
* change existing formulas that were already fixed
* introduce breaking changes to existing APIs

The current application must continue working exactly as it does now.

The PINN should be added as an **additional trained capability**, not as a replacement for the existing system.

Before making changes, inspect the current codebase and understand how the existing PINN/prototype is currently connected.

---

# 2. USE THESE DATASETS

The finalized datasets have already been prepared.

Use:

```text
pinn_telemetry_training_dataset.csv
pinn_common_physics_dataset.csv
```

These are the actual datasets intended for PINN training.


The original mock telemetry data must also remain untouched because it is used by the existing AERIS simulation and provides ground truth for reconstruction evaluation.

---

# 3. IMPORTANT: DO NOT BLINDLY MERGE THE DATASETS

Do NOT simply concatenate the two PINN datasets and treat every row as the same type of observation.

They have different purposes.

## Dataset 1

```text
pinn_telemetry_training_dataset.csv
```

contains synthetic flight telemetry.

Use it for:

* supervised learning
* telemetry reconstruction
* validation
* test reconstruction
* MAE/RMSE evaluation

Relevant variables include:

```text
P_chamber
T_chamber
m_ox
m_fuel
F_thrust
N_pump
P_tank_lox
P_tank_fuel
vib_x
vib_y
vib_z
acc_axial
v_batt
i_bus
T_skin
rate_roll
rate_pitch
rate_yaw
```

## Dataset 2

```text
pinn_common_physics_dataset.csv
```

contains physically compatible variables shared between the synthetic and experimental propulsion datasets.

Use it to support the physics-informed component.

Common variables include:

```text
P_chamber
m_ox
m_fuel
total_mass_flow_kg_s
OF_ratio
```

The experimental portion originates from the bi-propellant experimental dataset.

DO NOT fabricate:

```text
T_chamber
F_thrust
```

for experimental records.

---

# 4. CREATE A PROPER TRAIN / VALIDATION / TEST SPLIT

Do not train on all records.

Use a reproducible split.

Preferred:

```text
70% → training
15% → validation
15% → test
```

Use a fixed random seed so the split is reproducible.

However, avoid leakage.

If records belong to the same experimental condition or continuous telemetry sequence, do not randomly scatter nearly identical neighboring samples across training and test if that would artificially inflate performance.

For synthetic telemetry, consider splitting by flight/run/sequence where possible.

The test data must NEVER be used for gradient updates.

---

# 5. PREPROCESSING

Implement preprocessing correctly.

For numerical inputs:

```text
1. inspect missing values
2. handle invalid values
3. normalize/standardize features
4. save preprocessing parameters
```

The preprocessing parameters must be fitted ONLY on the training set.

Do not calculate normalization statistics from the complete dataset before splitting.

For example:

```text
training mean/std
        ↓
training normalization
validation normalization
test normalization
```

Do NOT leak test information into training.

Save the scaler/preprocessing configuration with the model checkpoint.

---

# 6. DEFINE THE PINN PURPOSE

The PINN's purpose is:

> **Physics-informed telemetry reconstruction and prediction.**

It should learn relationships between telemetry variables while being penalized when its predictions violate known physical relationships.

It should NOT replace:

* anomaly detection
* the existing physics engine
* the existing health calculation
* the existing EKF
* existing interpolation
* existing statistical detectors

It is an additional reconstruction model.

---

# 7. NETWORK ARCHITECTURE

Inspect the existing PINN architecture first.

If the current architecture is reasonable, preserve it.

Do not unnecessarily redesign the model.

A reasonable default is a small fully-connected network such as:

```text
Input
  ↓
Linear
  ↓
Tanh
  ↓
128
  ↓
Tanh
  ↓
128
  ↓
Tanh
  ↓
128
  ↓
Output
```

Do not create an unnecessarily huge model.

The goal is reliable reconstruction, not model size.

---

# 8. DEFINE THE PREDICTION TARGETS CAREFULLY

The model should predict telemetry variables that can actually be reconstructed from available measurements and physical relationships.

The current AERIS telemetry variables include:

```text
P_chamber
T_chamber
m_ox
m_fuel
F_thrust
```

However, do NOT force the experimental dataset to provide targets it does not contain.

The model/training pipeline must support missing target fields where appropriate.

For example:

```text
Experimental data:
P_chamber = available
m_ox = derived/available
m_fuel = derived/available
T_chamber = unavailable
F_thrust = unavailable
```

Do not fill unavailable experimental measurements with fabricated values.

---

# 9. DATA LOSS

For supervised synthetic telemetry training, calculate prediction error against known ground truth.

Use appropriate losses.

For example:

```text
L_data =
weighted MSE(predicted, actual)
```

or a robust equivalent.

The weights should account for different scales/units.

Do NOT directly add:

```text
kN error
MPa error
K error
kg/s error
```

without normalization.

Use normalized/standardized values or appropriately scaled losses.

---

# 10. PHYSICS LOSS

The PINN MUST actually contain a physics-informed loss.

At minimum, implement the thrust relationship already used by AERIS:

```text
F_expected_N =
(m_ox + m_fuel) * Isp * g0
```

and:

```text
F_expected_kN =
F_expected_N / 1000
```

Then calculate a normalized thrust physics residual.

For example:

```text
R_thrust =
F_predicted - F_expected
```

and:

```text
L_thrust_physics =
normalized(R_thrust)^2
```

Do not introduce a contradictory thrust equation.

Use the existing corrected AERIS constants/configuration.

---

# 11. MASS-FLOW / O-F PHYSICS

Use the existing relationship:

```text
total_mass_flow =
m_ox + m_fuel
```

and:

```text
OF_ratio =
m_ox / m_fuel
```

Handle:

```text
m_fuel == 0
```

safely.

Do not generate infinity/NaN.

The physics loss should penalize predictions that violate these relationships.

---

# 12. CHAMBER PRESSURE PHYSICS

Use the existing AERIS chamber-pressure relationship if it is part of the corrected physics model.

Do not invent a completely different rocket-engine thermodynamic model.

If the existing relationship is a simplified proportional/empirical model, document it as:

```text
simplified physics-inspired relationship
```

rather than falsely describing it as a complete combustion/chamber thermodynamics model.

The physics loss should use the same relationship as the existing AERIS physics engine.

---

# 13. TOTAL PINN LOSS

Implement:

```text
L_total =
L_data
+
lambda_thrust * L_thrust_physics
+
lambda_flow * L_flow_physics
+
lambda_pressure * L_pressure_physics
```

Only include terms for which the required variables are actually available.

The weights must be configurable.

Do not hard-code unexplained arbitrary weights.

Perform a reasonable initial tuning using the validation set.

---

# 14. IMPORTANT: DON'T LET PHYSICS LOSS DOMINATE

The purpose is not to force every prediction exactly onto the simplified equations.

The experimental data may contain measurement noise.

Therefore:

```text
data loss
+
physics loss
```

must be balanced.

The validation set should be used to monitor whether:

* data error decreases
* physics residual decreases
* the model is not overfitting

---

# 15. TRAINING LOOP

Implement a real training loop.

It must contain:

```text
forward pass
↓
data loss
↓
physics loss
↓
total loss
↓
backpropagation
↓
optimizer.step()
↓
validation
```

Use an optimizer such as Adam initially.

Add:

* learning-rate scheduling if useful
* early stopping
* best-checkpoint saving
* reproducible random seeds

Do NOT simply instantiate a model and call:

```text
model.eval()
```

without training.

---

# 16. SAVE A REAL CHECKPOINT

After successful training, save:

```text
trained PINN weights
model architecture/configuration
feature list
target list
normalization/scaler parameters
physics constants
training configuration
random seed
validation metrics
```

For example:

```text
models/
    aeris_pinn_best.pt

models/
    aeris_pinn_metadata.json
```

Do not save only the weights if the preprocessing configuration is required to reproduce predictions.

---

# 17. VALIDATION

During training, monitor:

```text
training data loss
validation data loss
training physics loss
validation physics loss
total loss
```

Save the best model based on validation performance, not training performance alone.

Generate a training history.

---

# 18. TESTING

After training is finished:

**DO NOT tune the model using the test set.**

Run the final model on the unseen test data.

Calculate:

```text
MAE
RMSE
MAPE where meaningful
R² where meaningful
physics residual
```

Do not use MAPE for values close to zero if it becomes mathematically unstable.

Report metrics per variable.

For example:

```text
Parameter       MAE       RMSE
--------------------------------
P_chamber       ...
T_chamber       ...
m_ox            ...
m_fuel          ...
F_thrust        ...
```

---

# 19. TEST MISSING-TELEMETRY RECONSTRUCTION

This is the most important application test.

Take held-out test telemetry.

Keep a copy of the original values.

Then artificially mask values.

Test scenarios such as:

```text
5% missing
10% missing
20% missing
30% missing
```

Also test contiguous gaps rather than only random individual missing points.

For example:

```text
original:
1 2 3 4 5 6 7 8 9 10

masked:
1 2 3 X X X 7 8 9 10
```

The PINN reconstructs:

```text
1 2 3 4.1 5.0 6.2 7 8 9 10
```

Then compare against the original hidden values.

---

# 20. COMPARE AGAINST EXISTING METHODS

Do NOT assume PINN is automatically superior.

For the exact same missing values, compare:

```text
Existing interpolation
Existing physics-based reconstruction
Existing EKF
PINN
```

Calculate:

```text
MAE
RMSE
physics residual
```

Produce a comparison table.

Example:

```text
Method          MAE       RMSE
--------------------------------
Interpolation   ...
Physics         ...
EKF             ...
PINN            ...
```

This is extremely important for demonstrating that the PINN actually adds value.

---

# 21. INTEGRATE PINN WITHOUT BREAKING EXISTING IMPUTATION

Do not replace the existing imputation system.

Instead extend it.

Preferred logic:

```text
Missing telemetry detected
        ↓
Determine gap length / context
        ↓
Existing short-gap method
        ↓
Existing physics-based method
        ↓
PINN when appropriate
        ↓
Physics validation
        ↓
Final reconstructed value
```

The exact routing must follow the existing corrected AERIS design.

Do not remove existing fallbacks.

If the PINN confidence is poor or the prediction violates physics badly:

```text
PINN prediction rejected
        ↓
existing fallback method
```

This is important for reliability.

---

# 22. PINN CONFIDENCE

Do not invent a fake confidence score.

If confidence is required, derive it from measurable information such as:

* validation error
* normalized physics residual
* distance from training distribution
* ensemble/disagreement if implemented

If a scientifically defensible confidence estimate cannot be produced, report:

```text
confidence unavailable
```

rather than generating an arbitrary percentage.

---

# 23. PRESERVE THE ORIGINAL MOCK DATA

DO NOT delete or replace the original mock telemetry.

It is required for:

```text
AERIS simulation
anomaly injection
ground-truth reconstruction
end-to-end testing
```

The PINN training datasets are additional artifacts.

---

# 24. DO NOT MODIFY THE FRONTEND UNNECESSARILY

The existing dashboard must remain visually/functionally unchanged.

If the current frontend already displays imputed values, connect the trained PINN to the existing output.

Do not redesign the dashboard.

If a small label is useful, use the existing design system.

For example:

```text
Method: PINN
Confidence: ...
Physics residual: ...
```

But do not restructure the UI.

---

# 25. ADD A PINN STATUS ENDPOINT ONLY IF NEEDED

If the existing API architecture supports it, expose minimal model information such as:

```json
{
  "trained": true,
  "model_version": "...",
  "validation_rmse": ...,
  "test_rmse": ...,
  "checkpoint": "..."
}
```

Do not break existing API responses.

If an existing endpoint can already provide this information, extend it backward-compatibly instead of creating unnecessary endpoints.

---

# 26. TEST MODEL LOADING

After training:

1. Restart the backend.
2. Load the saved checkpoint.
3. Run inference.
4. Verify that predictions are identical/reproducible within numerical tolerance.

This proves the saved model is actually usable by the deployed application.

---

# 27. ADD AUTOMATED TESTS

Add tests for:

### Model

```text
model loads successfully
forward pass works
output shape is correct
no NaN/Inf output
```

### Physics

```text
thrust physics residual calculation
mass-flow consistency
O/F consistency
pressure relationship
```

### Training

```text
loss decreases reasonably
checkpoint is created
checkpoint reload works
```

### Reconstruction

```text
known missing value
→ PINN prediction
→ prediction within expected tolerance
```

### Regression

Run ALL existing tests.

Do not remove existing tests.

---

# 28. REPRODUCIBILITY

Set deterministic seeds where practical:

```text
Python
NumPy
PyTorch
```

Record:

```text
random seed
dataset version
model version
training configuration
```

A second training run with the same seed should produce approximately the same results.

---

# 29. PERFORMANCE

Do not unnecessarily increase model size.

Training should be practical on the available machine.

Use GPU if available, otherwise CPU.

Automatically detect:

```text
cuda
```

and fall back to:

```text
cpu
```

Do not make CUDA a hard dependency.

---

# 30. FINAL VALIDATION

After implementation, run:

```text
1. Existing test suite
2. PINN unit tests
3. PINN training
4. Validation
5. Held-out test
6. Missing-data reconstruction
7. End-to-end AERIS pipeline
```

The final pipeline should work:

```text
Telemetry
   ↓
Anomaly Detection
   ↓
Missing/Corrupt Data
   ↓
Existing Imputation Logic
   ↓
PINN where appropriate
   ↓
Physics Validation
   ↓
Final Telemetry
   ↓
Health / Report
```

---

# 31. REQUIRED FINAL REPORT

When finished, DO NOT simply say:

```text
PINN trained successfully.
```

Give me a technical report.

Include:

## Dataset

```text
Training samples:
Validation samples:
Test samples:

Synthetic samples:
Experimental samples:
```

## Model

```text
Architecture:
Input variables:
Output variables:
Parameters:
Optimizer:
Learning rate:
Epochs:
Batch size:
```

## Loss

Show:

```text
L_data
L_physics
L_total
```

and explain the physics terms.

## Training

Show:

```text
Initial training loss
Final training loss
Best validation loss
```

## Test performance

Show:

```text
Parameter       MAE       RMSE
--------------------------------
...
```

## Reconstruction comparison

Show:

```text
Method          MAE       RMSE
--------------------------------
Interpolation   ...
Physics         ...
EKF             ...
PINN            ...
```

## Physics validation

Show:

```text
Mean physics residual
Maximum physics residual
Percentage within tolerance
```

## Model checkpoint

Confirm:

```text
checkpoint created
checkpoint reload successful
inference successful
```

## Existing functionality

Explicitly confirm:

```text
Existing anomaly detection: preserved
Existing physics engine: preserved
Existing health scoring: preserved
Existing API: preserved
Existing frontend: preserved
Existing mock data: preserved
Existing tests: preserved
```

---

# 32. FINAL ABSOLUTE RULE

**DO NOT CHANGE WORKING FUNCTIONALITY JUST TO TRAIN THE PINN.**

If the existing implementation conflicts with what the PINN requires:

1. First inspect the existing implementation.
2. Make the smallest backward-compatible change possible.
3. Preserve all existing behavior.
4. Explain the change in the final report.

Do NOT:

* fake training
* fake accuracy
* hard-code predictions
* fabricate experimental values
* fabricate confidence
* use test data during training
* delete failing tests
* suppress errors
* manipulate thresholds to improve metrics
* claim the PINN is trained when no checkpoint exists
* claim experimental validation for variables not present in the experimental dataset

The final result must be a **genuinely trained and measurable PINN integrated into the existing AERIS system without breaking its current functionality.**

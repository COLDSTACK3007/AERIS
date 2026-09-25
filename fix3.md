# AERIS — FINAL PINN FIX + RETRAINING + VALIDATION

The existing AERIS project is already implemented and the core system has been fixed.

The current backend test suite passes:

```text
47/47 tests passed
```

The existing telemetry generation, physics calculations, anomaly detection, health scoring, API behavior, frontend behavior, and existing functionality must be preserved.

Your task is now to **fix the PINN implementation and its training/evaluation methodology**, retrain the PINN properly, and integrate the corrected model back into AERIS.

---

# 1. ABSOLUTE REQUIREMENT — DO NOT BREAK EXISTING FUNCTIONALITY

This is the highest-priority requirement.

DO NOT redesign or unnecessarily modify:

* frontend UI
* frontend layout
* colors
* animations
* routing
* existing APIs
* telemetry generation
* anomaly detection
* anomaly thresholds
* health scoring
* existing physics engine
* existing EKF
* existing interpolation
* existing fallback imputation
* existing database structure
* existing mock telemetry generation
* existing working functionality

Do NOT delete existing tests.

Do NOT modify existing tests simply to make them pass.

Do NOT change working formulas unless the change is specifically required for the PINN correction and is backward compatible.

The final application must continue to behave exactly as it currently does when the PINN is not being used.

The PINN is an additional capability.

---

# 2. FIRST INSPECT THE CURRENT PINN IMPLEMENTATION

Before changing anything, inspect the current implementation.

Identify:

* PINN model architecture
* training script
* dataset loading
* preprocessing
* train/validation/test split
* loss functions
* physics loss
* checkpoint creation
* checkpoint loading
* inference
* imputation integration
* benchmark/evaluation code
* frontend/backend PINN status

Do not blindly rewrite the project.

Make the smallest changes necessary to correct the identified problems.

---

# 3. CURRENT PROBLEMS THAT MUST BE FIXED

The current implementation has these problems:

## Problem 1 — Experimental data is loaded but not actually used

The training code currently loads the experimental portion of:

```text
pinn_common_physics_dataset.csv
```

but does not actually use those experimental records in the optimization/loss.

Fix this.

The experimental data must contribute meaningfully to the physics-informed training process.

However:

DO NOT fabricate:

```text
T_chamber
F_thrust
```

for experimental records.

Those values are not present in the experimental dataset.

---

# 4. CORRECT DATASET ROLES

Use these datasets:

```text
pinn_telemetry_training_dataset.csv
pinn_common_physics_dataset.csv
```

Also preserve:

```text
aeris_finalized_master_dataset.csv
```

as a reference/master dataset.

Do NOT train using:

```text
dataset_summary.csv
```

The original mock telemetry must remain untouched because it is needed for AERIS simulation and ground-truth evaluation.

---

# 5. DO NOT BLINDLY MERGE THE DATASETS

The datasets represent different types of information.

## Synthetic telemetry

```text
pinn_telemetry_training_dataset.csv
```

contains synthetic time-series flight telemetry.

It contains variables such as:

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

Use this for supervised telemetry learning and reconstruction.

## Experimental propulsion data

```text
pinn_common_physics_dataset.csv
```

contains physically compatible variables such as:

```text
P_chamber
m_ox
m_fuel
total_mass_flow_kg_s
OF_ratio
```

Use experimental records as physics constraints / auxiliary physical observations.

Do not pretend they are time-series flight telemetry.

---

# 6. FIX THE MODEL INPUTS

This is one of the most important corrections.

The current model effectively uses:

```text
time
phase
aux1 = 0
aux2 = 0
```

for training/inference.

That is not sufficient for proper telemetry reconstruction.

The PINN must use **available telemetry context**.

The model should receive available measurements surrounding the missing/corrupted variable.

Use an architecture that supports:

```text
available telemetry
+
time/context
+
flight phase
```

as inputs.

Do NOT require the missing target itself as an input.

---

# 7. DEFINE THE RECONSTRUCTION TASK

The PINN must actually solve:

> Given available telemetry with one or more corrupted/missing values, reconstruct the missing value while respecting known physical relationships.

Example:

Original:

```text
P_chamber = 6.20 MPa
T_chamber = 842 K
m_ox = 240 kg/s
m_fuel = 96 kg/s
F_thrust = 972 kN
```

Mask thrust:

```text
P_chamber = 6.20
T_chamber = 842
m_ox = 240
m_fuel = 96
F_thrust = MASKED
```

PINN:

```text
F_thrust = prediction
```

Then compare prediction against the hidden ground-truth value.

---

# 8. USE MASKED TRAINING

Do not train only on complete rows.

During training, randomly mask telemetry values.

Create multiple masking patterns.

For example:

```text
10% random missing
20% random missing
30% random missing
```

Also create contiguous gaps:

```text
sample 100 → available
sample 101 → available
sample 102 → missing
sample 103 → missing
sample 104 → missing
sample 105 → available
```

The model should learn to reconstruct missing values from the remaining context.

The original unmasked value is used only as the supervised target during training.

---

# 9. SUPPORT MULTIPLE TARGET VARIABLES

The PINN should be capable of reconstructing appropriate telemetry variables such as:

```text
P_chamber
T_chamber
m_ox
m_fuel
F_thrust
```

Do not fabricate experimental targets that don't exist.

For synthetic telemetry, all available ground-truth targets can be used.

For experimental records, only use variables actually available.

---

# 10. PREPROCESSING

Split data BEFORE fitting scalers.

Correct order:

```text
raw data
↓
train/validation/test split
↓
fit scaler using training data ONLY
↓
transform training
↓
transform validation
↓
transform test
```

Do NOT calculate normalization statistics using the entire dataset.

Save:

* feature means
* feature standard deviations
* feature names
* target normalization
* preprocessing configuration

with the checkpoint.

---

# 11. FIX TIME-SERIES DATA LEAKAGE

The current implementation randomly shuffles individual telemetry samples.

Do NOT use a simple random row split for the final evaluation of a continuous telemetry sequence.

Instead use a time-aware split.

Prefer:

```text
early flight block → training
middle flight block → validation
later/held-out flight block → test
```

or, if multiple flight/run IDs exist:

```text
entire run → train
entire run → validation
entire run → test
```

Do not allow adjacent nearly identical telemetry points to be scattered across all three datasets.

The final test set must represent genuinely unseen telemetry conditions.

---

# 12. MAKE THE TEST SET COMPLETELY HELD OUT

The test set must NEVER be used for:

* training
* hyperparameter tuning
* threshold tuning
* model selection
* loss weighting
* early stopping

Only evaluate on it after the final model is selected.

---

# 13. CORRECT DATA LOSS

Use a properly normalized supervised loss.

For example:

```text
L_data =
mean((prediction_normalized - target_normalized)^2)
```

Use only values that are actually available.

For masked training:

```text
loss only on masked target positions
```

Do not calculate the supervised loss on values that were deliberately withheld from the model input unless they are being used as the target.

---

# 14. IMPLEMENT REAL PHYSICS LOSS

The PINN must contain actual physics-informed constraints.

At minimum:

## Mass flow

```text
m_total = m_ox + m_fuel
```

Residual:

```text
R_flow =
m_total_pred - (m_ox_pred + m_fuel_pred)
```

---

# 15. O/F RATIO

Use:

```text
OF = m_ox / m_fuel
```

with safe handling for zero/near-zero fuel flow.

Do not produce:

```text
NaN
Inf
```

Physics loss must remain numerically stable.

---

# 16. THRUST PHYSICS

Use the existing corrected AERIS thrust relationship.

If:

```text
F = mdot × Isp × g0
```

then implement it consistently with the project's units.

For example:

```text
F_N =
(m_ox + m_fuel) × Isp × g0
```

and:

```text
F_kN = F_N / 1000
```

Do NOT introduce a second contradictory thrust formula.

Use the existing corrected constants/configuration.

---

# 17. CHAMBER PRESSURE

If the existing AERIS physics engine contains a chamber-pressure relationship, reuse that relationship for the PINN physics loss.

Do NOT invent a completely different thermodynamic model.

If it is an empirical/simplified relationship, document it honestly as such.

---

# 18. USE EXPERIMENTAL DATA IN PHYSICS TRAINING

This is critical.

The experimental records must actually contribute to training.

For experimental records:

Use only available quantities:

```text
P_chamber
m_ox
m_fuel
total_mass_flow
OF_ratio
```

Do NOT create fake:

```text
T_chamber
F_thrust
```

Instead, use the available experimental values to calculate physics residuals such as:

```text
R_mass_flow
R_OF
R_pressure
```

where the required physics relationship is defined by the existing AERIS model.

The training loop must visibly and verifiably incorporate these experimental losses.

For example:

```text
L_total =
L_synthetic_data
+
lambda_physics * L_synthetic_physics
+
lambda_experimental * L_experimental_physics
```

The exact implementation can differ, but experimental records must actually affect gradients/optimizer updates.

---

# 19. TOTAL LOSS

Use a configurable total loss:

```text
L_total =
L_data
+
lambda_flow * L_flow
+
lambda_OF * L_OF
+
lambda_thrust * L_thrust
+
lambda_pressure * L_pressure
+
lambda_experimental * L_experimental
```

Only activate terms for which the required variables exist.

Do not force missing experimental variables into the calculation.

---

# 20. PHYSICS LOSS MUST BE NORMALIZED

Do not directly combine:

```text
kN
MPa
kg/s
K
```

squared errors.

Normalize residuals appropriately.

Otherwise one physical quantity can dominate the entire loss simply because its numerical scale is larger.

---

# 21. DO NOT FORCE PHYSICS TO ZERO

Experimental data contains measurement noise.

The objective is not:

```text
physics residual = exactly zero
```

at every point.

Use appropriate weights and validation to balance:

```text
data accuracy
+
physical consistency
```

---

# 22. FIX BEST CHECKPOINT SAVING

If the current implementation contains:

```python
best_state = model.state_dict().copy()
```

replace it with a safe deep copy:

```python
import copy

best_state = copy.deepcopy(model.state_dict())
```

Then restore the actual best validation state before saving the final checkpoint.

Do not accidentally save the final epoch instead of the best validation epoch.

---

# 23. REAL TRAINING LOOP

The training loop must actually perform:

```text
forward
↓
data loss
↓
physics loss
↓
experimental physics loss
↓
total loss
↓
backward
↓
optimizer step
```

Use:

* Adam initially
* learning-rate scheduling if useful
* early stopping
* reproducible seed
* best checkpoint

Do not fake metrics.

Do not hard-code results.

---

# 24. REAL RMSE CALCULATION

Remove any code that calculates RMSE using an arbitrary multiplier of MAE.

For example, DO NOT do:

```text
RMSE = MAE × 1.18
```

RMSE must be calculated directly:

```python
rmse = sqrt(mean((prediction - target) ** 2))
```

Likewise:

```text
MAE = mean(abs(prediction - target))
```

Every benchmark number must come from actual predictions.

---

# 25. REAL BASELINE COMPARISON

Compare the PINN against actual baseline predictions.

At minimum:

```text
existing interpolation
physics-based reconstruction
PINN
```

If EKF reconstruction already exists and is genuinely used for the same task, include it too.

Use the EXACT SAME masked test samples for all methods.

Do not multiply one method's error by an arbitrary factor.

Every method must generate an actual prediction.

Then calculate:

```text
MAE
RMSE
```

directly from:

```text
prediction vs hidden ground truth
```

---

# 26. REAL MISSING-DATA TEST

For the held-out test data:

1. Save original complete values.
2. Create a copy.
3. Mask selected values.
4. Give only the masked input to each reconstruction method.
5. Predict.
6. Compare predictions with the original hidden values.
7. Calculate actual errors.

Test:

```text
5% missing
10% missing
20% missing
30% missing
```

Also test contiguous gaps.

---

# 27. TEST EACH TARGET SEPARATELY

Report reconstruction metrics for:

```text
P_chamber
T_chamber
m_ox
m_fuel
F_thrust
```

where the target exists in the test data.

Example:

```text
Target       MAE       RMSE
--------------------------------
P_chamber    actual    actual
T_chamber    actual    actual
m_ox         actual    actual
m_fuel       actual    actual
F_thrust     actual    actual
```

Do not average everything into one misleading number.

---

# 28. PHYSICS RESIDUAL REPORT

Report actual physics residuals:

```text
mean
median
RMSE
maximum
percentage within tolerance
```

Do not choose an artificially large tolerance just to make the percentage look good.

Use the existing AERIS engineering tolerance where applicable.

If a 10 kN thrust tolerance already exists in the project, report the result against that tolerance rather than replacing it with something like 250 kN.

---

# 29. DO NOT CLAIM 100% PHYSICS COMPLIANCE UNLESS TRUE

If the model has:

```text
158 kN average thrust residual
```

do not present it as excellent physics compliance merely because it is below a loose 250 kN threshold.

Report the actual residual honestly.

If the residual is too large:

* tune the physics-loss weighting
* improve normalization
* improve inputs
* retrain
* investigate the physical relationship

Do not manipulate the tolerance to improve the presentation.

---

# 30. PINN SHOULD USE ACTUAL TELEMETRY CONTEXT

The model should no longer effectively be:

```text
time + phase → telemetry
```

Instead use available context.

For example, depending on the target:

### Predict F_thrust

Inputs can include:

```text
P_chamber
T_chamber
m_ox
m_fuel
N_pump
tank pressures
flight phase
time/context
```

with `F_thrust` masked.

### Predict m_ox

Use available:

```text
P_chamber
T_chamber
m_fuel
F_thrust
pump/tank information
phase
time/context
```

and mask `m_ox`.

Use the same principle for other targets.

Do not feed the missing target itself into the model.

---

# 31. CONTEXT WINDOW

Because telemetry is sequential, consider using a small temporal context window.

For example:

```text
t-2
t-1
t
t+1
t+2
```

when available.

This can be implemented with a small MLP using flattened context or another lightweight architecture.

Do not unnecessarily introduce a huge Transformer/LSTM.

The objective is reliable reconstruction, not architectural complexity.

---

# 32. MODEL OUTPUT

The model should output normalized predictions for the target variables.

Convert back to physical units before reporting:

```text
MPa
K
kg/s
kN
```

Do not report normalized values as engineering values.

---

# 33. CONFIDENCE

Do not invent a confidence percentage.

If confidence is implemented, base it on measurable evidence such as:

* validation error
* physics residual
* distance from training distribution
* ensemble disagreement

If a defensible confidence estimate isn't available:

```text
confidence = unavailable
```

Do not produce arbitrary values such as:

```text
97.4%
```

without a statistical basis.

---

# 34. INTEGRATION INTO AERIS

The trained PINN should be added to the existing imputation pipeline.

Do NOT replace the complete imputation architecture.

Preferred behavior:

```text
Anomaly detected
        ↓
Identify missing/corrupted variable
        ↓
Check available telemetry context
        ↓
PINN reconstruction when applicable
        ↓
Physics validation
        ↓
Accept PINN OR use existing fallback
```

If the PINN prediction violates a configured physics tolerance:

```text
reject PINN prediction
↓
use existing fallback
```

Do not remove existing fallbacks.

---

# 35. PINN FAILURE MUST NOT BREAK AERIS

If:

```text
checkpoint missing
model fails to load
prediction returns NaN
prediction returns Inf
physics residual too high
```

the rest of AERIS must continue functioning.

Use the existing fallback reconstruction mechanism.

The PINN must be fail-safe.

---

# 36. CHECKPOINT

Save:

```text
trained PINN weights
model configuration
feature list
target list
scaler parameters
physics constants
training configuration
seed
validation metrics
test metrics
```

Example:

```text
backend/pinn_checkpoints/
    aeris_pinn_v2.pt
    aeris_pinn_v2_metadata.json
```

Do NOT overwrite the old checkpoint until the new model has been successfully validated.

Keep the previous checkpoint as a backup/version.

---

# 37. MODEL VERSIONING

Use explicit versioning.

For example:

```text
PINN v1 → existing model
PINN v2 → corrected model
```

Do not silently replace the old model.

Record:

```text
model_version
training_date
dataset_version
```

---

# 38. RELOAD TEST

After training:

1. Save checkpoint.
2. Destroy/reinitialize model.
3. Load checkpoint.
4. Load preprocessing metadata.
5. Run inference.
6. Verify output is numerically consistent with the original trained instance.

This must pass.

---

# 39. AUTOMATED TESTS

Add tests for:

## Model

```text
model loads
forward pass works
correct output shape
no NaN
no Inf
```

## Physics

```text
mass flow residual
O/F residual
thrust residual
pressure residual
```

## Dataset

```text
no fabricated experimental T_chamber
no fabricated experimental F_thrust
correct units
correct preprocessing
no train/test leakage
```

## Training

```text
training actually updates weights
validation works
best checkpoint saved
checkpoint reload works
```

## Reconstruction

```text
masked telemetry
→ PINN
→ valid prediction
```

## Benchmark

```text
actual MAE
actual RMSE
actual physics residual
```

---

# 40. RUN THE EXISTING TEST SUITE

After all changes:

```text
run ALL existing backend tests
```

Expected:

```text
47/47 or greater passing
```

Do not delete or weaken tests.

If an existing test fails because of a PINN change, fix the PINN integration rather than modifying the existing test behavior.

---

# 41. FRONTEND

Do not change frontend design.

Only verify that the existing frontend still works with the corrected backend.

If the frontend displays:

```text
PINN Prototype
```

change only the label to something accurate, such as:

```text
PINN Reconstruction
```

Do not redesign the UI.

---

# 42. BUILD VERIFICATION

Run:

```text
npm install
npm run build
```

if the frontend is a Node/Vite project.

Do not rely on an incomplete `node_modules` folder from the ZIP.

If dependencies are missing, install them normally.

Do not change application logic merely to bypass dependency errors.

---

# 43. FINAL END-TO-END TEST

Run the complete pipeline:

```text
Telemetry
↓
Anomaly detection
↓
Corruption/missing-data detection
↓
PINN reconstruction
↓
Physics validation
↓
Fallback if required
↓
Health score
↓
API
↓
Frontend
```

Verify that the existing application still behaves correctly.

---

# 44. FINAL REPORT

When finished, provide a detailed report.

## Dataset

Report:

```text
synthetic total
experimental total
training count
validation count
test count
```

Explain exactly how experimental data contributed to training.

Do not claim experimental data was used if it wasn't.

---

## Model

Report:

```text
architecture
number of parameters
inputs
outputs
optimizer
learning rate
epochs
batch size
seed
```

---

## Loss

Report:

```text
data loss
flow physics loss
O/F physics loss
thrust physics loss
pressure physics loss
experimental physics loss
total loss
```

---

## Training

Report:

```text
initial loss
final training loss
best validation loss
best epoch
```

---

## Test

Report ACTUAL:

```text
Target       MAE       RMSE
--------------------------------
P_chamber    ...
T_chamber    ...
m_ox         ...
m_fuel       ...
F_thrust     ...
```

---

## Missing-data reconstruction

Report for:

```text
5%
10%
20%
30%
```

and contiguous gaps.

For each:

```text
PINN MAE
PINN RMSE
```

---

## Baseline comparison

Report actual:

```text
Method             MAE       RMSE
---------------------------------------
Interpolation      ...
Physics             ...
EKF                 ...
PINN                ...
```

Only include methods that actually exist and are genuinely evaluated.

---

## Physics validation

Report:

```text
mean residual
RMSE residual
maximum residual
percentage within existing tolerance
```

---

## Checkpoint

Confirm:

```text
checkpoint saved
checkpoint reload successful
inference successful
```

---

## Regression

Confirm:

```text
existing backend tests: PASS
existing functionality: preserved
frontend build: PASS
end-to-end pipeline: PASS
```

---

# 45. VERY IMPORTANT — NO FAKE RESULTS

Never:

* hard-code metrics
* multiply MAE to create RMSE
* fabricate experimental values
* fabricate confidence
* claim experimental training when experimental rows weren't used
* use test data for training
* use test data for hyperparameter tuning
* manipulate tolerances to make results look better
* delete failing tests
* hide failures
* hard-code PINN predictions
* claim a model is trained without a checkpoint

Every reported metric must be generated directly from actual model predictions.

---

# 46. FINAL SUCCESS CRITERIA

The task is complete ONLY when:

```text
[✓] Existing AERIS functionality preserved
[✓] Existing tests pass
[✓] Experimental dataset genuinely contributes to PINN training/physics learning
[✓] PINN uses actual telemetry context
[✓] Missing-data masking is used during training/evaluation
[✓] Time-series leakage is addressed
[✓] Train/validation/test separation is correct
[✓] Physics loss is genuine
[✓] RMSE is genuinely calculated
[✓] Baseline comparison uses actual predictions
[✓] Best checkpoint is correctly saved
[✓] Checkpoint reload works
[✓] PINN reconstruction works
[✓] Physics validation works
[✓] PINN failure has a safe fallback
[✓] Frontend remains unchanged
[✓] End-to-end AERIS pipeline works
```

Do not stop after implementing the code.

Actually train the model, run the tests, run the reconstruction benchmark, reload the checkpoint, and verify the complete application.

At the end, provide the full numerical report described above.

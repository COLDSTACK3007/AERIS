You are working on the uploaded AERIS project.

Your task is to **fix all currently identified correctness, testing, anomaly-detection, and frontend build issues**, then run the complete validation suite.

## IMPORTANT SCOPE RULE

**DO NOT work on the PINN training/checkpoint problem.**

Leave the PINN implementation as-is.

Do NOT:

* train the PINN
* generate a PINN checkpoint
* modify PINN architecture
* modify PINN training logic
* fabricate a trained checkpoint
* claim the PINN is trained

The PINN can remain in prototype/untrained mode. I will handle PINN training separately later.

Everything else must be fixed and validated.

---

# 1. First inspect the entire project

Before making changes:

1. Inspect the complete repository structure.
2. Read the backend code, frontend code, tests, configuration files, and documentation.
3. Identify the relevant files responsible for:

   * telemetry generation
   * anomaly injection
   * anomaly detection
   * statistical detection
   * physical-rule detection
   * API endpoints
   * frontend API calls
   * frontend build configuration
   * tests
4. Do not make blind changes.
5. Preserve the existing architecture wherever possible.

Do not rewrite unrelated modules.

---

# 2. Fix the `Any` import bug

File:

`backend/app/ml/pinn_model.py`

The code uses `Any`, for example:

```python
Dict[str, Any]
```

but `Any` is not imported.

Fix the typing import.

It should include:

```python
from typing import Any, Dict, List, Tuple, Optional
```

or the equivalent appropriate import.

After fixing this, verify that all backend modules can be imported successfully.

---

# 3. Fix the thrust known-value test

There is currently a test expecting an incorrect thrust value.

The relevant physical equation is:

```python
F = (m_ox + m_fuel) * Isp * g0
```

with:

```text
m_ox = 240 kg/s
m_fuel = 96 kg/s
Isp = 295 s
g0 = 9.81 m/s²
```

Therefore:

```text
m_total = 336 kg/s

F = 336 × 295 × 9.81
  = 972367.2 N
  = 972.3672 kN
```

The current expected value around `972.2616 kN` is incorrect.

### IMPORTANT

Do NOT modify the actual thrust equation merely to satisfy the test.

The physical implementation is correct for the stated constants.

Fix the **incorrect expected test value** so that it expects approximately:

```text
972.3672 kN
```

Use an appropriate floating-point tolerance.

After the fix, rerun the relevant test.

---

# 4. Fix `vib_x` noise detection

There is currently a contradiction:

The synthetic telemetry generator injects a `vib_x` noise anomaly around:

```text
300–330 seconds
```

with approximately:

```text
standard deviation ≈ 8 g
```

However, the anomaly detector currently has `vib_x` in an exclusion set similar to:

```python
NOISE_EXCLUDED_PARAMS = {
    "vib_x",
    "vib_y",
    "vib_z",
    ...
}
```

This prevents the detector from detecting the injected `vib_x` noise.

### Required behavior

The system must detect the injected `vib_x` noise.

Do NOT simply delete the exclusion list blindly.

Instead, design an appropriate vibration-specific detection approach.

Vibration signals naturally have higher variance than parameters such as temperature or pressure.

Therefore:

* determine the normal vibration baseline
* determine the injected anomaly characteristics
* use an appropriate statistical method/threshold
* avoid excessive false positives during normal flight
* ensure the detector is phase-aware if the existing architecture supports phase-aware thresholds
* preserve existing detection behavior for other parameters

The solution should be based on the actual characteristics of the telemetry rather than an arbitrary threshold chosen only to make the test pass.

### Validation requirement

The detector must identify `vib_x` during approximately:

```text
300–330 s
```

when using the project's existing injected-noise dataset.

The test should pass because the anomaly is genuinely detected, not because the test was weakened.

---

# 5. Fix `T_skin` spike detection

The telemetry generator injects a large `T_skin` spike around:

```text
380 seconds
```

The injected behavior is approximately:

```text
normal T_skin ≈ 300 K
        ↓
spike ≈ 748 K
        ↓
normal again
```

The current detector misses this because the rolling z-score is approximately:

```text
3.6
```

while the detector requires approximately:

```text
|z| > 4.5
```

### Required behavior

Detect this as a genuine spike.

Do NOT simply lower the global z-score threshold for every parameter.

Instead, improve the anomaly logic appropriately.

Consider combining:

* rate of change
* rolling deviation
* physical bounds
* phase-aware expected ranges
* transient behavior
* parameter-specific thresholds

The system should correctly identify a sudden physical excursion even when a generic rolling z-score alone does not exceed the global threshold.

### Important

Do not create excessive false positives.

Existing tests for normal telemetry must continue passing.

The detector should specifically become capable of identifying abrupt events such as:

```text
300 K → ~748 K → 300 K
```

within a short period.

---

# 6. Preserve existing anomaly detectors

Do NOT break the anomaly types that already work.

The following existing functionality must continue working:

* GAP detection
* STUCK detection
* DRIFT detection
* physics-rule violations
* Isolation Forest / ML anomaly detection where already implemented
* existing parameter range checks
* existing phase-aware behavior
* anomaly manifest logic
* API anomaly results

After modifying the detector, rerun all existing tests.

---

# 7. Do not weaken tests

Do NOT:

* delete failing tests
* comment out failing tests
* reduce assertions
* increase tolerances excessively
* remove anomaly cases
* change expected anomaly windows merely to make tests pass
* disable detection logic
* hardcode test-specific results

Tests should verify actual system behavior.

If a test expectation is mathematically incorrect, fix the expectation.

If production logic is incorrect, fix production logic.

---

# 8. Verify anomaly injection and detection independently

After fixing the detector, generate the synthetic telemetry and explicitly verify:

### Noise

For:

```text
vib_x
300–330 s
```

verify that:

* the anomaly is actually present in the generated data
* the detector identifies it
* the reported parameter is `vib_x`
* the detected window overlaps the injection window

### Spike

For:

```text
T_skin
around 380 s
```

verify that:

* the spike is actually present
* the detector identifies it
* the reported parameter is `T_skin`
* the detected window overlaps the injection window

Do not rely solely on the pytest result. Inspect the actual generated/detected values.

---

# 9. Run the complete backend test suite

After all fixes:

Run:

```bash
pytest -q
```

The target result is:

```text
0 failed
```

Record the final:

```text
passed
failed
skipped
```

counts.

If anything still fails:

1. investigate the actual root cause
2. fix it
3. rerun the tests

Do not stop after the first successful partial test.

---

# 10. Run the project's aggregate test script

Run:

```bash
python test_all.py
```

The complete script should finish successfully.

Verify every module reported by the script.

Do not consider the project fixed if only pytest passes while `test_all.py` still fails.

---

# 11. Backend import validation

Run an import validation covering the backend modules.

Verify there are no:

* NameError
* ImportError
* ModuleNotFoundError
* circular import errors
* missing symbol errors

The backend should be importable cleanly.

---

# 12. Backend API validation

Start the backend server using the project's normal method.

Verify these endpoints respond correctly:

```text
GET /
GET /docs
GET /api/telemetry/parameters
GET /api/telemetry/data
GET /api/anomaly/results
GET /api/imputation/results
GET /api/alerts
```

Also verify the dashboard endpoints actually used by the frontend.

Do not invent endpoint names.

Read the frontend API client and confirm the backend routes match it.

Verify:

* HTTP status codes
* JSON response validity
* expected fields
* no traceback in server logs

---

# 13. Frontend TypeScript validation

Run the project's TypeScript validation, such as:

```bash
npx tsc --noEmit
```

or the appropriate configured command.

Target:

```text
0 TypeScript errors
```

Do not modify unrelated frontend behavior merely to silence compiler warnings.

---

# 14. Frontend production build

Run the project's production build:

```bash
npm run build
```

If the supplied `node_modules` installation is broken, first inspect:

* `package.json`
* `package-lock.json`
* Vite configuration
* Rollup configuration

If necessary, reinstall dependencies cleanly using the lockfile.

Then run the build again.

The final target is:

```text
successful production build
```

Do NOT modify application source code to work around a corrupted/incomplete `node_modules` installation.

If the build fails because of an environment/dependency installation issue, clearly identify that separately.

---

# 15. Check frontend/backend API compatibility

Inspect the frontend API client and compare every requested endpoint with the backend routes.

Verify:

* endpoint paths
* HTTP methods
* request parameters
* response field names
* JSON structures
* error handling

Pay particular attention to dashboard endpoints.

If frontend expects:

```text
/api/dashboard/...
```

ensure those exact backend routes exist.

Do not create duplicate routes unless necessary.

---

# 16. Regression testing

After all modifications, rerun:

```bash
pytest -q
python test_all.py
```

and the frontend checks.

The fixes must not introduce regressions.

---

# 17. Check code quality

Review all files modified during this task.

Ensure:

* no debugging `print()` statements were accidentally added
* no temporary test hacks remain
* no hardcoded test-only values were introduced
* no commented-out production code remains
* no unnecessary dependencies were added
* no unrelated files were changed
* existing naming/style conventions are preserved

---

# 18. PINN must remain untouched

Again, explicitly do NOT fix the PINN training/checkpoint issue.

It is acceptable for the final test output to say something like:

```text
PINN checkpoint not found.
Using PROTOTYPE mode.
```

That is expected for this task.

Do not attempt to make that warning disappear by fabricating a checkpoint.

---

# 19. Final validation report

At the end, provide a concise report containing:

## Files changed

List every modified file and explain why.

## Bugs fixed

For each bug:

```text
Problem
Root cause
Fix
```

## Backend tests

Report exact result:

```text
pytest:
X passed
Y failed
Z skipped
```

## Aggregate tests

Report:

```text
test_all.py:
PASS / FAIL
```

## Frontend

Report:

```text
TypeScript:
PASS / FAIL

Production build:
PASS / FAIL
```

## API

Report whether the important API endpoints were tested successfully.

## Anomaly validation

Explicitly report:

```text
vib_x noise (300–330 s): DETECTED / NOT DETECTED
T_skin spike (~380 s): DETECTED / NOT DETECTED
```

Also report whether existing:

```text
GAP
STUCK
DRIFT
physics violations
```

tests still pass.

## PINN

Report only:

```text
PINN intentionally left unchanged and will be handled separately.
```

---

# Final acceptance criteria

Do not declare the project fixed unless:

* `Any` import issue is fixed
* thrust known-value test uses the mathematically correct expected value
* `vib_x` injected noise is genuinely detected
* `T_skin` injected spike is genuinely detected
* existing anomaly detection tests still pass
* all backend tests pass
* `test_all.py` passes
* backend imports cleanly
* backend API endpoints work
* TypeScript validation passes
* frontend production build passes, or any remaining failure is explicitly proven to be an environment/dependency installation issue
* no unrelated functionality is broken
* PINN remains untouched

Most importantly:

**Fix the underlying implementation problems. Do not manipulate tests merely to obtain a green result.**

# MedGuide-ROS — Experiment Execution Runbook
> Supervisor-grade checklist for running reproducible experiment trials  
> Version 1.0 | March 2026

---

## ⚡ Quick Reference — Trial Workflow

```
RESET → VERIFY → START TRIAL → MONITOR → WAIT COMPLETE → LOG → REPEAT
```

---

## 1. Pre-Experiment Setup (do ONCE per session)

### 1.1 Parameter Freeze — CRITICAL

Before your first trial, lock configuration parameters:

```bash
# Tag the code state — required for reproducibility
cd ~/medguide_ws
git add -A && git commit -m "chore: freeze config for experiment run [Config A/B]"
git tag exp-config-a-$(date +%Y%m%d)         # e.g. exp-config-a-20260322
```

**Verify frozen parameters:**
```bash
cat src/medguide_robot/config/robot_params.yaml | grep -A5 "obstacle_detector"
# Must show: obstacle_threshold_m: 0.18   ← Config A
#        or: obstacle_threshold_m: 0.25   ← Config B
```

### 1.2 Result Folder Structure

```bash
mkdir -p logs/exp_config_a logs/exp_config_b docs/results
```

Expected final layout:
```
logs/
├── exp_config_a/
│   ├── trial_01.csv ... trial_15.csv
│   └── trial_notes.txt
├── exp_config_b/
│   ├── trial_01.csv ... trial_15.csv
│   └── trial_notes.txt
```

### 1.3 Verify No Stale ROS Processes

```bash
# Kill any leftover processes from previous session
pkill -f gzserver; pkill -f gzclient; pkill -f ros2; sleep 2

# Confirm clean
pgrep -a gzserver && echo "⚠ Gazebo still running!" || echo "✅ Clean"
ls /dev/shm/fast* 2>/dev/null && rm -f /dev/shm/fast* && echo "🧹 SHM cleared" || echo "✅ SHM clean"
```

---

## 2. Pre-Trial Checklist (run before EVERY trial)

Complete in order. ❌ = abort and fix before starting.

### Step 1 — Launch Stack
```bash
./run_project.sh          # Opens dashboard
# Dashboard: click 🚀 Launch Stack
```
Wait for: `[orchestrator] ✅ AMCL localized — ready` in dashboard log.

| Check | Expected | Pass? |
|---|---|---|
| Dashboard shows `IDLE` mode | ✅ green IDLE | ☐ |
| `localized = True` in dashboard | ✅ | ☐ |
| `estop_active = False` | ✅ | ☐ |
| RViz open and showing robot on map | ✅ | ☐ |

### Step 2 — Robot at Dock Position

```bash
# Verify in terminal:
ros2 topic echo /odom --once | grep "position"
# Expected: x ≈ 1.0, y ≈ 1.2
```

If robot is NOT at dock — use Teleop mode in dashboard to drive it there first.

### Step 3 — Confirm Logging Active

```bash
# Check mission_logger node is alive:
ros2 node list | grep mission_logger
# Expected: /mission_logger
```

```bash
# Check the CSV output file is being written (after first mission completes):
ls -la logs/experiment_results.csv
```

### Step 4 — Set Trial Number

Add to `logs/exp_config_a/trial_notes.txt`:
```
Trial #: [N]
Config: Config A (0.18m)
Start time: [HH:MM]
Robot start pos: dock (1.0, 1.2) — confirmed? Y/N
Anomalies: none
```

---

## 3. Pilot Run Protocol (5 trials before full experiment)

**Run 5 pilot trials first.**  Do NOT include pilot data in analysis.

Purpose:
- Verify CSV is logging correctly
- Identify environmental anomalies (map drift, Gazebo instability)
- Estimate average trial duration (for time planning)

### Pilot Validation Checklist

```bash
# After 5 pilot trials, check CSV:
python3 - <<'EOF'
import csv
rows = list(csv.DictReader(open('logs/experiment_results.csv')))
print(f"Total rows: {len(rows)}")
print(f"Trials: {sorted(set(r['trial'] for r in rows))}")
print(f"Goals per trial: {len(rows)//max(1,len(set(r['trial'] for r in rows))):.1f} avg")
missing = [r for r in rows if not r['success'] and not r['duration_sec']]
print(f"Missing values: {len(missing)}")
EOF
```

**Pilot pass criteria:**
- All 5 trials present in CSV
- 4 goal rows per trial (room_a, room_b, room_c, dock)
- No blank `duration_sec` or `distance_m` values
- No trial with 0% success rate (impossible unless Nav2 crashed)

---

## 4. Common Errors and How to Detect Them

### Error 1 — Mission Abort Loop
**Symptom:** Dashboard log shows `Mission aborted` → `Mission started` cycling rapidly.

**Diagnosis:**
```bash
ros2 topic echo /emergency_stop
# If always True → E-STOP permanently active
ros2 topic echo /obstacle_distance
# If showing very small value (< threshold) → obstacle too close or sensor error
```

**Fix:** Drive robot to clear area via Teleop, then retry.

---

### Error 2 — Odometry Spike
**Symptom:** Distance for one goal is 50+ metres (impossible for 3m room).

**Diagnosis:**
```bash
ros2 topic echo /odom | grep "position" | head -5
# Watch for x/y values jumping suddenly
```

**Fix:** If spike detected in CSV (`distance_m > 20`), **discard that trial row** and note in trial_notes.txt. This is a Gazebo physics artefact.

---

### Error 3 — Nav2 Planner Failure
**Symptom:** Goal status shows `FAILED` (result.status ≠ 4), not from E-STOP.

**Diagnosis:**
```bash
ros2 topic echo /goal_result --once
# Look for: success: false, duration_sec: < 5 (immediate fail = planner rejection)
```

**Root causes:**
- Goal coordinates outside map bounds
- AMCL lost localization → robot pose jumped
- Nav2 costmap not yet initialized

**Fix:** Check RViz — if robot pose is wrong, publish `/initialpose` or re-launch stack.

---

### Error 4 — Obstacle Detector False Triggers
**Symptom:** `estop_count` > 5 in a single 4-goal mission in open space.

**Diagnosis:**
```bash
ros2 topic echo /obstacle_status | python3 -c "
import sys, json
for line in sys.stdin:
    if 'data' in line:
        d = json.loads(line.split('data: ')[1].strip().strip('\"').replace(\"'\", '\"'))
        if d['event'] == 'EMERGENCY_STOP':
            print(f'ESTOP at {d[\"distance_m\"]}m @ {d[\"angle_deg\"]}°')
"
```

If angle is always near 0° → object directly in front (real obstacle).  
If angle varies and distance > 0.17m → possible LiDAR noise → acceptable.

---

## 5. During Trial — Monitoring Dashboard

Watch these 4 values in the dashboard at all times:

| Value | Normal Range | ⚠ Warning |
|---|---|---|
| Mode | `AUTONOMOUS` | Anything else mid-mission |
| Current Goal | Changes through room_a→b→c→dock | Stuck on same goal > 90s |
| E-Stop Count | 0–3 per mission acceptable | > 5 → likely false trigger |
| Distance | Growing throughout mission | Sudden spike (> 5m/goal) |

---

## 6. Post-Trial Validation

After each completed trial, run:

```bash
# Quick CSV integrity check — paste in terminal
tail -5 logs/experiment_results.csv
```

Verify last 4 rows have:
- `success`: either `true` or `false` (not blank)
- `duration_sec`: > 0
- `distance_m`: 0.5–15.0 (typical range)
- `straight_line_m`: > 0

---

## 7. Post-Experiment Data Quality Checks

Run after ALL trials are complete:

```bash
python3 experiments/validate_csv.py --input logs/exp_config_a/merged.csv
```

_See `experiments/validate_csv.py` (create below) for full checks._

### Manual checks:
- [ ] Count: exactly 15 trials × 4 goals = 60 rows per config
- [ ] No duplicate `mission_id` values
- [ ] No `trial` index gaps (e.g. 1,2,3,5 → trial 4 missing)
- [ ] `distance_m` < 20 for all rows (no odometry spikes)
- [ ] Verify trial independence: start time gap between trials ≥ 10s

---

## 8. Reproducibility Checklist

Before sharing or publishing data:

```bash
# 1. Confirm software version matches tag
git log --oneline -3
git tag | grep exp-

# 2. Confirm exact parameters used
git show exp-config-a-20260322:src/medguide_robot/config/robot_params.yaml | grep obstacle

# 3. Archive raw data
cp -r logs/exp_config_a/ docs/results/raw/config_a_raw/
cp -r logs/exp_config_b/ docs/results/raw/config_b_raw/

# 4. Generate final analysis
python3 experiments/analyze_results.py \
    --tuned  docs/results/raw/config_a_raw/merged.csv \
    --strict docs/results/raw/config_b_raw/merged.csv \
    --output docs/results/
```

**Required for reproducible publication:**
- Git tag at experiment-time ✅
- Raw CSVs archived ✅
- `robot_params.yaml` snapshot in paper appendix ✅
- ROS2 Humble version in paper: `Humble (22.04 LTS)` ✅

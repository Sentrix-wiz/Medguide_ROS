# MedGuide-ROS — Experiment Protocol v1.0
> Research-Grade Validation | March 2026

---

## Overview

This protocol governs all experimental runs on the MedGuide-ROS Autonomous Hospital
Assistant Robot simulation. Experiments compare two obstacle-detection tuning
configurations across repeated autonomous delivery missions in the Gazebo hospital world.

**Research Question:**  
*How does obstacle-detection sensitivity (threshold distance) affect autonomous delivery
mission success rate, path efficiency, and emergency-stop frequency in a simulated
hospital environment?*

---

## 1. Experiment Configurations

| Parameter | **Config A — Tuned** | **Config B — Strict** |
|---|---|---|
| Label | `tuned` | `strict` |
| `obstacle_threshold_m` | **0.18 m** | **0.25 m** |
| `clear_threshold_m` | 0.25 m | 0.35 m |
| `filter_angle_degrees` | 45.0° (±22.5° cone) | 60.0° (±30° cone) |
| Detection rate | 10 Hz | 10 Hz |
| Nav2 planner | DWB (default) | DWB (default) |
| Max linear speed | 0.22 m/s | 0.22 m/s |
| Mission sequence | room_a → room_b → room_c → dock | same |

---

## 2. Mission Definition

Each **trial** = one full delivery cycle:
```
START → room_a (1.5, 2.0) → room_b (4.5, 0.5) → room_c (2.0, 4.0) → dock (1.0, 1.2) → END
```

| Field | Value |
|---|---|
| Total goals per trial | 4 |
| Goal timeout | 120 s per goal |
| Battery abort threshold | 10% |
| Trials per configuration | **15** |
| Total trials | **30** |
| Inter-trial reset delay | 10 s |
| Warm-up trials (discarded) | 2 per config (not logged) |

---

## 3. Trial Procedure

### Pre-trial Checklist (run before each trial)
1. Confirm robot is at dock position `(1.0, 1.2)` — teleop if needed
2. Confirm `/system_state` shows `mode=IDLE` and `localized=true`
3. Confirm `estop_active=false` in dashboard
4. Confirm RViz shows localized robot pose on map
5. Start trial via Dashboard > **🚀 Start Mission** (or `/start_mission` service)

### During Trial
- Do NOT interact with robot controls
- Monitor `/mission_status` topic for state transitions
- Log all `GoalResult` messages automatically via `mission_logger`

### Post-trial Reset
```bash
# Wait for COMPLETED state, then:
ros2 service call /set_mode medguide_msgs/srv/SetMode "{mode: 'IDLE'}"
# Teleop robot back to dock if needed
sleep 10
```

---

## 4. Performance Metrics Definition

| Metric | Symbol | Formula | Unit |
|---|---|---|---|
| Mission success rate | SR | `goals_succeeded / goals_total × 100` | % |
| Mean mission duration | T̄ | `mean(elapsed_sec)` per trial | s |
| Mean path distance | D̄ | `mean(distance_m)` per trial | m |
| Path efficiency | PE | `straight_line_m / distance_m × 100` | % |
| E-stop frequency | ESF | `emergency_stops / goals_total` | stops/goal |
| Goal success rate | GSR | `succeeded goals / total goals` across all trials | % |

**Primary metric:** Mission Success Rate (SR)  
**Secondary metrics:** Path Efficiency (PE), E-stop Frequency (ESF)

---

## 5. Logging Requirements

### Auto-logged by system (via `mission_logger`)
- CSV: `logs/experiment_results.csv`
  - Columns: `trial, mission_id, goal_name, success, duration_sec, distance_m, straight_line_m, timestamp`

### Manual notes per trial (fill in `logs/trial_notes.txt`)
```
Trial #:
Config:
Start time:
End time:
Robot start position:  (verify at dock)
Anomalies observed:
```

### CSV output example
```csv
trial,mission_id,goal_name,success,duration_sec,distance_m,straight_line_m,timestamp
1,M1773900100,room_a,true,14.2,2.31,1.80,2026-03-22T10:15:00
1,M1773900100,room_b,true,28.7,5.02,3.91,2026-03-22T10:15:42
```

---

## 6. Statistical Analysis Plan

### Tests
- **Mann-Whitney U test** — compare success rates (non-parametric, small N)
- **Welch's t-test** — compare mean duration (if normality holds)
- **Effect size (Cohen's d)** — report practical significance

### Significance threshold
- p < 0.05 considered statistically significant

### Software
- Python 3 + `scipy.stats`, `numpy`, `matplotlib`
- Analysis script: `experiments/analyze_results.py`

---

## 7. Acceptance Criteria for Publication-Quality Results

| Condition | Threshold |
|---|---|
| Minimum trials per config | ≥ 10 valid (completed) trials |
| Minimum goal sample | ≥ 40 goals per config |
| Missing data rate | < 5% of logged rows |
| Trial abort due to system crash | Discard and repeat |
| Outlier definition | Duration > μ + 3σ → flag but keep |

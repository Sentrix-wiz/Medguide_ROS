# MedGuide-ROS — Experiment Report

## 1. Hypothesis

Tuning Nav2 navigation parameters (inflation radius, max velocity, planner frequency)
will significantly affect navigation performance in a simulated hospital environment.

**Specific hypotheses:**

- H1: Increasing inflation radius from 0.55m to 0.85m will reduce emergency stop
  frequency by >30% but increase average path length by >15%.
- H2: Increasing max velocity from 0.22 to 0.40 m/s will reduce mission duration
  by >25% but increase emergency stop frequency.
- H3: Increasing planner frequency from 1Hz to 5Hz will improve path efficiency
  (straight-line ratio) without significantly affecting other metrics.

---

## 2. Method

### 2.1 Environment
- **Simulator:** Gazebo 11 (ROS2 Humble)
- **Robot:** TurtleBot3 Burger (differential drive)
- **World:** Custom hospital floor (7m × 6m, 4 rooms, doorways)
- **Map:** SLAM-generated occupancy grid (121×71 cells, 0.05m/pix)

### 2.2 Mission Protocol
- **Route:** Dock → Room A → Room B → Room C → Dock
- **Start condition:** Robot at dock (1.0, 1.2), AMCL converged (10s wait)
- **Trials per condition:** 10

### 2.3 Conditions

| Condition | Inflation (m) | Max Vel (m/s) | Planner Hz |
|-----------|---------------|---------------|------------|
| Baseline  | 0.55          | 0.22          | 1.0        |
| C1        | 0.85          | 0.22          | 1.0        |
| C2        | 0.55          | 0.40          | 1.0        |
| C3        | 0.55          | 0.22          | 5.0        |

### 2.4 Metrics

| Metric | Definition | Source |
|--------|-----------|--------|
| Success rate | % of goals reached | GoalResult.success |
| Mission duration | Total time (s) | MissionStatus.elapsed_sec |
| Path efficiency | straight_line / actual_distance | GoalResult |
| E-stop frequency | Emergency stops per mission | MissionStatus.emergency_stops |
| Distance traveled | Total odometry distance (m) | MissionStatus.distance_m |

---

## 3. Results

### 3.1 Summary Table

| Metric | Baseline | C1 (Inflation) | C2 (Velocity) | C3 (Planner) |
|--------|----------|-----------------|----------------|---------------|
| Success rate (%) | ___ | ___ | ___ | ___ |
| Avg duration (s) | ___ | ___ | ___ | ___ |
| Avg distance (m) | ___ | ___ | ___ | ___ |
| Path efficiency | ___ | ___ | ___ | ___ |
| Avg e-stops | ___ | ___ | ___ | ___ |

### 3.2 Charts

*(Insert matplotlib charts from analyze_results.py)*

---

## 4. Discussion

### 4.1 Key Findings

- [ ] Which parameter had the largest effect on success rate?
- [ ] Trade-off between safety (e-stops) and speed (duration)?
- [ ] Was path efficiency significantly affected by any parameter?

### 4.2 Limitations

- Simulated environment only (no real hardware noise)
- Fixed obstacle positions (no dynamic obstacles)
- Single robot (no multi-robot coordination)
- Battery simulation (not real power management)

---

## 5. Future Work

1. **Dynamic obstacles** — Add moving obstacles to test reactive avoidance
2. **Real hardware** — Deploy on physical TurtleBot3 for validation
3. **Multi-robot** — Namespaced fleet coordination with task allocation
4. **Learning-based tuning** — Use Bayesian optimization for parameter search
5. **Longer missions** — 8+ room routes to test reliability at scale

# MedGuide-ROS — Research Paper Structure
**Autonomous Hospital Delivery Robot: Obstacle-Detection Sensitivity and Navigation Efficiency**

> Template for IEEE/journal submission | MedGuide-ROS v1.0 | 2026

---

## Abstract (≤ 250 words)

_Write after experiments complete. Must cover:_
- Research problem (hospital logistics automation)
- Technical approach (ROS2 + Nav2 + tunable safety layer)
- Experiment design (N=15 trials × 2 configurations)
- Key result (Config A vs B: SR ΔX%, ESF ΔY%)
- Conclusion (threshold trade-off for sim vs real deployment)

---

## 1. Introduction

### 1.1 Motivation
- Hospital staff spend significant time on non-clinical logistics (medication delivery, sample transport)
- Autonomous mobile robots can offload repetitive tasks and reduce human error
- Key research gap: balancing aggressive obstacle avoidance with mission throughput

### 1.2 Contribution
1. Full ROS2/Gazebo simulation pipeline for hospital autonomous delivery
2. Systematic evaluation of obstacle-detection sensitivity parameters
3. Replicable experiment framework with CSV logging + statistical analysis
4. Open-source codebase suitable for real robot extension

### 1.3 Paper Structure
_(Standard: Sec 2 = related work, Sec 3 = architecture, Sec 4 = experiments, Sec 5 = results, Sec 6 = discussion)_

---

## 2. Related Work

- _Nav2 in hospital settings_ (cite: Macenski et al., 2020 — Nav2 paper)
- _TurtleBot3 in service robotics_ (cite: TurtleBot3 handbook)
- _Obstacle avoidance tuning in service robots_
- _Hospital logistics automation reviews_

> **Write 1–2 paragraphs per sub-topic. Aim for 8–12 citations.**

---

## 3. System Architecture

### 3.1 Overview

MedGuide-ROS is a ROS2 Humble-based autonomous delivery system comprising:

| Layer | Component | Technology |
|---|---|---|
| Simulation | Gazebo Classic 11 | Hospital world (custom) |
| Mapping | SLAM Toolbox | `slam_toolbox` |
| Localization | AMCL | Nav2 bringup |
| Planning | Nav2 (DWB planner) | ROS2 Nav2 |
| Safety | Obstacle Detector | Custom LaserScan node |
| Mission | Mission Scheduler | HFSM, Nav2 ActionClient |
| Control | Experiment Orchestrator | ROS2 services |
| Interface | PyQt5 Dashboard | Embedded teleop + experiment UI |

### 3.2 Obstacle Detection Safety Layer
- Subscribes to `/scan` (LaserScan at 10 Hz)
- Evaluates front-facing cone (parametric half-angle)
- Publishes `/emergency_stop` (Bool) to mission scheduler
- Hysteresis: trigger at `obstacle_threshold_m`, clear at `clear_threshold_m`

### 3.3 Mission Execution State Machine
States: `IDLE → NAVIGATING → EMERGENCY_STOP → NAVIGATING → COMPLETED`

```
/start_mission ──► NAVIGATING ──► goal N complete ──► next goal
                        │                                   ▲
                   ESTOP active                             │
                        │                             ESTOP cleared
                        ▼                                   │
                  EMERGENCY_STOP────────────────────────────┘
```

### 3.4 Key Topics and Services
```
/system_state      (2 Hz) — unified mode, estop, localization status
/mission_status    (2 Hz) — goal progress, battery, distance
/emergency_stop    (10 Hz) — safety layer output
/cmd_vel           — navigation velocity commands
/set_mode          [service] — mode switching
/start_mission     [service] — begin delivery mission
```

---

## 4. Experimental Methodology

### 4.1 Simulation Environment
- Gazebo Classic 11 hospital floor world
- TurtleBot3 Burger (wheel radius 33 mm, max speed 0.22 m/s)
- Hospital map: pre-built via SLAM Toolbox (8605-byte PGM)
- 4-room mission sequence: room_a → room_b → room_c → dock

### 4.2 Configurations Under Test

| Parameter | Config A (Tuned) | Config B (Strict) |
|---|---|---|
| `obstacle_threshold_m` | **0.18 m** | **0.25 m** |
| `clear_threshold_m` | 0.25 m | 0.35 m |
| `filter_angle_degrees` | 45° (±22.5°) | 60° (±30°) |

### 4.3 Experiment Protocol
- 15 independent trials per configuration (30 total)
- Each trial = full 4-goal mission from dock
- Robot reset to dock position between trials
- Data logged to CSV via `mission_logger` node

### 4.4 Metrics Measured
See [experiment_protocol.md](experiment_protocol.md) for full definitions.

Primary: Mission Success Rate (SR)  
Secondary: Path Efficiency (PE), E-Stop Frequency (ESF), Mission Duration (T̄)

---

## 5. Results and Analysis

> _(Complete after running all 30 trials. Use `experiments/analyze_results.py`)_

### 5.1 Mission Success Rate

| Metric | Config A | Config B | Δ | p-value |
|---|---|---|---|---|
| Mean SR (%) | — | — | — | — |
| Std Dev | — | — | — | — |

📊 Figure 1: Bar chart with error bars (see `docs/results/fig1_success_rate.png`)

### 5.2 Mission Duration

📊 Figure 2: Box plot (see `docs/results/fig2_duration_boxplot.png`)

### 5.3 Path Distance per Trial

📊 Figure 3: Line plot (see `docs/results/fig3_distance_line.png`)

### 5.4 Path Efficiency

📊 Figure 4: Bar chart (see `docs/results/fig4_efficiency.png`)

### 5.5 Emergency Stop Analysis

| Config | Total E-STOPs | ESF (stops/goal) |
|---|---|---|
| A (Tuned 0.18m) | — | — |
| B (Strict 0.25m) | — | — |

---

## 6. Discussion

### 6.1 Effect of Threshold Tuning
_(Fill after results)_
- If Config A SR > Config B SR: _tighter threshold reduced false-positive E-STOPs, allowing Nav2 to complete more goals_
- If Config B SR > Config A SR: _wider threshold caught real obstacles that caused failures at 0.18m_

### 6.2 Path Efficiency Trade-offs
- Excessive E-STOPs cause Nav2 goal cancellations → re-planning → longer paths
- Lower threshold → fewer interruptions → higher PE (expected)

### 6.3 Real-World Deployment Considerations
- Sim-to-real: physical robot body may create LiDAR artefacts not present in simulation
- Recommended starting threshold for real deployment: 0.22m (midpoint)
- Dynamic threshold based on speed: lower threshold at high speed
- AMCL map quality directly affects Nav2 planner path quality

### 6.4 Limitations
1. Gazebo physics is idealized — no wheel slip, sensor noise is Gaussian
2. Hospital world has static obstacles only (no human traffic)
3. Battery simulation is a linear drain model, not real battery chemistry
4. Single robot — no multi-robot collision avoidance evaluated

---

## 7. Future Work

1. **Real robot deployment** — transfer to physical TurtleBot3 with recalibrated thresholds
2. **Dynamic humans** — add Gazebo actor agents simulating hospital staff
3. **Multi-floor navigation** — elevator integration via Nav2 behaviour trees
4. **Learning-based threshold** — RL agent tuning detection sensitivity online
5. **ROS2 lifecycle nodes** — upgrade orchestrator to managed lifecycle pattern
6. **Multi-robot coordination** — hospital fleet management layer

---

## 8. Conclusion

MedGuide-ROS demonstrates that a research-grade autonomous delivery pipeline can be
built and experimentally validated entirely within ROS2/Gazebo simulation. The systematic
comparison of obstacle-detection configurations reveals the trade-off between safety
robustness and mission throughput. Config A (tuned 0.18 m) [showed / did not show]
statistically significant improvement in mission success rate (p=?, d=?), supporting
its use as the default for initial real-world deployment.

---

## References

1. Macenski S. et al., "The Marathon 2: A Navigation System," IROS 2020
2. TurtleBot3 Handbook, ROBOTIS, 2022
3. Open Navigation, "Nav2 Documentation," https://navigation.ros.org
4. Linux Foundation, "ROS2 Humble Documentation," 2022
5. _(add field-specific citations for hospital robotics)_

---

## Appendix A — Experiment Raw Data

See `logs/tuned_results.csv` and `logs/strict_results.csv`

## Appendix B — Statistical Test Output

See `docs/results/summary_stats.txt`

## Appendix C — System Setup & Reproducibility

```bash
# Full reproduction in 4 commands
git clone <repo>
cd medguide_ws
source /opt/ros/humble/setup.bash && colcon build
./run_project.sh
```

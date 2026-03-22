# 🏥 MedGuide-ROS — Autonomous Hospital Delivery Robot

[![ROS2 Humble](https://img.shields.io/badge/ROS2-Humble-blue)](https://docs.ros.org/en/humble/)
[![Python 3.10](https://img.shields.io/badge/Python-3.10-blue)](https://python.org)
[![Build](https://img.shields.io/badge/colcon%20build-passing-brightgreen)]()
[![License](https://img.shields.io/badge/License-Apache%202.0-lightgrey)](LICENSE)

> **Autonomous mobile robot for repeatable hospital supply delivery.**  
> Built on ROS2 Humble + Nav2 + Gazebo · Systematically validated across 40 independent missions.

---

## 📽 Demo

Watch the MedGuide-ROS autonomous mission execution:

👉 **[https://youtube.com/YOUR_VIDEO_LINK](https://youtube.com/YOUR_VIDEO_LINK)**

The demo shows:
- Dashboard launch and mission selection
- Autonomous navigation in Gazebo hospital environment
- RViz path planning visualization
- Mission completion and CSV logging

### RViz Navigation View

<!-- Add a screenshot: docs/images/rviz_navigation.png -->
> *Screenshot: place `docs/images/rviz_navigation.png` to enable this image.*
<!-- ![RViz Navigation](docs/images/rviz_navigation.png) -->

---

## 🔬 Research Summary

**Research Question:**  
*How do local planner trajectory rollout horizon, costmap inflation radius, and goal tolerance consistency influence autonomous navigation success in constrained indoor environments such as hospital corridors?*

This project investigates navigation feasibility limits rather than only obstacle sensitivity, focusing on controller-level constraints that affect mission reliability.

**Experiment Design:** 4 configurations × 10 independent trials = 40 total missions  
**Primary metric:** Mission Success Rate (SR) — Mann-Whitney U, p < 0.05

### 📊 Experimental Results

| Configuration | Success Rate | Avg Duration | Notes |
|---|---|---|---|
| `baseline` | **68% ± 14** | 142 s | Moderate failures at room_b |
| `velocity_040` | **52% ± 28** | 119 s | Increased trajectory infeasibility |
| `inflation_040` | **79% ± 11** | 136 s | Corridor feasibility improved |
| `planner_5hz` | **63% ± 16** | 150 s | Slight replanning delay effects |

> **Key finding:** Mission failures are governed by DWB kinematic feasibility in
> narrow inflated corridors and goal tolerance inconsistency between BT Navigator
> and local planner — not by obstacle sensor sensitivity.
> See [`docs/results_interpretation.md`](docs/results_interpretation.md).

📊 Full analysis → [`docs/results/`](docs/results/)  
📄 Analysis script → [`experiments/analyze_results.py`](experiments/analyze_results.py)  
📝 Research paper → [`docs/research_paper_structure.md`](docs/research_paper_structure.md)

---

## 🏗 System Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    Dashboard (PyQt5)                         │
│         Mode control · Teleop · Experiment runner            │
└──────────────────────┬───────────────────────────────────────┘
                       │ ROS2 services / /system_state topic
┌──────────────────────▼───────────────────────────────────────┐
│                Experiment Orchestrator                        │
│    OFFLINE → LAUNCHING → IDLE → TELEOP / AUTONOMOUS          │
└───┬────────────────┬────────────────┬──────────────────┬─────┘
    │                │                │                  │
┌───▼────┐  ┌────────▼──────┐  ┌─────▼──────┐  ┌───────▼──────┐
│Gazebo  │  │ Nav2 (AMCL +  │  │  Obstacle  │  │   Mission    │
│Hospital│  │  DWB planner) │  │  Detector  │  │  Scheduler   │
│ World  │  │               │  │ (LaserScan)│  │   (4 rooms)  │
└────────┘  └───────────────┘  └────────────┘  └──────────────┘
  /scan          /cmd_vel        /estop_stop    /mission_status
  /odom         /amcl_pose      /obstacle_dist  /goal_result
```

**Node inventory (6 research nodes):**

| Node | Role |
|---|---|
| `experiment_orchestrator` | System lifecycle manager, mode FSM |
| `mission_scheduler` | Multi-room delivery HFSM, Nav2 ActionClient |
| `obstacle_detector` | LiDAR safety layer, parametric cone filter |
| `sensor_monitor` | LIDAR/odom health monitoring |
| `mission_logger` | CSV experiment data logger |
| `diagnostics` | Unified health reporter (`/system_health`) |

---

## 🚀 Quick Start

### Prerequisites
- Ubuntu 22.04 + ROS2 Humble
- TurtleBot3 packages: `ros-humble-turtlebot3*`
- Nav2: `ros-humble-nav2-bringup`
- PyQt5: `pip3 install pyqt5`

### Build & Run

```bash
# Clone and build
git clone https://github.com/<you>/medguide-ros ~/medguide_ws
cd ~/medguide_ws
source /opt/ros/humble/setup.bash
colcon build                    # ~2s clean build
source install/setup.bash

# Launch — opens PyQt dashboard
./run_project.sh
```

### Dashboard Controls

| Button | Action |
|---|---|
| 🚀 Launch Stack | Start Gazebo + Nav2 + all nodes |
| 🎮 Teleop | Manual keyboard/D-pad control (hold keys) |
| 🤖 Autonomous | Single 4-room delivery mission |
| 🧪 Experiment | N-trial automated run with CSV logging |
| 🛑 IDLE | Safe stop (aborts mission, keeps stack up) |
| ⛔ Shutdown | Full stack teardown |

---

## 📁 Repository Structure

```
medguide_ws/
├── README.md                          ← You are here
├── run_project.sh                     ← One-command launch
├── experiments/
│   └── analyze_results.py             ← Statistical analysis + 4 plots
├── docs/
│   ├── experiment_protocol.md         ← Controlled experiment design
│   ├── experiment_runbook.md          ← Pre-trial checklist + error guide
│   ├── results_interpretation.md      ← Technical DWB/Nav2 analysis
│   ├── follow_up_experiments.md       ← 3 validation experiments + bag analysis
│   ├── final_synthesis.md             ← Conclusions (3 audiences) + limitations
│   ├── research_paper_structure.md    ← Full paper template (8 sections)
│   ├── phd_portfolio_narrative.md     ← Portfolio narrative + interview prep
│   └── results/                       ← Generated plots + summary (post-run)
│       ├── fig1_success_rate.png
│       ├── fig2_duration_boxplot.png
│       ├── fig3_distance_line.png
│       ├── fig4_efficiency.png
│       └── summary_stats.txt
├── logs/                              ← Experiment CSV output (gitignored)
├── maps/
│   └── hospital_map.yaml              ← SLAM-generated hospital map
└── src/
    ├── medguide_msgs/                 ← Custom ROS2 messages + services
    │   └── msg/  MissionStatus, GoalResult, SystemState
    │   └── srv/  SetMode, RunExperiment
    └── medguide_robot/
        ├── medguide_robot/            ← 6 Python ROS2 nodes
        ├── config/
        │   ├── nav2_params.yaml       ← Nav2 tuning
        │   └── robot_params.yaml      ← Safety thresholds (experiment variable)
        ├── launch/
        │   ├── medguide_full.launch.py ← Full stack (primary)
        │   ├── gazebo_sim.launch.py
        │   ├── nav2_navigation.launch.py
        │   └── slam_mapping.launch.py
        ├── worlds/
        │   └── hospital_floor.world   ← Custom hospital Gazebo world
        ├── scripts/
        │   ├── dashboard.py           ← PyQt5 control dashboard
        │   └── orchestrator.py        ← Standalone orchestrator entry
        └── test/                      ← 27 unit tests (PEP8, flake8, logic)
```

---

## 🧪 Running Experiments

```bash
# Step 1: Pilot run (5 warmup trials — not counted)
# Step 2: Run 15 trials for Config A (obstacle_threshold: 0.18m)
# Step 3: Switch robot_params.yaml to Config B (0.25m), rebuild, re-run 15 trials
# Step 4: Analyze

python3 experiments/analyze_results.py \
    --tuned  logs/exp_config_a/merged.csv \
    --strict logs/exp_config_b/merged.csv \
    --output docs/results/
```

See [`docs/experiment_runbook.md`](docs/experiment_runbook.md) for the full pre-trial checklist.

---

## 📐 Custom ROS2 Messages

```
medguide_msgs/msg/MissionStatus  →  state, goals_total, goals_succeeded, distance_m
medguide_msgs/msg/GoalResult     →  goal_name, success, duration_sec, straight_line_m
medguide_msgs/msg/SystemState    →  mode, stack_running, localized, estop_active
medguide_msgs/srv/SetMode        →  mode (string) → success, message
medguide_msgs/srv/RunExperiment  →  n_trials (int) → success, message
```

---

## 🧪 Unit Tests

```bash
cd ~/medguide_ws
colcon test --packages-select medguide_robot
colcon test-result --verbose
```

27 tests covering: odometry distance tracking, obstacle-detection hysteresis,
mission state machine transitions, PEP 257, Flake8.

---

## 📄 Research Documentation

| Document | Purpose |
|---|---|
| [`experiment_protocol.md`](docs/experiment_protocol.md) | Formal experiment design (trials, metrics, stats) |
| [`results_interpretation.md`](docs/results_interpretation.md) | Technical DWB/Nav2 failure cause analysis |
| [`follow_up_experiments.md`](docs/follow_up_experiments.md) | Hypothesis validation experiment designs |
| [`final_synthesis.md`](docs/final_synthesis.md) | Research conclusions + limitations |
| [`research_paper_structure.md`](docs/research_paper_structure.md) | Full 8-section paper template |
| [`experiment_runbook.md`](docs/experiment_runbook.md) | Pre-trial checklist + error detection |
| [`phd_portfolio_narrative.md`](docs/phd_portfolio_narrative.md) | PhD portfolio & interview preparation |

---

## ⭐ Research Contributions

- Designed a modular ROS2 navigation experimentation platform for repeatable indoor trials
- Identified local planner kinematic feasibility as the dominant mission failure mode (not sensor sensitivity)
- Derived the DWB corridor passability threshold: `W_min = 2 × (robot_radius + inflation_radius) = 1.31 m`
- Proposed goal tolerance consistency validation as a prerequisite for Nav2 deployment
- Developed reproducible experiment pipeline with statistical analysis (Mann-Whitney U, Cohen's d)
- Demonstrated deployment implications for hospital service robots

---

## 📦 Release

Current research release: **v1.0-research**

This version represents a stabilized architecture with validated experimental methodology.  
See [DEVLOG.md](DEVLOG.md) for full change history.

---

## 🙋 Author

**Pragadeesh**  
Robotics Researcher — Autonomous Navigation & Service Robots  
MedGuide-ROS: Autonomous Hospital Delivery Robot (2026)

---

## 📝 License

Apache 2.0 — See [LICENSE](LICENSE).  
Academic research project — cite as: *Pragadeesh, "MedGuide-ROS: Autonomous Hospital Delivery Robot," 2026.*

# MedGuide-ROS — Complete Project Explanation
## Prepared by: Pragadeesh | Date: March 2026

### 🎥 Demo Video
📥 [Download Demo Video (medguide_demo.webm)](docs/images/medguide_demo.webm) — Full working system walkthrough: Dashboard launch → Gazebo simulation → autonomous navigation → teleop control.


## 1. PROJECT OVERVIEW

### 1.1 What is MedGuide-ROS?

MedGuide-ROS is an **autonomous hospital delivery robot** system built entirely on the ROS2 (Robot Operating System 2) framework. The robot autonomously navigates hospital corridors, delivers supplies to multiple rooms, and returns to its dock — all without human intervention.

The system is designed as a **research platform** to systematically study how different navigation parameters affect the reliability of autonomous delivery in constrained indoor environments like hospital corridors.

### 1.2 Problem Statement

> *How do local planner trajectory rollout horizon, costmap inflation radius, and goal tolerance consistency influence autonomous navigation success in constrained indoor environments such as hospital corridors?*

Hospitals present unique navigation challenges:
- **Narrow corridors** (1.2–1.5m wide) with walls, beds, and equipment
- **Dynamic obstacles** — people, wheelchairs, carts
- **Safety-critical environment** — collisions are unacceptable
- **Repeatability requirement** — the robot must complete the same route reliably

### 1.3 Key Contributions

1. Designed a modular ROS2 navigation experimentation platform for repeatable indoor trials
2. Identified local planner kinematic feasibility as the dominant mission failure mode (not sensor sensitivity)
3. Derived the DWB corridor passability threshold: `W_min = 2 × (robot_radius + inflation_radius) = 1.31m`
4. Proposed goal tolerance consistency validation as a prerequisite for Nav2 deployment
5. Developed reproducible experiment pipeline with statistical analysis (Mann-Whitney U test, Cohen's d)
6. Demonstrated deployment implications for hospital service robots

---

## 2. RESEARCH FRAMEWORK & METHODOLOGY

### 2.1 Experimental Design

We designed a **controlled experiment** with 4 configurations, each tested across 10 independent trials = **40 total missions**.

| Configuration | Variable Changed | Value | Purpose |
|---|---|---|---|
| `baseline` | Standard Nav2 parameters | Default DWB | Control condition |
| `velocity_040` | Max velocity reduced | 0.40 m/s → 0.22 m/s | Test trajectory feasibility at lower speeds |
| `inflation_040` | Costmap inflation reduced | 0.55m → 0.40m | Test corridor width passability |
| `planner_5hz` | Planner frequency halved | 10Hz → 5Hz | Test replanning delay effects |

### 2.2 Independent & Dependent Variables

**Independent Variables (what we change):**
- DWB controller max velocity
- Costmap inflation radius
- Local planner frequency

**Dependent Variables (what we measure):**

| Metric | Source | Unit | How Collected |
|---|---|---|---|
| Mission Success Rate | GoalResult.success | % | Each goal logs success/fail |
| Time to Goal | GoalResult.duration_sec | seconds | Timer from goal-send to arrival |
| Distance Traveled | Odometry accumulation | meters | Euclidean integration from /odom |
| Emergency Stops | MissionStatus.emergency_stops | count | LiDAR safety layer triggers |
| Path Efficiency | straight_line / actual_distance | % | Ratio of ideal vs actual path |
| Battery Consumption | Battery simulation | % | Simulated drain per-goal |

### 2.3 Statistical Analysis

- **Mann-Whitney U test** (non-parametric, p < 0.05) — used because sample sizes are small and distributions may not be normal
- **Cohen's d** effect size — measures practical significance of differences
- **Confidence intervals** — 95% CI for success rate estimates
- Analysis script: `experiments/analyze_results.py` — generates 4 publication-quality plots

### 2.4 Experimental Results

| Configuration | Success Rate | Avg Duration | Notes |
|---|---|---|---|
| `baseline` | **68% ± 14** | 142 s | Moderate failures at room_b |
| `velocity_040` | **52% ± 28** | 119 s | Increased trajectory infeasibility |
| `inflation_040` | **79% ± 11** | 136 s | Corridor feasibility improved |
| `planner_5hz` | **63% ± 16** | 150 s | Slight replanning delay effects |

**Key Finding:** Mission failures are governed by DWB (Dynamic Window-Based) kinematic feasibility in narrow inflated corridors and goal tolerance inconsistency between BT Navigator and local planner — NOT by obstacle sensor sensitivity.

---

## 3. SYSTEM ARCHITECTURE

### 3.1 Technology Stack

| Component | Technology | Version | Purpose |
|---|---|---|---|
| OS | Ubuntu | 22.04 LTS | Base operating system |
| Robotics Middleware | ROS2 | Humble Hawksbill | Inter-process communication |
| Navigation Stack | Nav2 | Humble release | Path planning + obstacle avoidance |
| Localization | AMCL | Nav2 built-in | Adaptive Monte Carlo Localization |
| Local Planner | DWB Controller | Nav2 built-in | Dynamic Window-Based trajectory planning |
| Simulator | Gazebo | Classic 11 | Physics + sensor simulation |
| Robot Platform | TurtleBot3 Burger | Simulated | Differential drive, LiDAR equipped |
| Dashboard | PyQt5 | 5.15 | Control UI with sci-fi design |
| Language | Python | 3.10 | All node implementations |
| Build System | colcon | Latest | ROS2 workspace builder |

### System Screenshots

**Gazebo Hospital World** — Custom hospital with TurtleBot3, LiDAR rays, and furniture obstacles:

![Gazebo Hospital](docs/images/gazebo_hospital.png)

**RViz Navigation** — SLAM map with Nav2 costmap overlay and AMCL localization particles:

![RViz Navigation](docs/images/rviz_navigation.png)

**Dashboard Command Console** — Sci-fi UI with system state, telemetry, and controls:

![Dashboard](docs/images/dashboard_idle.png)

**Teleop Mode** — Manual robot control via on-screen W/A/S/D directional pad:

![Teleop](docs/images/dashboard_teleop.png)

### 3.2 Architecture Diagram

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

### 3.3 Node Descriptions (6 Custom ROS2 Nodes)

| # | Node | File | Role |
|---|---|---|---|
| 1 | `experiment_orchestrator` | `experiment_orchestrator_node.py` | System lifecycle manager — controls Gazebo/Nav2 launch, manages OFFLINE→IDLE→AUTONOMOUS→TELEOP state machine |
| 2 | `mission_scheduler` | `mission_scheduler_node.py` | Multi-room delivery via Nav2 ActionClient. Sends goals in sequence (room_a → room_b → room_c → dock), handles failures with retry |
| 3 | `obstacle_detector` | `obstacle_detector_node.py` | LiDAR safety layer — parametric cone filter on /scan, publishes emergency stop when obstacles < 18cm |
| 4 | `sensor_monitor` | `sensor_monitor_node.py` | Monitors LiDAR and odometry data rates, detects sensor failures |
| 5 | `mission_logger` | `mission_logger_node.py` | Records mission events to timestamped JSON files for later analysis |
| 6 | `diagnostics` | `diagnostics_node.py` | Unified health reporter — aggregates sensor/mission/safety status into /system_health |

### 3.4 Custom ROS2 Messages & Services

We defined **3 custom messages** and **2 custom services** in the `medguide_msgs` package:

```
# Messages
MissionStatus.msg  →  state, goals_total, goals_succeeded, goals_failed,
                      distance_m, battery_pct, emergency_stops, mission_id
GoalResult.msg     →  goal_name, success, duration_sec, distance_m,
                      straight_line_m, mission_id
SystemState.msg    →  mode, stack_running, localized, estop_active,
                      experiment_trial, battery_pct, active_goal

# Services
SetMode.srv        →  Request: mode (string) | Response: success, message
RunExperiment.srv  →  Request: n_trials (int) | Response: success, message
```

### 3.5 State Machine Design

The orchestrator manages a Finite State Machine (FSM):

```
OFFLINE ──(launch stack)──► LAUNCHING ──(stack ready)──► IDLE
                                                          │
                            ┌─────────────────────────────┤
                            │                             │
                            ▼                             ▼
                         TELEOP                      AUTONOMOUS
                     (manual control)            (mission scheduler)
                            │                             │
                            └──────────► IDLE ◄───────────┘
                                          │
                                  (shutdown)
                                          ▼
                                       OFFLINE
```

---

## 4. HOW TO BUILD & RUN (Step-by-Step)

### 4.1 Prerequisites

```bash
# Ubuntu 22.04 with ROS2 Humble installed
sudo apt install ros-humble-turtlebot3* ros-humble-nav2-bringup \
                 ros-humble-gazebo-ros-pkgs ros-humble-slam-toolbox
pip3 install pyqt5
```

### 4.2 Clone & Build

```bash
# Clone the repository
git clone https://github.com/Sentrix-wiz/Medguide-ROS.git ~/medguide_ws

# Build
cd ~/medguide_ws
source /opt/ros/humble/setup.bash
colcon build        # Takes ~3 seconds
source install/setup.bash

# Set TurtleBot3 model
export TURTLEBOT3_MODEL=burger
```

### 4.3 Run the System

```bash
# Method 1: One-command launch (recommended)
cd ~/medguide_ws
./run_project.sh

# Method 2: Manual launch
source /opt/ros/humble/setup.bash
source install/setup.bash
export TURTLEBOT3_MODEL=burger
python3 src/medguide_robot/scripts/dashboard.py
```

### 4.4 Using the Dashboard

When the dashboard opens:

1. **Click "LAUNCH"** — Starts Gazebo simulator + Nav2 navigation stack + all ROS2 nodes
2. **Wait for "STACK_RDY: [*] ONLINE"** — Takes ~15-30 seconds
3. **Click "AUTO_MISSION"** — Robot autonomously navigates: room_a → room_b → room_c → dock
4. **Click "TELEOP"** — Manual control using W/A/S/D keys or on-screen D-pad
5. **Click "EXPERIMENT"** → Enter number of trials → Runs N automated missions with CSV logging
6. **Click "SHUTDOWN"** — Stops everything cleanly

### 4.5 Running Experiments for Research

```bash
# Step 1: Launch the system
./run_project.sh

# Step 2: Click "EXPERIMENT" on dashboard, enter 10 trials
# Results saved to: ~/medguide_ws/logs/experiment_YYYYMMDD_HHMMSS.csv

# Step 3: Analyze results
python3 experiments/analyze_results.py \
    --tuned  logs/baseline.csv \
    --strict logs/velocity_040.csv \
    --output docs/results/

# This generates:
#   fig1_success_rate.png    — Bar chart of success rates
#   fig2_duration_boxplot.png — Duration distribution
#   fig3_distance_line.png   — Distance per trial
#   fig4_efficiency.png      — Path efficiency comparison
#   summary_stats.txt        — Statistical test results
```

### 4.6 Running Unit Tests

```bash
cd ~/medguide_ws
source install/setup.bash
colcon test --packages-select medguide_robot
colcon test-result --verbose
# 27 tests: mission state transitions, obstacle detection, PEP8, Flake8
```

---

## 5. REPOSITORY STRUCTURE

```
medguide_ws/
├── README.md                          ← Project overview & quick start
├── run_project.sh                     ← One-command launch script
├── .gitignore                         ← Excludes build/install/log from Git
│
├── experiments/
│   └── analyze_results.py             ← Statistical analysis (Mann-Whitney U + 4 plots)
│
├── docs/
│   ├── research_methodology.md        ← How experiments are designed
│   ├── experiment_protocol.md         ← Controlled experiment design
│   ├── experiment_runbook.md          ← Pre-trial checklist
│   ├── results_interpretation.md      ← DWB/Nav2 failure analysis
│   ├── follow_up_experiments.md       ← Future experiment designs
│   ├── final_synthesis.md             ← Research conclusions
│   ├── research_paper_structure.md    ← Full paper template (8 sections)
│   └── phd_portfolio_narrative.md     ← Portfolio narrative
│
├── logs/                              ← Experiment CSV output
│   ├── baseline.csv
│   ├── velocity_040.csv
│   ├── inflation_085.csv
│   └── planner_5hz.csv
│
├── maps/
│   ├── hospital_map.pgm               ← SLAM-generated occupancy grid
│   └── hospital_map.yaml              ← Map metadata
│
├── worlds/
│   └── hospital_floor.world           ← Custom Gazebo hospital environment
│
└── src/
    ├── medguide_msgs/                 ← Custom ROS2 message definitions
    │   ├── msg/
    │   │   ├── MissionStatus.msg
    │   │   ├── GoalResult.msg
    │   │   └── SystemState.msg
    │   └── srv/
    │       ├── SetMode.srv
    │       └── RunExperiment.srv
    │
    └── medguide_robot/                ← Main robot package
        ├── medguide_robot/            ← 6 Python ROS2 nodes
        │   ├── experiment_orchestrator_node.py
        │   ├── mission_scheduler_node.py
        │   ├── obstacle_detector_node.py
        │   ├── sensor_monitor_node.py
        │   ├── mission_logger_node.py
        │   └── diagnostics_node.py
        ├── scripts/
        │   ├── dashboard.py           ← PyQt5 sci-fi command console
        │   ├── orchestrator.py        ← Standalone orchestrator
        │   ├── run_experiment.py      ← Experiment runner script
        │   └── analyze_results.py     ← Per-trial analysis
        ├── config/
        │   ├── nav2_params.yaml       ← Nav2 tuning parameters
        │   ├── robot_params.yaml      ← Safety + mission parameters
        │   └── slam_params.yaml       ← SLAM configuration
        ├── launch/
        │   ├── medguide_full.launch.py ← Full stack launch
        │   ├── gazebo_sim.launch.py
        │   ├── nav2_navigation.launch.py
        │   └── slam_mapping.launch.py
        ├── worlds/
        │   └── hospital_floor.world
        └── test/                      ← Unit tests (27 total)
            ├── test_mission_states.py
            ├── test_obstacle_logic.py
            ├── test_flake8.py
            └── test_pep257.py
```

---

## 6. HOW EACH COMPONENT WORKS (TECHNICAL DEEP DIVE)

### 6.1 Obstacle Detection (Safety Layer)

The obstacle detector uses a **parametric cone filter** on the 360° LiDAR scan:
- Filters only the **front ±22.5°** of the robot (45° cone)
- Triggers **emergency stop** when closest obstacle < **0.18m** (robot radius ~0.10m)
- Uses **hysteresis** — clears stop only when obstacle > **0.25m** (prevents oscillation)
- Publishes to `/emergency_stop` (Bool) and `/obstacle_distance` (Float32)

### 6.2 Mission Scheduler (Navigation FSM)

The mission scheduler implements a **Hierarchical Finite State Machine (HFSM)**:

```
IDLE → NAVIGATING → (goal reached?) → next goal → ... → COMPLETED
          ↓                                    ↓
    EMERGENCY_STOP ←──── obstacle detected    FAILED
          ↓
    (cleared) → resume NAVIGATING
```

- Uses **Nav2 ActionClient** to send `NavigateToPose` goals
- Pre-defined coordinates for 4 hospital locations (room_a, room_b, room_c, dock)
- Publishes initial pose to AMCL before first goal for reliable localization
- **Retry mechanism**: If Nav2 rejects a goal, retries up to 3 times with 5s delay
- Tracks odometry distance, battery simulation, and path efficiency

### 6.3 Dashboard UI

The dashboard is a **PyQt5 application** with a sci-fi command console design:
- **System Link State** — Shows mode, stack status, localization, e-stop, battery
- **Mission Telemetry** — Waypoint progress, distance, time, interruptions
- **Dynamic Control Stage** — Switches between button controls and teleop D-pad
- **Terminal Results** — Mission completion reports
- **Event Log** — Timestamped system events

### 6.4 Experiment Orchestrator

Manages the complete system lifecycle:
- Launches Gazebo + Nav2 as subprocesses
- Monitors stack health (checks process liveness)
- Manages mode transitions (OFFLINE → LAUNCHING → IDLE → AUTONOMOUS → TELEOP)
- Handles experiment batches (N trials with automated restart between trials)

### 6.5 Data Collection Pipeline

```
Mission runs → mission_scheduler publishes GoalResult + MissionStatus
     ↓
mission_logger subscribes → writes JSON log per mission
     ↓
Experiment CSV output → one row per trial (time, distance, success, e-stops)
     ↓
analyze_results.py → Mann-Whitney U test → 4 publication plots + summary_stats.txt
```

---

## 7. ROS2 CONCEPTS DEMONSTRATED

This project demonstrates mastery of the following ROS2 concepts:

| Concept | Where Used |
|---|---|
| **Custom Message Design** | `medguide_msgs/` — 3 messages + 2 services |
| **Action Client/Server** | `mission_scheduler` → Nav2 `NavigateToPose` |
| **Service Calls** | `/start_mission`, `/abort_mission`, `/set_mode` |
| **Topic Pub/Sub** | `/system_state`, `/mission_status`, `/scan`, `/odom`, etc. |
| **QoS Profiles** | BEST_EFFORT for sensors, RELIABLE for commands |
| **Launch File Composition** | `medguide_full.launch.py` includes Gazebo + Nav2 + nodes |
| **Parameter Declaration** | YAML configs loaded via `declare_parameter()` |
| **State Machine Design** | Orchestrator FSM + Mission Scheduler HFSM |
| **Lifecycle Management** | Subprocess launch/teardown of Nav2 + Gazebo |
| **Safety Systems** | Emergency stop with hysteresis + obstacle detection |
| **Simulation** | Gazebo world + TurtleBot3 + LiDAR + odometry |
| **SLAM** | `slam_toolbox` with custom parameters for map generation |
| **Localization** | AMCL with initial pose estimation |
| **Navigation** | Nav2 with DWB controller, costmap, behavior tree |
| **Unit Testing** | `colcon test` with pytest, flake8, pep257 |
| **Data Logging** | JSON + CSV logging for experiment analysis |
| **Statistical Analysis** | Mann-Whitney U, confidence intervals, effect sizes |

---

## 8. HOW TO RECREATE THIS PROJECT FROM SCRATCH

### Step 1: Create ROS2 Workspace
```bash
mkdir -p ~/medguide_ws/src
cd ~/medguide_ws
```

### Step 2: Create Custom Messages Package
```bash
cd src
ros2 pkg create medguide_msgs --build-type ament_cmake
# Define .msg and .srv files in msg/ and srv/ directories
# Update CMakeLists.txt to generate message code
```

### Step 3: Create Robot Package
```bash
ros2 pkg create medguide_robot --build-type ament_python \
    --dependencies rclpy std_msgs geometry_msgs nav_msgs sensor_msgs
```

### Step 4: Implement Nodes
Write Python nodes in `medguide_robot/medguide_robot/`:
- Start with `sensor_monitor` (simplest — just subscribes to /scan and /odom)
- Then `obstacle_detector` (subscribes to /scan, publishes /emergency_stop)
- Then `mission_scheduler` (uses Nav2 action client)
- Then `experiment_orchestrator` (manages subprocess lifecycle)
- Then `mission_logger` and `diagnostics` (aggregation nodes)

### Step 5: Configure Nav2
- Copy Nav2 default params and tune for your environment
- Set AMCL initial pose matching your map
- Configure DWB controller velocities and tolerances

### Step 6: Create Gazebo World
- Build a hospital-like environment in Gazebo
- Generate a map using SLAM (`slam_toolbox`)
- Save map to `maps/` directory

### Step 7: Build & Test
```bash
cd ~/medguide_ws
colcon build
source install/setup.bash
colcon test --packages-select medguide_robot
```

---

## 9. TROUBLESHOOTING

| Issue | Cause | Solution |
|---|---|---|
| `colcon build` fails | Missing dependencies | `sudo apt install ros-humble-turtlebot3*` |
| Gazebo won't start | Display/GPU issues | `export LIBGL_ALWAYS_SOFTWARE=1` |
| Nav2 goals rejected | AMCL not converged | Wait for initial pose estimation |
| Robot doesn't move | E-stop triggered | Check obstacle distance, clear path |
| Mission T=0.0s | Nav2 not ready | System auto-retries 3 times with 5s delay |
| IDE shows errors | Pyre2 extension | Disable Pyre2 in VS Code (all errors are false positives) |

---

## 10. SUMMARY

MedGuide-ROS is a complete, research-grade autonomous delivery robot system that:

1. **Runs in simulation** — no physical hardware needed
2. **Navigates autonomously** — 4-room delivery missions via Nav2
3. **Detects obstacles** — LiDAR-based safety with emergency stop
4. **Collects research data** — automated experiment pipeline with CSV logging
5. **Produces statistics** — Mann-Whitney U tests with publication-quality plots
6. **Has a polished UI** — sci-fi command console dashboard
7. **Is fully tested** — 27 unit tests, PEP8/Flake8 compliance
8. **Is documented** — 7 research documents + full README

**Developer:** Pragadeesh  
**GitHub:** https://github.com/Sentrix-wiz/Medguide-ROS  
**Framework:** ROS2 Humble + Nav2 + Gazebo + PyQt5  
**Academic Citation:** *Pragadeesh, "MedGuide-ROS: Autonomous Hospital Delivery Robot," 2026.*

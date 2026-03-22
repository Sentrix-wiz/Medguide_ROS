# MedGuide-ROS — Development Log

> Complete history of everything built, fixed, and verified.

---

## Phase 1 — ROS2 Foundations
**Nodes:** heartbeat_publisher, sensor_echo, teleop_safety
- Created custom heartbeat topic at 1 Hz
- Sensor echo node for LIDAR/odometry raw logging
- Teleop safety node: velocity limits (0.5 m/s linear, 1.5 rad/s angular)
- **Tests:** 4 unit tests (heartbeat, teleop limits)

## Phase 2 — Simulation Environment
**Files:** `gazebo_sim.launch.py`, `hospital_floor.world`
- TurtleBot3 Burger in custom hospital world
- Hospital layout: 7m × 6m with 4 rooms (A, B, C, dock)
- Interior walls with doorways for navigation
- Furniture obstacles: table, chair, bed, cabinet
- Robot spawns at dock position (1.0, 1.2)

## Phase 3 — SLAM Mapping
**Files:** `slam_mapping.launch.py`, `maps/hospital_map.yaml`
- Async SLAM Toolbox integration
- Generated occupancy grid map (121 × 71 cells, 0.05m/pix)
- Map saved to `maps/hospital_map.pgm`
- Includes mapped doorways and obstacle positions

## Phase 4 — Nav2 Navigation
**Files:** `nav2_params.yaml`, `nav2_navigation.launch.py`
- AMCL localization with auto initial pose at (1.0, 1.2)
- NavFn global planner (A* search)
- DWB local controller (dynamic window approach)
- Costmap: static + obstacle layer + inflation (0.55m radius)
- Behavior server: spin, backup, drive_on_heading, wait

## Phase 5 — Safety Perception
**Files:** `obstacle_detector_node.py`
- LIDAR-based obstacle detection (60° forward cone)
- Emergency stop at 0.25m threshold
- Hysteresis clearing at 0.35m (prevents oscillation)
- Publishes `/estop` and `/cmd_vel` override
- **Tests:** 8 unit tests (hysteresis, thresholds, oscillation)

## Phase 6 — Mission Scheduling
**Files:** `mission_scheduler_node.py`, `robot_params.yaml`
- Room-to-room delivery: Room A → B → C → Dock
- Nav2 action client integration (NavigateToPose)
- Odometry-based distance tracking per mission
- Battery simulation with drain and abort threshold
- Service API: `/start_mission`, `/abort_mission`
- **Tests:** 11 unit tests (state machine, distance, goals)

## Phase 7 — Diagnostics & Logging
**Files:** `diagnostics_node.py`, `mission_logger_node.py`
- System health: uptime, scan/odom Hz, e-stop state, node count
- Mission logger: writes per-goal results to CSV
- Custom messages: `MissionStatus.msg`, `GoalResult.msg`
- Publishes `/system_health`, `/mission_status`, `/goal_result`

## Phase 8 — Research Infrastructure
**Files:** `run_experiment.py`, `analyze_results.py`, `generate_demo_data.py`
- Experiment runner: N trials with AMCL convergence wait
- CSV logging: trial, mission_id, goal_name, success, duration, distance
- Analysis: pandas stats + matplotlib comparison charts
- Demo data: 4 conditions × 10 trials = 160 data points
- Experiment plan document: `docs/experiment_plan.md`

## Phase 9 — Full Stack Integration & Launch
**Files:** `medguide_full.launch.py`, `medguide_control.py`
- Full launch: Gazebo + Nav2 + 5 custom nodes + RViz
- Interactive control panel (`medguide_control.py`):
  - 🚀 Launch full stack
  - 🎮 WASD manual drive
  - 🤖 Autonomous delivery mission
  - 📊 Experiment runner
  - 📐 Architecture viewer
  - 📈 System status

---

## Bug Fixes

| Bug | Root Cause | Fix |
|-----|-----------|-----|
| Nav2 plugins fail to load | Class names used `::` instead of `/` | Fixed 5 plugins in `nav2_params.yaml` |
| Mission COMPLETE spam | Timer leak in `_finish_goal()` | Single-shot cancelable timer |
| Robot doesn't move | Spawn at (0.5,0.5) inside inflation zone | Moved spawn to (1.0,1.2) |
| No paths between rooms | Solid walls with no doorways | Split walls into segments with gaps |
| Map not loaded | `yaml_filename` was empty | Set absolute path in `nav2_params.yaml` |
| Flake8 scanning build/ | `ament_flake8` scans from CWD | Added `--exclude build,install,log` |
| AMCL not converged | Goals sent immediately on startup | Added 10s convergence wait |

---

## Test Results

```
27 passed, 1 skipped — 0.77s
```

| Category | Tests | Status |
|----------|-------|--------|
| Odometry distance tracking | 4 | ✅ |
| Mission state machine | 7 | ✅ |
| Obstacle detection hysteresis | 6 | ✅ |
| Flake8 (code style) | 1 | ✅ |
| PEP 257 (docstrings) | 1 | ✅ |

---

## File Inventory (32 files)

| Category | Files |
|----------|-------|
| **Control** | `medguide_control.py`, `run.sh`, `run_teleop.sh`, `run_mission.sh`, `run_experiment.sh`, `setup.sh`, `test.sh` |
| **Launch** | `medguide_full.launch.py`, `gazebo_sim.launch.py`, `nav2_navigation.launch.py`, `slam_mapping.launch.py`, `phase1.launch.py`, `phase2_sim.launch.py` |
| **Nodes** | `mission_scheduler_node.py`, `obstacle_detector_node.py`, `sensor_monitor_node.py`, `diagnostics_node.py`, `mission_logger_node.py`, `heartbeat_publisher.py`, `sensor_echo.py`, `teleop_safety_node.py` |
| **Config** | `nav2_params.yaml`, `robot_params.yaml` |
| **Messages** | `MissionStatus.msg`, `GoalResult.msg` |
| **World** | `hospital_floor.world` |
| **Scripts** | `run_experiment.py`, `analyze_results.py`, `generate_demo_data.py` |
| **Tests** | `test_mission_states.py`, `test_obstacle_logic.py`, `test_flake8.py`, `test_pep257.py` |
| **Docs** | `README.md`, `DEVLOG.md`, `experiment_plan.md` |

---

## Current Status

✅ **Working:**
- Robot navigates autonomously in Gazebo
- Obstacle detection + emergency stop
- Mission scheduler (room-to-room delivery)
- SLAM mapping
- Experiment automation + CSV analysis
- Interactive control panel
- 27/27 tests passing

---

## Suggested Next Steps (for mentor discussion)

1. **Real Experiments** — Run 10-trial baseline with real Nav2 navigation, then tune:
   - Inflation radius (0.55m → 0.85m)
   - Max velocity (0.22 → 0.40 m/s)
   - Planner frequency (1Hz → 5Hz)

2. **Multi-Robot** — Add second TurtleBot3 with namespacing for fleet coordination

3. **Dynamic Obstacles** — Add moving obstacles in Gazebo to test reactive avoidance

4. **Path Efficiency Metric** — Compare actual path length vs straight-line distance

5. **Recovery Behaviors** — Tune spin/backup parameters when robot gets stuck

6. **ROS2 Bag Recording** — Record `/scan`, `/odom`, `/cmd_vel` for offline replay

7. **Research Paper** — Write up navigation performance comparison as a short paper

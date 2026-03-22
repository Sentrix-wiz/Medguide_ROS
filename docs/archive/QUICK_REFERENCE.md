# MedGuide-ROS Quick Reference

## 🚀 Build & Setup

```bash
# Build entire workspace
cd ~/medguide_ws
colcon build --symlink-install

# Build single package
colcon build --packages-select medguide_tasks

# Verify build
ls -lh install/lib/medguide_*/
```

## ▶️ Launch System

```bash
# Source environment (ALWAYS first!)
source ~/medguide_ws/install/setup.bash

# Launch everything (⭐ recommended)
ros2 launch medguide_bringup unified.launch.py

# Launch with custom settings
ros2 launch medguide_bringup unified.launch.py \
    use_sim_time:=true \
    launch_gazebo:=true \
    log_level:=DEBUG

# Launch individual systems
ros2 launch medguide_bringup gazebo_bringup.launch.py
ros2 launch medguide_bringup nav2_bringup.launch.py
ros2 launch medguide_bringup medguide_perception.launch.py
ros2 launch medguide_bringup medguide_navigation.launch.py
ros2 launch medguide_bringup medguide_tasks.launch.py
```

## 🎯 Run Individual Nodes

```bash
# Perception
ros2 run medguide_perception obstacle_detector

# Navigation  
ros2 run medguide_navigation navigation_goal_sender

# Task Management
ros2 run medguide_tasks mission_scheduler

# Legacy Status
ros2 run medguide_robot robot_status
```

## 📊 Monitor & Test

```bash
# Real-time mission monitor
python3 ~/medguide_ws/scripts/monitor_mission.py

# Obstacle distance monitor
python3 ~/medguide_ws/scripts/monitor_emergency_stop.py

# Automated mission test (CSV output)
python3 ~/medguide_ws/scripts/test_mission.py \
    --output results.csv \
    --loops 5 \
    --timeout 180

# Test with specific goals
python3 ~/medguide_ws/scripts/test_mission.py \
    --loops 1 \
    --timeout 300
```

## 🐳 Docker Commands

```bash
# Build image
./docker-helper.sh build

# Run interactive shell
./docker-helper.sh run

# Launch full system in container
./docker-helper.sh launch

# Run mission test in container
./docker-helper.sh test

# Monitor mission from container
docker run -it --rm --network host medguide-ros:humble-latest bash -c \
    "source install/setup.bash && python3 scripts/monitor_mission.py"

# Stop and clean
./docker-helper.sh stop
./docker-helper.sh clean
```

## 📡 ROS 2 Topics & Commands

```bash
# List all topics
ros2 topic list

# Subscribe to mission status (live)
ros2 topic echo /mission_status

# Check obstacle distance
ros2 topic echo /obstacle_distance

# View emergency stop state
ros2 topic echo /emergency_stop

# LaserScan data
ros2 topic echo /scan

# View robot odometry
ros2 topic echo /odom

# Get topic info
ros2 topic info /mission_status
ros2 topic info /emergency_stop

# Monitor all topic traffic
ros2 topic hz /scan /mission_status /emergency_stop
```

## 🔍 Debugging

```bash
# View node graph (in new terminal)
ros2 run rqt_graph rqt_graph

# Run RViz (in new terminal)
rviz2 -d ~/medguide_ws/rviz/medguide_simulation.rviz

# List all running nodes
ros2 node list

# Get node info
ros2 node info /mission_scheduler
ros2 node info /obstacle_detector
ros2 node info /navigation_goal_sender

# Verbose node logging
ros2 run medguide_tasks mission_scheduler \
    --ros-args --log-level DEBUG

# Record bag (rosbag2)
ros2 bag record /mission_status /emergency_stop /obstacle_distance \
    -o medguide_mission_recording

# Play bag
ros2 bag play medguide_mission_recording/

# Check ROS 2 environment
ros2 doctor
```

## 📁 Key Files

```bash
# Main orchestrator
src/medguide_bringup/launch/unified.launch.py

# Configuration files
config/mission_params.yaml              # Room definitions
config/perception_params.yaml           # Obstacle thresholds
config/nav2_params_hospital.yaml        # Nav2 settings
config/task_params.yaml                 # Task scheduling
config/system_config.yaml               # Global settings

# Gazebo simulation
worlds/hospital_floor.world

# RViz configuration
rviz/medguide_simulation.rviz

# Core nodes
src/medguide_perception/medguide_perception/obstacle_detector_node.py
src/medguide_navigation/medguide_navigation/navigation_goal_sender_node.py
src/medguide_tasks/medguide_tasks/mission_scheduler_node.py

# Testing/monitoring
scripts/test_mission.py
scripts/monitor_mission.py
scripts/monitor_emergency_stop.py
```

## 🔧 Common Troubleshooting

```bash
# Build failed? Clean and rebuild
rm -rf build/ install/ log/
colcon build --symlink-install

# Can't find package?
source install/setup.bash
ros2 pkg list | grep medguide

# Node won't start?
ros2 launch -d medguide_bringup unified.launch.py  # verbose

# Topics not available?
ros2 topic list
ros2 topic info /mission_status

# Check sensor data
ros2 topic echo /scan  # LaserScan values should not be 'inf'

# Help with ros2 commands
ros2 -h
ros2 launch -h
ros2 run -h
ros2 topic -h
```

## ⚙️ Configuration Quick Changes

```bash
# Change obstacle threshold (edit this file)
nano config/perception_params.yaml
# Change: obstacle_threshold_m: 0.3

# Add new mission goal (edit)
nano config/mission_params.yaml
# Add room under hospital_rooms section

# Change Nav2 parameters (edit)
nano config/nav2_params_hospital.yaml
# Adjust costmap, planner, controller settings
```

## 📈 Viewing Results

```bash
# After running test_mission.py, view CSV
cat medguide_mission_test_results.csv

# Parse results
head -n5 medguide_mission_test_results.csv
tail -n3 medguide_mission_test_results.csv

# Count successes
grep "mission_complete" medguide_mission_test_results.csv | wc -l
```

## 🎓 Learning Path

1. **Understand structure**: `tree -L 2 src/`
2. **Read docs**: `less README.md`
3. **Launch system**: `ros2 launch medguide_bringup unified.launch.py`
4. **Monitor topics**: `ros2 topic list` & `ros2 topic echo /mission_status`
5. **Run test**: `python3 scripts/test_mission.py --loops 1`
6. **Modify**: Edit `config/*.yaml` and re-run
7. **Extend**: Add nodes to `src/medguide_*/` packages

---

**Last Updated:** March 18, 2026  
**ROS Version:** Humble  
**Python:** 3.10+  
**Status:** ✅ Production Ready

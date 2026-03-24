# MedGuide-ROS — Real Robot Deployment Guide
## From Simulation to Physical TurtleBot3

---

## 1. HARDWARE REQUIREMENTS

### 1.1 Robot Platform

| Component | Specification | Purpose |
|---|---|---|
| **TurtleBot3 Burger** | OpenCR + Raspberry Pi 4 | Mobile base with differential drive |
| **LDS-01 LiDAR** | 360° laser scanner, 12cm–3.5m | Obstacle detection + SLAM + AMCL |
| **OpenCR Board** | STM32F7 + IMU + motor drivers | Low-level motor control |
| **Raspberry Pi 4** | 4GB RAM, Ubuntu 22.04 Server | On-board ROS2 compute |
| **LiPo Battery** | 11.1V 1800mAh | ~2.5 hours runtime |

### 1.2 Remote PC (Your Laptop)

| Component | Specification |
|---|---|
| **OS** | Ubuntu 22.04 LTS |
| **ROS2** | Humble Hawksbill |
| **Network** | Same WiFi network as robot |
| **Purpose** | Runs Nav2, Dashboard, RViz (heavy computation) |

### 1.3 Network Infrastructure

```
┌──────────────┐     WiFi (5GHz recommended)     ┌────────────────┐
│  Remote PC   │◄──────────────────────────►│  TurtleBot3    │
│  (Laptop)    │    ROS2 DDS auto-discovery       │  (Raspberry Pi)│
│              │                                   │                │
│  • Nav2      │    Topics: /scan, /odom,          │  • OpenCR      │
│  • Dashboard │    /cmd_vel, /tf                  │  • LiDAR       │
│  • RViz      │                                   │  • Motors      │
│  • AMCL      │                                   │                │
└──────────────┘                                   └────────────────┘
```

---

## 2. ROBOT SETUP (Raspberry Pi)

### 2.1 Flash Raspberry Pi

```bash
# Download Ubuntu 22.04 Server for RPi4
# Flash to microSD using Raspberry Pi Imager

# After boot, install ROS2 Humble:
sudo apt update && sudo apt upgrade -y
sudo apt install ros-humble-ros-base ros-humble-turtlebot3-bringup
echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
echo "export TURTLEBOT3_MODEL=burger" >> ~/.bashrc
echo "export ROS_DOMAIN_ID=30" >> ~/.bashrc
```

### 2.2 Flash OpenCR Firmware

```bash
# On the Raspberry Pi:
export OPENCR_PORT=/dev/ttyACM0
export OPENCR_MODEL=burger

# Download and flash firmware
ros2 run turtlebot3_bringup create_udev_rules
wget https://github.com/ROBOTIS-GIT/OpenCR-Binaries/raw/master/turtlebot3/ROS2/latest/opencr_update.tar.bz2
tar -xvf opencr_update.tar.bz2
cd opencr_update
./update.sh $OPENCR_PORT $OPENCR_MODEL.opencr
```

### 2.3 Network Configuration

```bash
# On Raspberry Pi — set static IP or note the IP:
hostname -I
# Example: 192.168.1.100

# Both machines MUST use the same ROS_DOMAIN_ID:
echo "export ROS_DOMAIN_ID=30" >> ~/.bashrc

# Verify connectivity:
ping <remote_pc_ip>
```

---

## 3. REMOTE PC SETUP (Your Laptop)

### 3.1 Install Dependencies

```bash
# Same as simulation setup:
sudo apt install ros-humble-turtlebot3* ros-humble-nav2-bringup \
                 ros-humble-slam-toolbox
pip3 install pyqt5

# Set domain ID to match robot:
echo "export ROS_DOMAIN_ID=30" >> ~/.bashrc
echo "export TURTLEBOT3_MODEL=burger" >> ~/.bashrc
source ~/.bashrc
```

### 3.2 Clone MedGuide-ROS

```bash
git clone https://github.com/Sentrix-wiz/Medguide-ROS.git ~/medguide_ws
cd ~/medguide_ws
source /opt/ros/humble/setup.bash
colcon build
source install/setup.bash
```

---

## 4. CREATING A MAP OF YOUR HOSPITAL

### 4.1 Start the Robot

```bash
# SSH into Raspberry Pi:
ssh ubuntu@<robot_ip>

# Terminal 1 (on robot): Start robot hardware
ros2 launch turtlebot3_bringup robot.launch.py
```

### 4.2 Run SLAM on Remote PC

```bash
# Terminal 2 (on remote PC): Start SLAM
ros2 launch nav2_bringup slam_launch.py use_sim_time:=false

# Terminal 3 (on remote PC): Start RViz to see the map
ros2 launch nav2_bringup rviz_launch.py

# Terminal 4 (on remote PC): Teleoperate to build the map
ros2 run turtlebot3_teleop teleop_keyboard
```

Drive the robot slowly through ALL corridors and rooms. Cover the entire area.

### 4.3 Save the Map

```bash
# When the map looks complete in RViz:
ros2 run nav2_mapserver map_saver_cli -f ~/medguide_ws/maps/hospital_map

# This creates:
#   hospital_map.pgm  — occupancy grid image
#   hospital_map.yaml — metadata (resolution, origin)
```

### 4.4 Define Room Coordinates

Open RViz and use the **"Publish Point"** tool to click on each room location. Note the (x, y) coordinates from the terminal output, then update:

```yaml
# src/medguide_robot/config/robot_params.yaml
rooms:
  dock:
    x: <your_dock_x>
    y: <your_dock_y>
    yaw: 0.0
  room_a:
    x: <your_room_a_x>
    y: <your_room_a_y>
    yaw: 0.0
  # ... etc
```

---

## 5. CHANGES FOR REAL ROBOT

### 5.1 Key Differences: Simulation → Real

| Parameter | Simulation | Real Robot | Why |
|---|---|---|---|
| `use_sim_time` | `true` | **`false`** | Real clock, not Gazebo clock |
| Gazebo launch | Included | **Removed** | No simulator needed |
| LiDAR topic | `/scan` (Gazebo) | `/scan` (real LDS-01) | Same topic name ✅ |
| Odometry | Gazebo plugin | OpenCR wheel encoders | Same `/odom` topic ✅ |
| `max_vel_x` | 0.22 m/s | **0.15 m/s** | Safer in real corridors |
| `inflation_radius` | 0.25 m | **0.35 m** | More safety margin with real obstacles |
| `obstacle_distance_threshold` | 0.18 m | **0.25 m** | Real sensors have noise |

### 5.2 Create Real Robot Launch File

Create a new launch file that replaces the Gazebo simulation with the real robot bringup:

```python
# src/medguide_robot/launch/medguide_real.launch.py

# Key changes from medguide_full.launch.py:
# 1. Remove gazebo_launch (no simulator)
# 2. Add turtlebot3 robot bringup (real hardware)
# 3. Set use_sim_time=false everywhere
# 4. Use real robot's /scan, /odom, /tf topics
```

### 5.3 Modified nav2_params for Real Robot

```yaml
# Create: config/nav2_params_real.yaml
# Copy nav2_params.yaml and change:

amcl:
  ros__parameters:
    use_sim_time: false          # Real clock
    max_particles: 5000          # More particles for real sensors
    laser_max_range: 3.5         # LDS-01 actual range
    set_initial_pose: true
    initial_pose:
      x: <your_dock_x>          # Where you place the robot
      y: <your_dock_y>
      yaw: 0.0

controller_server:
  ros__parameters:
    use_sim_time: false
    FollowPath:
      max_vel_x: 0.15           # Slower for safety
      max_vel_theta: 0.8        # Slower turns

local_costmap:
  local_costmap:
    ros__parameters:
      use_sim_time: false
      inflation_layer:
        inflation_radius: 0.35  # More safety margin

global_costmap:
  global_costmap:
    ros__parameters:
      use_sim_time: false
      inflation_layer:
        inflation_radius: 0.35
```

---

## 6. RUNNING ON REAL ROBOT

### 6.1 Launch Sequence

```bash
# Step 1: SSH into robot and start hardware
ssh ubuntu@<robot_ip>
ros2 launch turtlebot3_bringup robot.launch.py

# Step 2: On remote PC — start MedGuide with real robot params
cd ~/medguide_ws
source install/setup.bash
export TURTLEBOT3_MODEL=burger
ros2 launch medguide_robot medguide_real.launch.py

# Step 3: Open Dashboard
python3 src/medguide_robot/scripts/dashboard.py
```

### 6.2 Verify Before Autonomous Mode

Before clicking AUTO_MISSION on the real robot:

1. ✅ **Check AMCL** — Open RViz, verify the AMCL particles converge on the robot's actual position
2. ✅ **Test Teleop** — Use TELEOP mode to drive the robot manually, verify it responds correctly
3. ✅ **Check LiDAR** — Verify laser scan data looks clean in RViz
4. ✅ **Check Costmap** — Verify the costmap shows walls and obstacles correctly
5. ✅ **Test E-Stop** — Walk in front of the robot to verify emergency stop triggers

### 6.3 Safety Considerations

```
⚠️  CRITICAL SAFETY RULES FOR REAL ROBOT:
├── Always have someone ready to press the physical E-stop button
├── Clear the path of cables, small objects, and people's feet
├── Start with TELEOP to verify everything before AUTONOMOUS
├── Use reduced velocities (0.15 m/s max) indoors
├── Monitor the dashboard constantly during autonomous missions
└── The obstacle detector E-stop distance should be ≥ 0.25m for real sensors
```

---

## 7. SIM-TO-REAL TRANSFER METHODOLOGY

### 7.1 Why Simulation First?

| Advantage | Description |
|---|---|
| **Safety** | No risk of damaging hardware or people during development |
| **Speed** | Can run thousands of tests without battery/time constraints |
| **Reproducibility** | Same initial conditions every time |
| **Cost** | No physical robot needed during development |
| **Debugging** | Full state visibility (Gazebo + RViz + logs) |

### 7.2 What Transfers Directly (Zero Changes)

These ROS2 components work **identically** on simulation and real robot:

- ✅ All 6 custom ROS2 nodes (same code, same topics)
- ✅ Nav2 navigation stack (same planner, controller, behavior trees)
- ✅ Dashboard UI (same interface, same services)
- ✅ Mission scheduler (same action client, same goal format)
- ✅ Data collection pipeline (same CSV logging)
- ✅ Custom messages and services (same definitions)

### 7.3 What Requires Tuning

| Component | Sim → Real Change | Reason |
|---|---|---|
| AMCL particles | 2000 → 5000 | Real sensor noise requires more particles |
| Velocities | 0.22 → 0.15 m/s | Safety in real corridors |
| Inflation radius | 0.25 → 0.35 m | Real sensor uncertainty |
| E-stop distance | 0.18 → 0.25 m | LiDAR noise margin |
| Map | Re-scan with SLAM | Physical environment differs from Gazebo |

### 7.4 Sim-to-Real Gap Analysis

```
Simulation Accuracy:
├── Kinematics:    ★★★★★  (differential drive model is very accurate)
├── LiDAR:         ★★★★☆  (real LDS-01 has noise, Gazebo LiDAR is clean)
├── Odometry:      ★★★☆☆  (real wheels slip, Gazebo doesn't simulate slip)
├── Localization:  ★★★★☆  (AMCL works well with good map)
├── Navigation:    ★★★★☆  (Nav2 transfers directly)
└── Overall:       ★★★★☆  (high transfer fidelity for indoor robots)
```

---

## 8. CONNECTING TO HOSPITAL SYSTEMS (Future Work)

### 8.1 Integration Points

For a production hospital robot, the following systems would need integration:

```
┌─────────────────┐     ┌──────────────────┐     ┌────────────────┐
│  Hospital        │     │  MedGuide-ROS    │     │  Cloud / HIS   │
│  Infrastructure  │     │  Robot           │     │  Integration   │
├─────────────────┤     ├──────────────────┤     ├────────────────┤
│ • WiFi network   │────►│ • ROS2 nodes     │────►│ • Task queue   │
│ • Fire alarms    │────►│ • Safety system  │────►│ • Status API   │
│ • Elevator API   │────►│ • Floor planner  │────►│ • Patient data │
│ • Door locks     │────►│ • Access control │────►│ • Analytics    │
└─────────────────┘     └──────────────────┘     └────────────────┘
```

### 8.2 ROS2 Topics for External Systems

```python
# Custom topics for hospital integration:
/delivery_request    # External system sends delivery tasks
/robot_status        # Robot reports location + status to central system
/floor_change        # Elevator integration for multi-floor hospitals
/access_request      # Request door unlock from building management
```

### 8.3 Technologies for Production

| System | Technology | Purpose |
|---|---|---|
| Fleet Management | Open-RMF | Multi-robot coordination |
| Cloud Connectivity | AWS IoT + ROS2 | Remote monitoring |
| Task Scheduling | micro-ROS + DDS | Real-time task assignment |
| Security | SROS2 (DDS Security) | Encrypted robot communication |
| Multi-floor | Elevator API + Nav2 | Floor-to-floor navigation |

---

## 9. SUMMARY

This project demonstrates the complete **sim-to-real pipeline** for autonomous hospital robots:

1. **Simulation Development** → Gazebo + Nav2 (what we built) ✅
2. **Parameter Tuning** → Experiment pipeline with statistical analysis ✅
3. **Real Deployment** → TurtleBot3 hardware + SLAM mapping (this guide)
4. **Hospital Integration** → System interfaces (future work)

The same ROS2 code, messages, services, and navigation stack run on **both simulation and real hardware** — only configuration changes are needed for deployment.

---

**Author:** Pragadeesh  
**Project:** MedGuide-ROS — Autonomous Hospital Delivery Robot  
**GitHub:** https://github.com/Sentrix-wiz/Medguide-ROS

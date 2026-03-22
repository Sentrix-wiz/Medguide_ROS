# Research Methodology — MedGuide-ROS

## Experimental Setup

| Parameter | Value |
|-----------|-------|
| Robot platform | TurtleBot3 Burger (simulation) |
| Simulator | Gazebo 11 |
| Navigation stack | Nav2 (AMCL + DWB controller) |
| Map | Hospital floor (10×10m, generated via slam_toolbox) |
| PC requirements | 8–16GB RAM, ROS2 Humble, Ubuntu 22.04 |

## Running Reproducible Experiments

### 1. Launch the full stack
```bash
cd ~/medguide_ws
source install/setup.bash
export TURTLEBOT3_MODEL=burger
ros2 launch medguide_robot medguide_full.launch.py
```

### 2. Set initial pose in RViz2
Click **2D Pose Estimate** and place the robot at the dock position.

### 3. Run experiment trials
```bash
# Default: 3 trials → ~/medguide_ws/logs/experiment_results.csv
python3 src/medguide_robot/scripts/run_experiment.py --trials 5
```

### 4. Run unit tests
```bash
colcon test --packages-select medguide_robot
colcon test-result --verbose
```

## Metrics Collected

| Metric | Source | Unit |
|--------|--------|------|
| Success rate | GoalResult.success | % |
| Time to goal | GoalResult.duration_sec | seconds |
| Distance traveled | Odometry accumulation | meters |
| Emergency stops | MissionStatus.emergency_stops | count |
| Battery consumption | Battery simulation | % |

## Interpreting Results

- **Success rate < 90%**: Check map accuracy, AMCL localization, or costmap tuning
- **High time variance**: Indicates path planning inconsistency — tune DWB tolerances
- **Distance >> straight-line**: Obstacle avoidance causing detours — check inflation radius
- **Frequent e-stops**: Reduce obstacle_threshold_m or widen the obstacle filter cone

## Presenting in a Paper or Portfolio

### Suggested table format:
```
| Trial | Goals | Success | Avg Time (s) | Distance (m) | E-stops |
|-------|-------|---------|-------------|--------------|---------|
| 1     | 4     | 100%    | 23.4        | 12.8         | 0       |
| 2     | 4     | 75%     | 31.2        | 14.1         | 1       |
| ...   | ...   | ...     | ...         | ...          | ...     |
```

### Key claims you can make:
1. "The system achieves X% navigation success rate across N trials"
2. "Emergency stop integration reduced collision events to zero"
3. "Mean goal-reaching time of X seconds with Y meters path efficiency"
4. "Custom ROS2 message interfaces enable reproducible metric collection"

### ROS2 concepts demonstrated:
- Custom message design (`medguide_msgs`)
- Action client/server pattern (Nav2)
- Service-based mission control
- Sensor QoS configuration
- Launch file composition
- Parameterized configuration (YAML)
- State machine architecture
- Safety-critical real-time systems (emergency stop)

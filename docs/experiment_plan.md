# MedGuide-ROS — Experiment Plan

## Experiment 1: Navigation Performance Under Parameter Variation

### Hypothesis

> Tuning Nav2 controller and planner parameters significantly affects
> mission completion rate, goal-reaching time, and path efficiency
> in a simulated hospital environment.

---

### Baseline Configuration

Use the **default nav2_params.yaml** as baseline (Condition A):

| Parameter | Baseline Value | File Location |
|-----------|---------------|---------------|
| `inflation_radius` | 0.55 m | `nav2_params.yaml` → costmap |
| `max_vel_x` | 0.22 m/s | `nav2_params.yaml` → DWB controller |
| `planner_frequency` | 1.0 Hz | `nav2_params.yaml` → planner server |
| Mission route | room_a → room_b → room_c → dock | `robot_params.yaml` |

---

### Parameters to Tune (3 Conditions)

#### Condition B — Larger Inflation Radius (0.85 m)

```yaml
# nav2_params.yaml → local_costmap / global_costmap
inflation_layer:
  inflation_radius: 0.85   # baseline: 0.55
```

**Expected effect:** Robot keeps more distance from walls. Safer paths
but may fail in narrow corridors. Longer path lengths. Fewer emergency stops.

#### Condition C — Higher Max Velocity (0.40 m/s)

```yaml
# nav2_params.yaml → FollowPath (DWB controller)
FollowPath:
  max_vel_x: 0.40          # baseline: 0.22
  max_speed_xy: 0.40
```

**Expected effect:** Faster goal completion. Higher risk of overshooting
and emergency stops. Shorter mission durations but potentially lower
success rate due to difficulty stopping in time.

#### Condition D — Higher Planner Frequency (5.0 Hz)

```yaml
# nav2_params.yaml → planner_server
planner_server:
  expected_planner_frequency: 5.0   # baseline: 1.0
```

**Expected effect:** More responsive path replanning. Better obstacle
avoidance but higher CPU usage. Should improve success rate in
dynamic environments with minimal time penalty.

---

### Trial Design

| Item | Value | Justification |
|------|-------|---------------|
| Trials per condition | **10** | Minimum for computing reliable mean + std |
| Total trials | **40** | 4 conditions × 10 trials |
| Mission per trial | 4 goals | room_a → room_b → room_c → dock |
| Data points | **160** | 40 trials × 4 goals each |
| Reset between trials | Respawn robot at dock | Consistent starting pose |

> **Why 10 trials?** In robotics simulation research, 10–30 trials per
> condition is standard. With 10 trials we get meaningful mean/std while
> keeping total experiment time under 2 hours.

---

### Metrics to Collect

| Metric | Source | Formula |
|--------|--------|---------|
| **Success rate** | `GoalResult.success` | `successes / total_goals × 100` |
| **Avg duration** | `GoalResult.duration_sec` | `mean(duration)` for successful goals |
| **Path efficiency** | `GoalResult.distance_m` vs straight-line | `straight_line / actual_distance` |
| **E-stop frequency** | `MissionStatus.emergency_stops` | `e_stops / trial_count` |
| **Battery usage** | `MissionStatus.battery_pct` | `start_pct - end_pct` |

**Straight-line distances** (from robot_params.yaml):

| Route Segment | dx | dy | Straight-line |
|--------------|-----|-----|---------------|
| dock → room_a | 0.5 | 0.5 | 0.71 m |
| room_a → room_b | 4.0 | 0.0 | 4.00 m |
| room_b → room_c | 0.0 | 4.0 | 4.00 m |
| room_c → dock | -4.5 | -4.5 | 6.36 m |
| **Total** | | | **15.07 m** |

---

### Running the Experiment

```bash
# Step 1: Launch with baseline params
./run.sh

# Step 2: Set initial pose in RViz

# Step 3: Run 10 trials
source install/setup.bash
python3 src/medguide_robot/scripts/run_experiment.py \
  --trials 10 \
  --output logs/baseline_results.csv

# Step 4: Modify nav2_params.yaml for Condition B, restart, repeat
# Save as: logs/inflation_085_results.csv

# Step 5: Condition C → logs/velocity_040_results.csv

# Step 6: Condition D → logs/planner_5hz_results.csv
```

---

## Experiment 2: SLAM Quality vs Robot Speed

### Hypothesis

> Mapping at lower speeds produces higher quality maps (fewer artifacts,
> better loop closure) compared to fast mapping.

### Conditions

| Condition | Teleop Speed | Duration |
|-----------|-------------|----------|
| Slow map | max_vel=0.10 | ~5 min |
| Normal map | max_vel=0.22 | ~3 min |
| Fast map | max_vel=0.40 | ~2 min |

### How to Evaluate

1. Map each condition using slam_toolbox
2. Save maps: `ros2 run nav2_map_server map_saver_cli -f maps/slow_map`
3. Compare visually: wall sharpness, alignment, artifacts
4. Run 5 navigation trials on each map → compare success rates

---

## Analysis Workflow

### Step 1: Load and Compute Statistics

```python
import pandas as pd

# Load results
baseline = pd.read_csv('logs/baseline_results.csv')
condB = pd.read_csv('logs/inflation_085_results.csv')

# Success rate
print(f"Baseline: {baseline.success.mean()*100:.1f}%")
print(f"Cond B:   {condB.success.mean()*100:.1f}%")

# Duration (successful goals only)
base_dur = baseline[baseline.success == True].duration_sec
print(f"Avg time: {base_dur.mean():.1f}s ± {base_dur.std():.1f}s")
```

### Step 2: Comparison Table

```python
conditions = {
    'Baseline':   'logs/baseline_results.csv',
    'Inflation':  'logs/inflation_085_results.csv',
    'Velocity':   'logs/velocity_040_results.csv',
    'Planner':    'logs/planner_5hz_results.csv',
}

results = []
for name, path in conditions.items():
    df = pd.read_csv(path)
    ok = df[df.success == True]
    results.append({
        'Condition': name,
        'Success %': f"{df.success.mean()*100:.1f}",
        'Avg Time (s)': f"{ok.duration_sec.mean():.1f}",
        'Avg Dist (m)': f"{ok.distance_m.mean():.2f}",
    })

summary = pd.DataFrame(results)
print(summary.to_markdown(index=False))
```

### Step 3: Visualization

```python
import matplotlib.pyplot as plt

fig, axes = plt.subplots(1, 3, figsize=(14, 4))

# Success rate bar chart
axes[0].bar(summary.Condition, summary['Success %'].astype(float))
axes[0].set_ylabel('Success Rate (%)')
axes[0].set_title('Goal Success Rate')

# Duration box plot
axes[1].bar(summary.Condition, summary['Avg Time (s)'].astype(float))
axes[1].set_ylabel('Time (seconds)')
axes[1].set_title('Average Goal Duration')

# Distance comparison
axes[2].bar(summary.Condition, summary['Avg Dist (m)'].astype(float))
axes[2].axhline(y=3.77, color='r', linestyle='--', label='Straight-line')
axes[2].set_ylabel('Distance (m)')
axes[2].set_title('Path Length')
axes[2].legend()

plt.tight_layout()
plt.savefig('docs/experiment_results.png', dpi=150)
plt.show()
```

---

## Report Template

### 1. Introduction
- MedGuide-ROS: autonomous hospital delivery robot
- Research question: How do navigation parameters affect delivery performance?

### 2. Hypothesis
- State what you expect each parameter change to do

### 3. Method
- Describe: simulation setup, robot model, world, Nav2 config
- List conditions (A/B/C/D) with exact parameter values
- State: N trials per condition, mission route, metrics collected

### 4. Results
- Table: success rate, avg time, avg distance per condition
- Chart: bar graphs comparing conditions
- Note any patterns or surprises

### 5. Discussion
- Which parameter had the biggest impact on success rate?
- Was there a speed-accuracy tradeoff?
- How does path efficiency compare to straight-line?
- Limitations: simulation vs real world, small sample size

### 6. Conclusion
- Best parameter configuration found
- Recommendations for real-world deployment
- Future work: dynamic obstacles, multi-robot, real hardware

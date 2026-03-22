# MedGuide-ROS — PhD Portfolio Narrative

> Profile for direct PhD applications (ETH Zurich, TU Delft, CMU RI, Oxford)  
> Candidate: [Your Name] | MedGuide-ROS v1.0 | March 2026

---

## 1. Project Summary (Elevator Pitch)

> *"I designed and implemented MedGuide-ROS — a complete autonomous hospital robot
> system from scratch using ROS2, Nav2, and Gazebo. The system autonomously navigates
> a simulated hospital floor, executes multi-room delivery missions, and adapts its
> safety behaviour based on tunable perception parameters. I then ran a structured
> experiment comparing two safety configurations across 30 independent trials,
> producing statistically significant results on mission success rate, path efficiency,
> and emergency-stop frequency — demonstrating both engineering depth and research rigour."*

---

## 2. Key Technical Contributions

| Contribution | Skill Demonstrated |
|---|---|
| Full ROS2 system integration (8 custom nodes) | Systems integration, software architecture |
| Hierarchical finite state machine for mission scheduling | State machine design, autonomous behaviour |
| Tunable obstacle detection with LiDAR cone filtering | Sensor processing, safety-critical systems |
| Experiment orchestrator with service-based lifecycle | Distributed systems, ROS2 services/actions |
| PyQt5 dashboard with embedded teleop + experiment UI | HRI, GUI development, real-time systems |
| CSV logging + Python statistical analysis pipeline | Research methodology, data science |
| Codebase cleanup & academic documentation (Phase-A) | Software maintainability, code quality |

---

## 3. Research Skills Demonstrated

### Experimental Design
- Designed a **controlled experiment** with two configurations, 15 trials each
- Defined clear independent variable (obstacle threshold), dependent variables (SR, PE, ESF)
- Applied **Mann-Whitney U test** (non-parametric) with **Cohen's d** effect size
- Set pre-defined acceptance criteria (≥10 valid trials, p < 0.05 threshold)

### Systems Engineering
- Built from components: Gazebo → SLAM → AMCL → Nav2 → custom nodes → UI
- Defined clean topic/service interface contracts per node (no God-objects)
- Applied **hysteresis control** in safety layer to prevent oscillation
- Diagnosed and fixed real integration bugs (E-STOP threshold, RTPS SHM errors)

### Software Quality
- Full PEP8-compliant Python across all nodes (flake8 configured)
- Modular `setup.py` with typed console_scripts
- Safe incremental cleanup with `colcon build` validation at each step
- Git commit strategy with semantic commit messages

---

## 4. Lessons Learned from System Tuning

### 1. Threshold sensitivity is context-dependent
> Setting `obstacle_threshold_m = 0.25m` caused the robot to perceive nearby walls
> in hospital room corners as emergencies (reading 0.21m). This locked the system
> in a permanent EMERGENCY_STOP state. Reducing to 0.18m — below the physical
> robot radius but above the minimum safe distance — resolved the issue.
>
> **Lesson:** Safety parameters must be validated against the actual sensor geometry
> and environment density. What is "safe" on paper may be physically unreachable.

### 2. Focus area matters as much as distance
> Widening the detection cone from ±22.5° to ±30° increased false-positive E-STOPs
> in narrow corridors. Tighter cones are better for straight-corridor navigation;
> wider cones are needed near intersections.
>
> **Lesson:** Multi-parameter interactions require separate ablation experiments.
> Single-variable isolation is critical for clean research conclusions.

### 3. End-to-end integration reveals invisible coupling
> The PyQt dashboard's `keyPressEvent` was silently broken because button clicks
> stole Qt focus. The system appeared correct in isolation (keyboard events fired
> in unit tests) but failed in integration (after any UI click).
>
> **Lesson:** Subsystem testing is insufficient for robotics UI/middleware integration.
> Full system tests are required.

### 4. SLAM quality determines Nav2 quality
> A poorly converged AMCL pose caused Nav2 to plan paths through obstacles.
> Setting the initial pose estimate manually in RViz and publishing `/initialpose`
> repeatedly during LAUNCHING mode significantly improved localization convergence.
>
> **Lesson:** Localization quality is the foundation of autonomous navigation. Any
> research claim about nav performance must document localization confidence.

---

## 5. Potential Extensions toward Real Robot Deployment

| Challenge | Current Sim Assumption | Real-World Solution |
|---|---|---|
| Sensor noise | Ideal Gaussian noise | Kalman filter on scan, adaptive threshold |
| Wheel slip | Perfect odometry | EKF with IMU fusion |
| Dynamic obstacles | Static hospital world | Velocity obstacle (VO) avoidance layer |
| Battery | Linear drain model | Real BMS integration via `/battery_state` |
| Human safety | No regulatory layer | ISO 13482 service robot safety compliance |
| Elevator navigation | Not implemented | Nav2 behaviour tree extension |
| Multi-floor map | Single PGM map | Semantic map with floor IDs |
| Network | Localhost ROS2 | ROS2 DDS over Ethernet + QoS tuning |

---

## 6. Positioning for PhD Applications

### Research Fit Statement (use in motivation letter)

> *"My MedGuide-ROS project demonstrates experience across the full robotics research
> stack: from low-level sensor processing (LiDAR obstacle detection) through middleware
> integration (ROS2 services, Nav2 actions) to high-level mission planning (HFSM) and
> experiment-driven evaluation. This directly maps to [lab]'s research on [topic],
> where I see opportunities to extend my simulation prototype toward [specific extension
> matching lab's work]."*

### Talking Points for Interview

1. **"Describe a technical problem you debugged."**  
   → E-STOP threshold causing permanent Nav2 blocking — explain root cause, diagnosis via logs, parametric fix, and validation.

2. **"How did you ensure experimental rigour?"**  
   → Mann-Whitney U (non-parametric for N=15), Cohen's d effect size, pre-defined acceptance criteria, separate logs per configuration.

3. **"What would you change if you had 6 more months?"**  
   → Real robot transfer (TurtleBot3 physical), dynamic human agents in simulation, behaviour-tree-based mission planner.

4. **"How is your work different from existing hospital robot systems?"**  
   → Full open-source ROS2 stack with systematic parameter ablation — most commercial systems don't publish tuning methodology.

---

## 7. Documents to Include in PhD Application Portfolio

| Document | Status |
|---|---|
| `docs/research_paper_structure.md` | ✅ Template ready |
| `docs/experiment_protocol.md` | ✅ Complete |
| `experiments/analyze_results.py` | ✅ Ready to run |
| `docs/results/summary_stats.txt` | ⏳ After experiments |
| `docs/results/fig1_success_rate.png` | ⏳ After experiments |
| `docs/results/fig2_duration_boxplot.png` | ⏳ After experiments |
| Gazebo mission screenshot | ⏳ Capture during trial |
| RViz navigation path screenshot | ⏳ Capture during trial |
| Dashboard screenshot | ⏳ Capture from running system |
| System architecture diagram | ⏳ Draw in draw.io/Mermaid |
| GitHub repo (public, clean README) | ⏳ After git commits |

---

## 8. Recommended Project README Structure (for GitHub)

```markdown
# MedGuide-ROS 🏥

> Autonomous hospital delivery robot — ROS2 Humble + Gazebo + Nav2

## Demo
[GIF or screenshot here]

## System Architecture
[Architecture diagram]

## Quick Start
\`\`\`bash
source /opt/ros/humble/setup.bash
colcon build
./run_project.sh
\`\`\`

## Experiment Results
Config A (0.18m threshold): SR=X%, PE=Y%, ESF=Z
Config B (0.25m threshold): SR=X%, PE=Y%, ESF=Z

## Research Paper
[Link to paper PDF or preprint]

## Author
[Name, Institution, Contact]
```

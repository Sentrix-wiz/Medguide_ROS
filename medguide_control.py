#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════╗
║   MedGuide-ROS — Hospital Delivery Robot             ║
║   Interactive Control Panel v1.0                     ║
╚══════════════════════════════════════════════════════╝

One-command control panel for the MedGuide autonomous robot.
Launches Gazebo + Nav2 + RViz, then provides an interactive
menu to drive, run missions, and run experiments.

Usage:
    python3 medguide_control.py
"""

import os
import sys
import subprocess
import signal
import time
import threading


# ── ANSI Colors ──────────────────────────────────────
class C:
    BLUE = '\033[38;5;75m'
    GREEN = '\033[38;5;114m'
    YELLOW = '\033[38;5;221m'
    RED = '\033[38;5;203m'
    CYAN = '\033[38;5;117m'
    MAGENTA = '\033[38;5;177m'
    DIM = '\033[2m'
    BOLD = '\033[1m'
    RESET = '\033[0m'
    BG_BLUE = '\033[48;5;24m'
    BG_GREEN = '\033[48;5;22m'


WS = os.path.dirname(os.path.abspath(__file__))
LAUNCH_PROC = None
TELEOP_PROC = None


def clear():
    os.system('clear')


def banner():
    clear()
    print(f"""
{C.CYAN}{C.BOLD}
    ╔══════════════════════════════════════════════════════╗
    ║                                                      ║
    ║   🏥  MedGuide-ROS                                   ║
    ║   Autonomous Hospital Delivery Robot                 ║
    ║                                                      ║
    ║   ROS2 Humble · TurtleBot3 · Nav2 · Gazebo           ║
    ║                                                      ║
    ╚══════════════════════════════════════════════════════╝
{C.RESET}""")


def status_line(label, value, color=C.GREEN):
    print(f"    {C.DIM}│{C.RESET}  {label:<20s} {color}{value}{C.RESET}")


def section(title):
    print(f"\n    {C.BLUE}{C.BOLD}{'─' * 50}{C.RESET}")
    print(f"    {C.BLUE}{C.BOLD}  {title}{C.RESET}")
    print(f"    {C.BLUE}{C.BOLD}{'─' * 50}{C.RESET}\n")


def menu_item(key, icon, label, desc=""):
    desc_str = f"  {C.DIM}— {desc}{C.RESET}" if desc else ""
    print(f"    {C.YELLOW}[{key}]{C.RESET}  {icon}  {label}{desc_str}")


def launch_stack():
    """Launch the full MedGuide stack."""
    global LAUNCH_PROC

    if LAUNCH_PROC and LAUNCH_PROC.poll() is None:
        print(f"\n    {C.GREEN}✅ Stack already running!{C.RESET}")
        time.sleep(1)
        return True

    clear()
    print(f"""
{C.CYAN}{C.BOLD}
    ╔══════════════════════════════════════════════════════╗
    ║  🚀  Launching MedGuide Robot Stack...              ║
    ╚══════════════════════════════════════════════════════╝
{C.RESET}""")

    steps = [
        ("Gazebo simulation world", 3),
        ("Nav2 navigation stack", 3),
        ("AMCL localization", 2),
        ("Obstacle detector", 1),
        ("Mission scheduler", 1),
        ("Sensor monitor", 1),
        ("Diagnostics", 1),
        ("RViz visualization", 1),
        ("Waiting for AMCL convergence", 5),
    ]

    env = os.environ.copy()
    env['TURTLEBOT3_MODEL'] = 'burger'

    cmd = (
        f'source /opt/ros/humble/setup.bash && '
        f'source {WS}/install/setup.bash && '
        f'export TURTLEBOT3_MODEL=burger && '
        f'ros2 launch medguide_robot medguide_full.launch.py'
    )
    LAUNCH_PROC = subprocess.Popen(
        cmd, shell=True, executable='/bin/bash',
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        preexec_fn=os.setsid,
    )

    for label, dur in steps:
        print(f"    {C.CYAN}⏳{C.RESET}  {label}...", end='', flush=True)
        time.sleep(dur)
        if LAUNCH_PROC.poll() is not None:
            print(f"  {C.RED}✗ FAILED{C.RESET}")
            return False
        print(f"\r    {C.GREEN}✅{C.RESET}  {label}{'':>30s}")

    print(f"\n    {C.GREEN}{C.BOLD}╔════════════════════════════════════════╗{C.RESET}")
    print(f"    {C.GREEN}{C.BOLD}║  ✅  All Systems Online!               ║{C.RESET}")
    print(f"    {C.GREEN}{C.BOLD}╚════════════════════════════════════════╝{C.RESET}")
    print(f"\n    {C.DIM}Gazebo and RViz windows should be visible.{C.RESET}")
    time.sleep(2)
    return True


def start_teleop():
    """Launch keyboard teleop in this terminal."""
    global TELEOP_PROC
    clear()
    print(f"""
{C.YELLOW}{C.BOLD}
    ╔══════════════════════════════════════════════════════╗
    ║  🎮  Manual Robot Control                            ║
    ╠══════════════════════════════════════════════════════╣
    ║                                                      ║
    ║   W / ↑   =  Drive Forward                           ║
    ║   S / ↓   =  Drive Backward                          ║
    ║   A / ←   =  Turn Left                               ║
    ║   D / →   =  Turn Right                              ║
    ║   X       =  Emergency Stop                          ║
    ║                                                      ║
    ║   Press Ctrl+C to return to menu                     ║
    ║                                                      ║
    ╚══════════════════════════════════════════════════════╝
{C.RESET}""")

    cmd = (
        f'source /opt/ros/humble/setup.bash && '
        f'source {WS}/install/setup.bash && '
        f'export TURTLEBOT3_MODEL=burger && '
        f'ros2 run turtlebot3_teleop teleop_keyboard'
    )
    try:
        subprocess.run(cmd, shell=True, executable='/bin/bash')
    except KeyboardInterrupt:
        pass


def start_mission():
    """Trigger an autonomous delivery mission."""
    clear()
    print(f"""
{C.MAGENTA}{C.BOLD}
    ╔══════════════════════════════════════════════════════╗
    ║  🤖  Autonomous Delivery Mission                     ║
    ╠══════════════════════════════════════════════════════╣
    ║                                                      ║
    ║   Route: Room A → Room B → Room C → Dock             ║
    ║                                                      ║
    ║   Watch the robot navigate autonomously!             ║
    ║   The robot uses Nav2 path planning + AMCL           ║
    ║   localization to reach each room.                   ║
    ║                                                      ║
    ╚══════════════════════════════════════════════════════╝
{C.RESET}""")

    print(f"    {C.CYAN}⏳{C.RESET}  Sending mission command...", end='', flush=True)

    cmd = (
        f'source /opt/ros/humble/setup.bash && '
        f'source {WS}/install/setup.bash && '
        f"timeout 30 ros2 service call /start_mission std_srvs/srv/Trigger '{{}}'"
    )
    result = subprocess.run(
        cmd, shell=True, executable='/bin/bash',
        capture_output=True, text=True,
    )

    if 'success=True' in result.stdout:
        print(f"\r    {C.GREEN}✅{C.RESET}  Mission started!{'':>30s}")
        # Extract mission info
        for line in result.stdout.split('\n'):
            if 'message' in line:
                print(f"    {C.DIM}│{C.RESET}  {line.strip()}")
        print(f"\n    {C.GREEN}Watch the robot navigate in Gazebo and RViz!{C.RESET}")
        print(f"    {C.DIM}The robot visits all rooms then returns to dock.{C.RESET}")
    else:
        print(f"\r    {C.RED}✗{C.RESET}  Could not start mission{'':>30s}")
        print(f"    {C.DIM}Make sure the stack is running first (option 1).{C.RESET}")

    print(f"\n    {C.DIM}Press Enter to return to menu...{C.RESET}", end='')
    input()


def run_experiment():
    """Run automated experiment trials."""
    clear()
    print(f"""
{C.BLUE}{C.BOLD}
    ╔══════════════════════════════════════════════════════╗
    ║  📊  Navigation Performance Experiment               ║
    ╠══════════════════════════════════════════════════════╣
    ║                                                      ║
    ║   Runs multiple mission trials automatically         ║
    ║   Logs: success rate, duration, distance to CSV      ║
    ║                                                      ║
    ╚══════════════════════════════════════════════════════╝
{C.RESET}""")

    try:
        trials = input(f"    How many trials? [{C.YELLOW}3{C.RESET}]: ").strip()
        trials = int(trials) if trials else 3
    except (ValueError, EOFError):
        trials = 3

    ts = time.strftime('%Y%m%d_%H%M%S')
    output = f"{WS}/logs/experiment_{ts}.csv"
    os.makedirs(f"{WS}/logs", exist_ok=True)

    print(f"\n    {C.CYAN}⏳{C.RESET}  Running {trials} trials...")
    print(f"    {C.DIM}│{C.RESET}  Output: {output}")
    print(f"    {C.DIM}│{C.RESET}  This will take a few minutes.\n")

    cmd = (
        f'source /opt/ros/humble/setup.bash && '
        f'source {WS}/install/setup.bash && '
        f'python3 {WS}/src/medguide_robot/scripts/run_experiment.py '
        f'--trials {trials} --output {output}'
    )
    try:
        subprocess.run(cmd, shell=True, executable='/bin/bash')
    except KeyboardInterrupt:
        pass

    print(f"\n    {C.DIM}Press Enter to return to menu...{C.RESET}", end='')
    input()


def show_architecture():
    """Display the system architecture."""
    clear()
    print(f"""
{C.CYAN}{C.BOLD}
    ╔══════════════════════════════════════════════════════╗
    ║  📐  MedGuide-ROS System Architecture                ║
    ╚══════════════════════════════════════════════════════╝
{C.RESET}
    {C.BOLD}Layer 1 — Simulation{C.RESET}
    {C.DIM}│{C.RESET}  Gazebo (hospital world) → /scan, /odom, /cmd_vel

    {C.BOLD}Layer 2 — Perception{C.RESET}
    {C.DIM}│{C.RESET}  sensor_monitor     → LIDAR + odometry monitoring
    {C.DIM}│{C.RESET}  obstacle_detector   → emergency stop @ 0.25m

    {C.BOLD}Layer 3 — Navigation (Nav2){C.RESET}
    {C.DIM}│{C.RESET}  AMCL               → localization on map
    {C.DIM}│{C.RESET}  planner_server     → global path planning (NavFn)
    {C.DIM}│{C.RESET}  controller_server  → local trajectory (DWB)
    {C.DIM}│{C.RESET}  costmap (2D)       → static + obstacle + inflation

    {C.BOLD}Layer 4 — Task Management{C.RESET}
    {C.DIM}│{C.RESET}  mission_scheduler   → room-to-room delivery
    {C.DIM}│{C.RESET}  mission_logger      → CSV data logging
    {C.DIM}│{C.RESET}  diagnostics_node    → system health monitor

    {C.BOLD}Layer 5 — Research{C.RESET}
    {C.DIM}│{C.RESET}  run_experiment.py   → N-trial automation
    {C.DIM}│{C.RESET}  analyze_results.py  → stats + matplotlib charts

    {C.BOLD}Custom Messages{C.RESET}
    {C.DIM}│{C.RESET}  MissionStatus.msg   → mission_id, state, goals, distance
    {C.DIM}│{C.RESET}  GoalResult.msg      → per-goal success, duration, distance
""")
    print(f"    {C.DIM}Press Enter to return to menu...{C.RESET}", end='')
    input()


def show_status():
    """Show current system status."""
    global LAUNCH_PROC
    clear()
    section("System Status")

    stack_ok = LAUNCH_PROC and LAUNCH_PROC.poll() is None
    status_line("Robot Stack", "● RUNNING" if stack_ok else "○ STOPPED",
                C.GREEN if stack_ok else C.RED)

    if stack_ok:
        # Check ROS2 topics
        cmd = (
            f'source /opt/ros/humble/setup.bash && '
            f'source {WS}/install/setup.bash && '
            f'timeout 3 ros2 topic echo /system_health --once 2>/dev/null'
        )
        result = subprocess.run(
            cmd, shell=True, executable='/bin/bash',
            capture_output=True, text=True,
        )
        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                line = line.strip()
                if line and not line.startswith('---'):
                    status_line("", line, C.CYAN)

    print(f"\n    {C.DIM}Press Enter to return to menu...{C.RESET}", end='')
    input()


def cleanup(signum=None, frame=None):
    """Kill all child processes."""
    global LAUNCH_PROC
    print(f"\n\n    {C.YELLOW}Shutting down MedGuide...{C.RESET}")
    if LAUNCH_PROC and LAUNCH_PROC.poll() is None:
        os.killpg(os.getpgid(LAUNCH_PROC.pid), signal.SIGTERM)
        LAUNCH_PROC.wait(timeout=10)
    subprocess.run('killall -9 gzserver gzclient 2>/dev/null',
                    shell=True, stderr=subprocess.DEVNULL)
    print(f"    {C.GREEN}✅ All processes stopped.{C.RESET}\n")
    sys.exit(0)


def main():
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    while True:
        banner()

        stack_ok = LAUNCH_PROC and LAUNCH_PROC.poll() is None
        if stack_ok:
            print(f"    {C.GREEN}{C.BOLD}● Stack: RUNNING{C.RESET}")
        else:
            print(f"    {C.RED}○ Stack: NOT RUNNING{C.RESET}")

        section("Control Panel")
        menu_item("1", "🚀", "Launch Robot Stack",
                  "Gazebo + Nav2 + RViz + all nodes")
        menu_item("2", "🎮", "Manual Drive (WASD)",
                  "keyboard control the robot")
        menu_item("3", "🤖", "Start Autonomous Mission",
                  "robot visits all rooms")
        menu_item("4", "📊", "Run Experiment",
                  "N trials with CSV logging")
        menu_item("5", "📐", "View Architecture",
                  "system design overview")
        menu_item("6", "📈", "System Status",
                  "check node health")
        menu_item("Q", "🚪", "Quit",
                  "stop everything and exit")

        print()
        choice = input(f"    {C.YELLOW}▶ Choose [{C.BOLD}1-6, Q{C.RESET}{C.YELLOW}]: {C.RESET}").strip().lower()

        if choice == '1':
            launch_stack()
        elif choice == '2':
            if not stack_ok:
                print(f"\n    {C.RED}⚠ Launch the stack first (option 1)!{C.RESET}")
                time.sleep(2)
            else:
                start_teleop()
        elif choice == '3':
            if not stack_ok:
                print(f"\n    {C.RED}⚠ Launch the stack first (option 1)!{C.RESET}")
                time.sleep(2)
            else:
                start_mission()
        elif choice == '4':
            if not stack_ok:
                print(f"\n    {C.RED}⚠ Launch the stack first (option 1)!{C.RESET}")
                time.sleep(2)
            else:
                run_experiment()
        elif choice == '5':
            show_architecture()
        elif choice == '6':
            show_status()
        elif choice == 'q':
            cleanup()
        else:
            print(f"\n    {C.RED}Invalid choice. Try 1-6 or Q.{C.RESET}")
            time.sleep(1)


if __name__ == '__main__':
    main()

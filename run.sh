#!/bin/bash
#═══════════════════════════════════════════════════════
#  MedGuide-ROS — One-Command Launch
#═══════════════════════════════════════════════════════
set -e

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

clear
echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════╗"
echo "║     🏥 MedGuide-ROS — Hospital Delivery Robot   ║"
echo "║     Autonomous Navigation System  v0.7          ║"
echo "╚══════════════════════════════════════════════════╝"
echo -e "${NC}"

# Source ROS2 + workspace
source /opt/ros/humble/setup.bash
source "$(dirname "$0")/install/setup.bash"
export TURTLEBOT3_MODEL=burger

echo -e "${CYAN}[1/2]${NC} Launching full robot stack..."
echo -e "      Gazebo + Nav2 + Safety + Missions + RViz"
echo ""

# Launch in background
ros2 launch medguide_robot medguide_full.launch.py &
LAUNCH_PID=$!
sleep 15  # Wait for all nodes to initialize

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════╗"
echo -e "║  ✅  All Systems Online                          ║"
echo -e "╠══════════════════════════════════════════════════╣"
echo -e "║                                                  ║"
echo -e "║  ${YELLOW}How to Control:${GREEN}                                 ║"
echo -e "║                                                  ║"
echo -e "║  📍 Manual Drive (open new terminal):            ║"
echo -e "║     ${CYAN}cd ~/medguide_ws && source run_teleop.sh${GREEN}      ║"
echo -e "║     Use WASD keys to drive the robot             ║"
echo -e "║                                                  ║"
echo -e "║  🤖 Autonomous Mission (open new terminal):      ║"
echo -e "║     ${CYAN}cd ~/medguide_ws && source run_mission.sh${GREEN}     ║"
echo -e "║     Robot navigates to all rooms automatically   ║"
echo -e "║                                                  ║"
echo -e "║  📊 Run Experiment (open new terminal):          ║"
echo -e "║     ${CYAN}cd ~/medguide_ws && source run_experiment.sh${GREEN}  ║"
echo -e "║     Runs 3 trials and saves CSV data             ║"
echo -e "║                                                  ║"
echo -e "║  🖥️  Windows:                                     ║"
echo -e "║     • Gazebo  = 3D simulation world              ║"
echo -e "║     • RViz2   = Robot map + sensor view          ║"
echo -e "║                                                  ║"
echo -e "╚══════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "Press ${YELLOW}Ctrl+C${NC} to stop everything."
echo ""

# Wait for launch to finish
wait $LAUNCH_PID

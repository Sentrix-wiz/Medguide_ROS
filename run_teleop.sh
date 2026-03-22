#!/bin/bash
# 🎮 Manual Robot Control — WASD Keys
source /opt/ros/humble/setup.bash
source "$(dirname "$0")/install/setup.bash"
export TURTLEBOT3_MODEL=burger

echo ""
echo "🎮  Manual Robot Control"
echo "════════════════════════"
echo "  W = Forward    S = Backward"
echo "  A = Turn Left  D = Turn Right"
echo "  X = Stop       Q = Quit"
echo ""
echo "Press keys to drive the robot in Gazebo!"
echo ""

ros2 run turtlebot3_teleop teleop_keyboard

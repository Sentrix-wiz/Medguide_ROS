#!/bin/bash
# ═══════════════════════════════════════════════════════════
#  MedGuide-ROS — Quick Setup
#  Run this ONCE after cloning the repository
# ═══════════════════════════════════════════════════════════
set -e

echo "╔══════════════════════════════════════════╗"
echo "║   MedGuide-ROS — Building Project        ║"
echo "╚══════════════════════════════════════════╝"

cd "$(dirname "$0")"

# Source ROS2
source /opt/ros/humble/setup.bash

# Build both packages
echo ""
echo "▶ Building medguide_msgs (custom messages)..."
colcon build --packages-select medguide_msgs --symlink-install
echo "✅ medguide_msgs built"

echo ""
echo "▶ Building medguide_robot (main package)..."
source install/setup.bash
colcon build --packages-select medguide_robot --symlink-install
echo "✅ medguide_robot built"

# Run tests
echo ""
echo "▶ Running unit tests..."
source install/setup.bash
python3 -m pytest src/medguide_robot/test/ -v --tb=short 2>&1 | tail -10

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   ✅ Setup Complete!                     ║"
echo "║   Run: ./run.sh                          ║"
echo "╚══════════════════════════════════════════╝"

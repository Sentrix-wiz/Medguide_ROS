#!/bin/bash
# ═══════════════════════════════════════════════════════════
#  MedGuide-ROS — Run Unit Tests
# ═══════════════════════════════════════════════════════════
cd "$(dirname "$0")"
source /opt/ros/humble/setup.bash
source install/setup.bash

echo "Running MedGuide-ROS unit tests..."
echo ""
python3 -m pytest src/medguide_robot/test/ -v --tb=short

#!/bin/bash
# 🤖 Start Autonomous Delivery Mission
source /opt/ros/humble/setup.bash
source "$(dirname "$0")/install/setup.bash"

echo ""
echo "🤖  Starting Autonomous Mission"
echo "════════════════════════════════"
echo "  Robot will visit: Room A → Room B → Room C → Dock"
echo "  Watch in Gazebo and RViz!"
echo ""

ros2 service call /start_mission std_srvs/srv/Trigger '{}'

echo ""
echo "✅ Mission started! Watch the robot navigate in Gazebo."
echo "   Monitor: ros2 topic echo /mission_status"
echo ""

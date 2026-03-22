#!/bin/bash
# MedGuide-ROS — Single Command Launcher
# This script starts both the Experiment Orchestrator and the Dashboard UI.

# Source ROS2 and Workspace
source /opt/ros/humble/setup.bash
source ~/medguide_ws/install/setup.bash

echo "======================================================"
echo "    🚀 Starting MedGuide-ROS Autonomous System 🚀    "
echo "======================================================"

# Clean up any stale Gazebo/ROS processes safely
killall -9 gzserver gzclient 2>/dev/null
killall -9 rviz2 2>/dev/null

# Start Orchestrator in the background
echo "[INFO] Starting Experiment Orchestrator..."
python3 ~/medguide_ws/src/medguide_robot/scripts/orchestrator.py &
ORCH_PID=$!

sleep 2

# Start Dashboard UI in the foreground
echo "[INFO] Starting Dashboard UI..."
python3 ~/medguide_ws/src/medguide_robot/scripts/dashboard.py

# When dashboard is closed, kill orchestrator
echo "[INFO] Dashboard closed. Shutting down Orchestrator..."
kill -9 $ORCH_PID 2>/dev/null

echo "======================================================"
echo "                   System Offline                     "
echo "======================================================"

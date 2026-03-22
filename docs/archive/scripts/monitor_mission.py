#!/usr/bin/env python3
"""
Mission Status Monitor Script for MedGuide.

Subscribes to mission status topic and displays real-time progress of mission execution.
Useful for debugging and monitoring during development.

Usage:
    python3 monitor_mission.py
    
Displays:
  - Current mission status
  - Progress indicator
  - Mission metrics (if available)
  - Emergency stop state
"""

import sys
from datetime import datetime

import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Bool, Float32


class MissionMonitor(Node):
    """Monitor and display mission execution status in real-time."""

    def __init__(self):
        super().__init__('mission_monitor')
        
        # Subscriptions
        self.mission_status_sub = self.create_subscription(
            String,
            '/mission_status',
            self._mission_status_callback,
            10
        )
        
        self.emergency_stop_sub = self.create_subscription(
            Bool,
            '/emergency_stop',
            self._emergency_stop_callback,
            10
        )
        
        self.obstacle_distance_sub = self.create_subscription(
            Float32,
            '/obstacle_distance',
            self._obstacle_distance_callback,
            10
        )
        
        self.goal_status_sub = self.create_subscription(
            String,
            '/goal_status',
            self._goal_status_callback,
            10
        )
        
        # State
        self.mission_status = "IDLE"
        self.emergency_stop_active = False
        self.obstacle_distance = 999.0
        self.goal_status = "NONE"
        self.last_update = datetime.now()
        
        self.get_logger().info("Mission Monitor initialized")
        self._print_header()
        
        # Timer for periodic display update
        self.timer = self.create_timer(1.0, self._display_update)

    def _mission_status_callback(self, msg: String):
        """Handle mission status updates."""
        self.mission_status = msg.data
        self.last_update = datetime.now()
        
        # Check for mission state changes
        if "mission_complete" in msg.data.lower():
            self.get_logger().info("✓ MISSION COMPLETED!")
        elif "emergency_stop" in msg.data.lower() and "triggered" in msg.data.lower():
            self.get_logger().warn("⚠️  EMERGENCY STOP TRIGGERED!")
        elif "failed" in msg.data.lower():
            self.get_logger().error(f"✗ MISSION FAILED: {msg.data}")

    def _emergency_stop_callback(self, msg: Bool):
        """Handle emergency stop state."""
        if msg.data != self.emergency_stop_active:
            self.emergency_stop_active = msg.data
            if msg.data:
                self.get_logger().warn("🛑 Emergency stop ACTIVE")
            else:
                self.get_logger().info("🟢 Emergency stop CLEARED")

    def _obstacle_distance_callback(self, msg: Float32):
        """Handle obstacle distance updates."""
        self.obstacle_distance = msg.data

    def _goal_status_callback(self, msg: String):
        """Handle goal status updates."""
        self.goal_status = msg.data

    def _display_update(self):
        """Periodic display update."""
        self._print_status()

    def _print_header(self):
        """Print header banner."""
        print("\n" + "="*70)
        print("MedGuide Mission Status Monitor")
        print("="*70 + "\n")

    def _print_status(self):
        """Print current mission status."""
        # Safe indicator
        safety_icon = "🛑" if self.emergency_stop_active else "✓"
        
        # Distance indicator
        if self.obstacle_distance < 0.5:
            distance_color = "🔴"  # RED - danger
        elif self.obstacle_distance < 1.0:
            distance_color = "🟡"  # YELLOW - caution
        else:
            distance_color = "🟢"  # GREEN - safe
        
        # Clear screen and print status
        print(f"\r[{self.last_update.strftime('%H:%M:%S')}] ", end='')
        print(f"{safety_icon} Status: {self.mission_status[:60]:<60} ", end='')
        print(f"| {distance_color} Dist: {self.obstacle_distance:.2f}m", end='', flush=True)


def main():
    """Main entry point."""
    rclpy.init()
    monitor = MissionMonitor()
    
    try:
        rclpy.spin(monitor)
    except KeyboardInterrupt:
        print("\n\nMonitor stopped by user")
    finally:
        monitor.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

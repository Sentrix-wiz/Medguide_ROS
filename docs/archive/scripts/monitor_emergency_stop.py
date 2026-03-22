#!/usr/bin/env python3
"""
Emergency Stop Monitor for MedGuide.

Subscribes to obstacle detection and emergency stop topics,
displaying real-time obstacle distances and emergency state.

Useful for testing perception layer and obstacle avoidance behavior.

Usage:
    python3 monitor_emergency_stop.py
    
Displays:
  - Closest obstacle distance
  - Emergency stop state
  - Danger zones (color-coded)
"""

import sys
from collections import deque
from datetime import datetime

import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, Float32


class EmergencyStopMonitor(Node):
    """Monitor obstacle detection and emergency stop state."""

    def __init__(self):
        super().__init__('emergency_stop_monitor')
        
        # Parameters
        self.declare_parameter('obstacle_threshold_m', 0.3)
        self.declare_parameter('warning_threshold_m', 0.8)
        
        # Subscriptions
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
        
        # State
        self.emergency_stop_active = False
        self.obstacle_distance = 999.0
        self.distance_history = deque(maxlen=60)  # Last 60 samples
        self.emergency_stop_count = 0
        
        self.threshold = self.get_parameter('obstacle_threshold_m').value
        self.warning = self.get_parameter('warning_threshold_m').value
        
        # Timer for periodic display
        self.timer = self.create_timer(0.5, self._display_update)
        
        self.get_logger().info(
            f"Emergency Stop Monitor initialized\n"
            f"  Danger threshold: {self.threshold}m\n"
            f"  Warning threshold: {self.warning}m"
        )
        self._print_header()

    def _emergency_stop_callback(self, msg: Bool):
        """Handle emergency stop state change."""
        if msg.data and not self.emergency_stop_active:
            self.emergency_stop_active = True
            self.emergency_stop_count += 1
            self.get_logger().error(
                f"🛑 EMERGENCY STOP #{self.emergency_stop_count} - "
                f"Obstacle at {self.obstacle_distance:.3f}m"
            )
        elif not msg.data and self.emergency_stop_active:
            self.emergency_stop_active = False
            self.get_logger().info(f"✓ Emergency stop cleared - safe to proceed")

    def _obstacle_distance_callback(self, msg: Float32):
        """Handle obstacle distance updates."""
        self.obstacle_distance = msg.data
        self.distance_history.append(msg.data)

    def _display_update(self):
        """Periodic display refresh."""
        self._print_status_bar()

    def _print_header(self):
        """Print header information."""
        print("="*70)
        print("MedGuide Emergency Stop & Obstacle Monitor")
        print("="*70)
        print(f"\n🔴 DANGER: < {self.threshold}m  |  🟡 WARN: < {self.warning}m  |  "
              f"🟢 SAFE: >= {self.warning}m\n")

    def _get_status_icon(self, distance: float) -> str:
        """Get status icon based on distance."""
        if distance < self.threshold:
            return "🔴"  # DANGER - emergency stop active
        elif distance < self.warning:
            return "🟡"  # WARNING - approaching danger zone
        else:
            return "🟢"  # SAFE

    def _get_bar_visualization(self, distance: float, max_dist: float = 3.0) -> str:
        """Create a simple bar visualization of distance."""
        bar_length = 20
        
        if distance >= max_dist:
            filled = bar_length
        else:
            filled = int((distance / max_dist) * bar_length)
        
        # Color-coded fill
        danger_zone = int((self.threshold / max_dist) * bar_length)
        warn_zone = int((self.warning / max_dist) * bar_length)
        
        bar = ""
        for i in range(bar_length):
            if i < danger_zone:
                bar += "█"  # Always red danger zone
            elif i < warn_zone:
                bar += "▓"  # Warning zone
            elif i < filled:
                bar += "░"  # Filled area
            else:
                bar += "·"  # Empty area
        
        return f"[{bar}]"

    def _print_status_bar(self):
        """Print status bar with distance visualization."""
        status_icon = self._get_status_icon(self.obstacle_distance)
        bar = self._get_bar_visualization(self.obstacle_distance)
        
        emergency_str = "🛑 EMERGENCY STOP" if self.emergency_stop_active else "​Ready"
        
        print(
            f"\r{status_icon} Distance: {self.obstacle_distance:6.3f}m  "
            f"{bar}  | {emergency_str:<20}  | "
            f"E-stops: {self.emergency_stop_count:<3}",
            end='',
            flush=True
        )


def main():
    """Main entry point."""
    rclpy.init()
    monitor = EmergencyStopMonitor()
    
    try:
        rclpy.spin(monitor)
    except KeyboardInterrupt:
        print("\n\nMonitor stopped by user")
    finally:
        print()  # newline after last status bar
        monitor.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

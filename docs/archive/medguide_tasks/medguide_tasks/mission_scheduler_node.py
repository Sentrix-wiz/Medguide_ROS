#!/usr/bin/env python3
"""
Mission Scheduler Node for MedGuide.

Orchestrates mission execution by managing a queue of delivery goals,
sending them to the navigation goal sender, and tracking metrics.

Core responsibilities:
  - Maintain mission queue
  - Send goals sequentially via navigation action client
  - Track mission success/failure metrics
  - Publish mission status and progress
  - Handle emergency stops gracefully

Subscribes to:
  - /emergency_stop (std_msgs/Bool) - emergency stop signal from perception
  - /goal_status (std_msgs/String) - navigation goal completion status

Publishes to:
  - /mission_status (std_msgs/String) - current mission status
  - /mission_metrics (diagnostic_msgs/KeyValue) - aggregated metrics

Services:
  - /start_mission - Start a new mission sequence
  - /abort_mission - Abort current mission
"""

import time
import math
from typing import List
from enum import Enum

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped, Quaternion
from std_msgs.msg import String, Bool
from diagnostic_msgs.msg import KeyValue

from medguide_utils.mission_config import (
    HOSPITAL_ROOMS,
    DEFAULT_MISSION_SEQUENCE,
    MISSION_LOOP_RATE_HZ,
    INITIAL_BATTERY_LEVEL,
    BATTERY_DRAIN_RATE
)
from medguide_utils.types import MissionStatus, GoalStatus, MissionMetrics
from medguide_utils.qos_profiles import STATUS_QOS, COMMAND_QOS
from medguide_utils.logging_utils import (
    log_mission_start,
    log_mission_complete,
    log_battery_status
)


class MissionScheduler(Node):
    """Manages mission execution and tracks metrics."""

    def __init__(self):
        super().__init__('mission_scheduler')
        
        # Parameters
        self.declare_parameter('use_sim_time', True)
        self.declare_parameter('mission_sequence', DEFAULT_MISSION_SEQUENCE)
        self.declare_parameter('battery_drain_enabled', True)
        
        # Subscriptions
        self.emergency_stop_sub = self.create_subscription(
            Bool,
            '/emergency_stop',
            self._emergency_stop_callback,
            STATUS_QOS
        )
        
        self.goal_status_sub = self.create_subscription(
            String,
            '/goal_status',
            self._goal_status_callback,
            STATUS_QOS
        )
        
        # Publishers
        self.mission_status_pub = self.create_publisher(
            String,
            '/mission_status',
            STATUS_QOS
        )
        
        self.metrics_pub = self.create_publisher(
            KeyValue,
            '/mission_metrics',
            STATUS_QOS
        )
        
        # Main control loop timer
        self.mission_timer = self.create_timer(
            1.0 / MISSION_LOOP_RATE_HZ,
            self._mission_loop
        )
        
        # State variables
        self.mission_status = MissionStatus.IDLE
        self.current_goal_idx = 0
        self.mission_queue: List[str] = []
        self.emergency_stop_active = False
        self.last_goal_status = ""
        
        # Metrics tracking
        self.mission_start_time = None
        self.goal_succeeded = 0
        self.goal_failed = 0
        self.emergency_stop_count = 0
        self.battery_level = INITIAL_BATTERY_LEVEL
        self.battery_start = INITIAL_BATTERY_LEVEL
        
        self.get_logger().info("MissionScheduler initialized")

    def start_mission(self, goal_sequence: List[str] = None):
        """
        Start a new mission with the given goal sequence.
        
        Args:
            goal_sequence: List of goal names from HOSPITAL_ROOMS.
                          If None, uses default sequence.
        """
        if goal_sequence is None:
            goal_sequence = self.get_parameter('mission_sequence').value
        
        # Validate goals exist
        for goal_name in goal_sequence:
            if goal_name not in HOSPITAL_ROOMS:
                self.get_logger().error(f"Unknown goal: {goal_name}")
                return False
        
        # Reset metrics
        self.mission_status = MissionStatus.EXECUTING
        self.current_goal_idx = 0
        self.mission_queue = goal_sequence
        self.mission_start_time = time.time()
        self.goal_succeeded = 0
        self.goal_failed = 0
        self.emergency_stop_count = 0
        self.battery_start = self.battery_level
        
        log_mission_start(
            self.get_logger(),
            mission_id=f"seq_{int(time.time())}",
            goals=goal_sequence
        )
        
        self._publish_mission_status(
            f"MISSION_START: {len(goal_sequence)} goals"
        )
        
        return True

    def abort_mission(self):
        """Abort the current mission."""
        if self.mission_status == MissionStatus.EXECUTING:
            self.mission_status = MissionStatus.FAILED
            self._publish_mission_status("MISSION_ABORTED")
            self.get_logger().warn("Mission aborted by user")

    def _mission_loop(self):
        """Main mission execution loop."""
        if self.mission_status != MissionStatus.EXECUTING:
            return
        
        # Update battery simulation
        if self.get_parameter('battery_drain_enabled').value:
            elapsed_min = (time.time() - self.mission_start_time) / 60.0
            self.battery_level = max(
                0.0,
                self.battery_start - (elapsed_min * BATTERY_DRAIN_RATE)
            )
            
            # Log battery at intervals
            if int(self.battery_level) % 10 == 0:
                log_battery_status(self.get_logger(), self.battery_level)
        
        # Check if all goals are complete
        if self.current_goal_idx >= len(self.mission_queue):
            self._complete_mission()
            return
        
        # If emergency stop is active, remain idle
        if self.emergency_stop_active:
            self._publish_mission_status("EMERGENCY_STOP_ACTIVE: Waiting for clearance")
            return
        
        # Get current goal and send it
        goal_name = self.mission_queue[self.current_goal_idx]
        goal_config = HOSPITAL_ROOMS[goal_name]
        
        # Create navigation goal
        pose = PoseStamped()
        pose.header.frame_id = "map"
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.pose.position.x = goal_config.x
        pose.pose.position.y = goal_config.y
        pose.pose.position.z = 0.0
        
        # Simple quaternion for orientation (facing direction)
        q = self._euler_to_quaternion(0, 0, goal_config.theta)
        pose.pose.orientation = q
        
        # TODO: Call navigation_goal_sender via action (or service)
        # For now, simulate success after timeout
        self._simulate_goal_execution(goal_name)

    def _simulate_goal_execution(self, goal_name: str):
        """
        Simulate goal execution (for testing without full Nav2).
        In production, this would call the navigation_goal_sender action.
        """
        # TODO: Replace with actual action call to navigation_goal_sender
        # For simulation, randomly succeed (80% success rate)
        import random
        
        success = random.random() > 0.2  # 80% success
        
        if success:
            self.goal_succeeded += 1
            self._publish_mission_status(
                f"GOAL_SUCCEEDED: {goal_name} ({self.goal_succeeded} total)"
            )
            self.get_logger().info(f"Goal {goal_name} succeeded (simulated)")
        else:
            self.goal_failed += 1
            self._publish_mission_status(
                f"GOAL_FAILED: {goal_name} ({self.goal_failed} total)"
            )
            self.get_logger().warn(f"Goal {goal_name} failed (simulated)")
        
        # Move to next goal
        self.current_goal_idx += 1

    def _complete_mission(self):
        """Mark mission as complete and log metrics."""
        elapsed_time = time.time() - self.mission_start_time
        
        metrics = MissionMetrics(
            total_goals=len(self.mission_queue),
            succeeded_goals=self.goal_succeeded,
            failed_goals=self.goal_failed,
            total_time_seconds=elapsed_time,
            emergency_stops=self.emergency_stop_count,
            battery_used_percent=self.battery_start - self.battery_level
        )
        
        log_mission_complete(
            self.get_logger(),
            total_time=elapsed_time,
            success_count=metrics.succeeded_goals,
            failure_count=metrics.failed_goals
        )
        
        self.mission_status = MissionStatus.COMPLETED
        self._publish_mission_status(f"MISSION_COMPLETE: {metrics}")

    def _emergency_stop_callback(self, msg: Bool):
        """Handle emergency stop signal from perception layer."""
        if msg.data and not self.emergency_stop_active:
            self.emergency_stop_active = True
            self.emergency_stop_count += 1
            self.mission_status = MissionStatus.EMERGENCY_STOP
            self._publish_mission_status("EMERGENCY_STOP_TRIGGERED")
            self.get_logger().error("Emergency stop activated!")
        
        elif not msg.data and self.emergency_stop_active:
            self.emergency_stop_active = False
            if self.mission_queue:  # Resume if mission was in progress
                self.mission_status = MissionStatus.EXECUTING
                self._publish_mission_status("EMERGENCY_STOP_CLEARED: Resuming mission")
                self.get_logger().info("Emergency stop cleared, resuming mission")

    def _goal_status_callback(self, msg: String):
        """Handle goal status updates from navigation layer."""
        self.last_goal_status = msg.data
        self.get_logger().debug(f"Goal status: {msg.data}")

    def _publish_mission_status(self, status_text: str):
        """Publish mission status to topic."""
        msg = String()
        msg.data = f"[{self.mission_status.value}] {status_text}"
        self.mission_status_pub.publish(msg)

    @staticmethod
    def _euler_to_quaternion(roll: float, pitch: float, yaw: float) -> Quaternion:
        """Convert Euler angles to quaternion."""
        cy = math.cos(yaw * 0.5)
        sy = math.sin(yaw * 0.5)
        cp = math.cos(pitch * 0.5)
        sp = math.sin(pitch * 0.5)
        cr = math.cos(roll * 0.5)
        sr = math.sin(roll * 0.5)
        
        q = Quaternion()
        q.w = cr * cp * cy + sr * sp * sy
        q.x = sr * cp * cy - cr * sp * sy
        q.y = cr * sp * cy + sr * cp * sy
        q.z = cr * cp * sy - sr * sp * cy
        
        return q


def main(args=None):
    """Main entry point for the mission scheduler node."""
    rclpy.init(args=args)
    scheduler = MissionScheduler()
    
    # Start default mission after initialization
    scheduler.start_mission()
    
    try:
        rclpy.spin(scheduler)
    except KeyboardInterrupt:
        scheduler.get_logger().info("Shutting down mission scheduler")
    finally:
        scheduler.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

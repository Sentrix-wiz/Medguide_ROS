#!/usr/bin/env python3
"""
Obstacle Detection Node for MedGuide.

Analyzes LaserScan data to detect obstacles and publish emergency stop signals.
Subscribes to /scan from robot's lidar, processes obstacle distance,
and publishes emergency stop commands if obstacle is too close.

Subscribes to:
  - /scan (sensor_msgs/LaserScan) - robot's lidar data

Publishes to:
  - /emergency_stop (std_msgs/Bool) - emergency stop signal
  - /obstacle_distance (std_msgs/Float32) - closest obstacle distance (meters)

Safety Behavior:
  - If obstacle < threshold: publish emergency_stop=True
  - Robot must explicitly clear emergency stop before resuming
"""

import math
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Bool, Float32

from medguide_utils.qos_profiles import SENSOR_QOS, STATUS_QOS
from medguide_utils.mission_config import OBSTACLE_DISTANCE_THRESHOLD
from medguide_utils.logging_utils import log_emergency_stop


class ObstacleDetector(Node):
    """Detects obstacles from LaserScan and triggers emergency stop when needed."""

    def __init__(self):
        super().__init__('obstacle_detector')
        
        # Parameters
        self.declare_parameter('obstacle_threshold_m', OBSTACLE_DISTANCE_THRESHOLD)
        self.declare_parameter('scan_topic', '/scan')
        self.declare_parameter('emergency_stop_topic', '/emergency_stop')
        self.declare_parameter('distance_topic', '/obstacle_distance')
        self.declare_parameter('filter_angle_degrees', 45.0)  # Front-facing cone
        self.declare_parameter('use_sim_time', True)
        
        # Subscriptions
        scan_topic = self.get_parameter('scan_topic').value
        self.scan_sub = self.create_subscription(
            LaserScan,
            scan_topic,
            self._scan_callback,
            SENSOR_QOS
        )
        
        # Publishers
        emergency_stop_topic = self.get_parameter('emergency_stop_topic').value
        self.emergency_stop_pub = self.create_publisher(
            Bool,
            emergency_stop_topic,
            STATUS_QOS
        )
        
        distance_topic = self.get_parameter('distance_topic').value
        self.distance_pub = self.create_publisher(
            Float32,
            distance_topic,
            STATUS_QOS
        )
        
        # State tracking
        self.emergency_stop_active = False
        self.closest_distance = float('inf')
        
        self.get_logger().info(
            f"ObstacleDetector initialized. "
            f"Threshold: {self.get_parameter('obstacle_threshold_m').value}m"
        )

    def _scan_callback(self, msg: LaserScan):
        """
        Process incoming LaserScan message.
        
        Filters scan rays to front-facing cone, finds closest obstacle,
        and publishes emergency stop if threshold is crossed.
        """
        # Get filter angle (degrees) and convert to filter cone
        filter_angle = self.get_parameter('filter_angle_degrees').value
        filter_rad = math.radians(filter_angle / 2)
        
        # Scan properties
        angle_min = msg.angle_min
        angle_increment = msg.angle_increment
        
        # Find closest obstacle in front-facing cone
        min_distance = float('inf')
        angle_to_obstacle = 0.0
        
        for i, range_val in enumerate(msg.ranges):
            # Skip invalid readings
            if math.isnan(range_val) or math.isinf(range_val):
                continue
            if range_val < msg.range_min or range_val > msg.range_max:
                continue
            
            # Calculate angle of this beam
            current_angle = angle_min + (i * angle_increment)
            
            # Filter to front-facing cone only
            if abs(current_angle) > filter_rad:
                continue
            
            # Track minimum distance
            if range_val < min_distance:
                min_distance = range_val
                angle_to_obstacle = current_angle
        
        # Update closest distance state
        self.closest_distance = min_distance
        
        # Publish distance
        dist_msg = Float32()
        dist_msg.data = self.closest_distance
        self.distance_pub.publish(dist_msg)
        
        # Check emergency threshold
        threshold = self.get_parameter('obstacle_threshold_m').value
        new_emergency_state = self.closest_distance < threshold
        
        # Log and publish emergency stop state
        if new_emergency_state and not self.emergency_stop_active:
            # Transition from safe to emergency
            log_emergency_stop(self.get_logger(), self.closest_distance)
            self.emergency_stop_active = True
            
            self.get_logger().warn(
                f"EMERGENCY STOP TRIGGERED! "
                f"Obstacle at {self.closest_distance:.3f}m "
                f"@ angle {math.degrees(angle_to_obstacle):.1f}°"
            )
        
        elif not new_emergency_state and self.emergency_stop_active:
            # Transition from emergency to safe
            self.get_logger().info(
                f"Emergency stop cleared. "
                f"Closest obstacle: {self.closest_distance:.3f}m"
            )
            self.emergency_stop_active = False
        
        # Publish emergency stop state
        emergency_msg = Bool()
        emergency_msg.data = self.emergency_stop_active
        self.emergency_stop_pub.publish(emergency_msg)


def main(args=None):
    """Main entry point for the obstacle detector node."""
    rclpy.init(args=args)
    node = ObstacleDetector()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Shutting down obstacle detector")
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

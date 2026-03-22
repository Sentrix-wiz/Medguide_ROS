#!/usr/bin/env python3
"""
Obstacle Detector Node — Phase 5 Safety Layer.

Analyzes LaserScan data to detect obstacles in a front-facing cone and
publishes emergency stop signals when obstacles are too close.

This node acts as an independent safety layer — it runs alongside Nav2
and can trigger emergency stops that pause mission execution.

Topics Subscribed
-----------------
    /scan (sensor_msgs/LaserScan) — lidar range data

Topics Published
----------------
    /emergency_stop    (std_msgs/Bool)    — True when obstacle too close
    /obstacle_distance (std_msgs/Float32) — closest obstacle distance (m)
    /obstacle_status   (std_msgs/String) — JSON status for mission_scheduler

Parameters
----------
    obstacle_threshold_m   (float) — emergency stop distance (default: 0.25)
    clear_threshold_m      (float) — hysteresis clear distance (default: 0.35)
    filter_angle_degrees   (float) — front-facing cone half-angle (default: 60)
    scan_topic             (str)   — LaserScan topic (default: '/scan')
    detection_rate_hz      (float) — max processing rate (default: 10.0)

"""

import math
import json


import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Bool, Float32, String


class ObstacleDetectorNode(Node):
    """Detects obstacles from LaserScan and triggers emergency stop."""

    def __init__(self):
        super().__init__('obstacle_detector')

        # Declare parameters
        self.declare_parameter('obstacle_threshold_m', 0.25)
        self.declare_parameter('clear_threshold_m', 0.35)
        self.declare_parameter('filter_angle_degrees', 60.0)
        self.declare_parameter('scan_topic', '/scan')
        self.declare_parameter('detection_rate_hz', 10.0)

        # Read parameters
        self.threshold = self.get_parameter('obstacle_threshold_m').value
        self.clear_threshold = self.get_parameter('clear_threshold_m').value
        self.filter_angle_deg = self.get_parameter('filter_angle_degrees').value
        self.filter_angle_rad = math.radians(self.filter_angle_deg / 2.0)
        scan_topic = self.get_parameter('scan_topic').value

        # QoS for sensor data (BEST_EFFORT to match Gazebo)
        sensor_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            depth=5,
        )

        # Subscriber
        self.scan_sub = self.create_subscription(
            LaserScan, scan_topic, self._scan_callback, sensor_qos
        )

        # Publishers
        self.estop_pub = self.create_publisher(Bool, '/emergency_stop', 10)
        self.distance_pub = self.create_publisher(
            Float32, '/obstacle_distance', 10
        )
        self.status_pub = self.create_publisher(
            String, '/obstacle_status', 10
        )

        # State
        self.emergency_active = False
        self.closest_distance = float('inf')
        self.obstacle_angle = 0.0
        self.scan_count = 0
        self.estop_trigger_count = 0
        self.last_process_time = self.get_clock().now()

        # Rate limiting
        rate = self.get_parameter('detection_rate_hz').value
        self.min_process_interval = 1.0 / rate

        self.get_logger().info(
            f'ObstacleDetector started: threshold={self.threshold}m, '
            f'clear={self.clear_threshold}m, cone=±{self.filter_angle_deg/2}°'
        )

    def _scan_callback(self, msg: LaserScan):
        """Process LaserScan and check for close obstacles."""
        # Rate limit processing
        now = self.get_clock().now()
        dt = (now - self.last_process_time).nanoseconds / 1e9
        if dt < self.min_process_interval:
            return
        self.last_process_time = now
        self.scan_count += 1

        # Find closest obstacle in front-facing cone
        min_dist = float('inf')
        min_angle = 0.0
        valid_rays = 0

        for i, r in enumerate(msg.ranges):
            # Skip invalid
            if math.isnan(r) or math.isinf(r):
                continue
            if r < msg.range_min or r > msg.range_max:
                continue

            # Calculate beam angle
            angle = msg.angle_min + (i * msg.angle_increment)

            # Filter to front cone only
            if abs(angle) > self.filter_angle_rad:
                continue

            valid_rays += 1
            if r < min_dist:
                min_dist = r
                min_angle = angle

        self.closest_distance = min_dist
        self.obstacle_angle = min_angle

        # Publish distance
        dist_msg = Float32()
        dist_msg.data = min_dist if min_dist != float('inf') else -1.0
        self.distance_pub.publish(dist_msg)

        # Emergency stop logic with hysteresis
        was_active = self.emergency_active

        if min_dist < self.threshold:
            self.emergency_active = True
        elif min_dist > self.clear_threshold:
            self.emergency_active = False

        # Publish emergency stop
        estop_msg = Bool()
        estop_msg.data = self.emergency_active
        self.estop_pub.publish(estop_msg)

        # Log state transitions
        if self.emergency_active and not was_active:
            self.estop_trigger_count += 1
            self.get_logger().error(
                f'🚨 EMERGENCY STOP #{self.estop_trigger_count}! '
                f'Obstacle at {min_dist:.3f}m '
                f'@ {math.degrees(min_angle):.1f}° '
                f'(threshold={self.threshold}m)'
            )
            self._publish_status('EMERGENCY_STOP', min_dist, min_angle)

        elif not self.emergency_active and was_active:
            self.get_logger().info(
                f'✅ Emergency stop CLEARED. '
                f'Closest: {min_dist:.3f}m > {self.clear_threshold}m'
            )
            self._publish_status('CLEAR', min_dist, min_angle)

        # Periodic status (every 50 scans)
        elif self.scan_count % 50 == 0:
            state = 'ESTOP' if self.emergency_active else 'SAFE'
            self.get_logger().info(
                f'[{state}] closest={min_dist:.2f}m '
                f'@ {math.degrees(min_angle):.1f}° '
                f'(rays={valid_rays}, stops={self.estop_trigger_count})'
            )

    def _publish_status(self, event: str, distance: float, angle: float):
        """Publish structured status for mission_scheduler consumption."""
        status = {
            'event': event,
            'distance_m': round(distance, 3),
            'angle_deg': round(math.degrees(angle), 1),
            'total_stops': self.estop_trigger_count,
            'scan_count': self.scan_count,
        }
        msg = String()
        msg.data = json.dumps(status)
        self.status_pub.publish(msg)


def main(args=None):
    """Entry point for the obstacle detector node."""
    rclpy.init(args=args)
    node = ObstacleDetectorNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()

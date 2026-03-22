#!/usr/bin/env python3
"""
Sensor Monitor Node — Phase 2 Learning Node.

Subscribes to real simulator sensor topics (/scan and /odom) and logs
periodic statistics. Teaches how to work with actual robotics message
types: LaserScan and Odometry.

Topics Subscribed
-----------------
    /scan  (sensor_msgs/LaserScan) — lidar range data from TurtleBot3
    /odom  (nav_msgs/Odometry)     — wheel odometry (position + velocity)

Parameters
----------
    scan_topic  (str)   — LaserScan topic name (default: '/scan')
    odom_topic  (str)   — Odometry topic name (default: '/odom')
    log_rate_hz (float) — How often to print stats (default: 0.5)

"""

import math

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import LaserScan
from nav_msgs.msg import Odometry


class SensorMonitorNode(Node):
    """Monitors /scan and /odom topics and logs human-readable stats."""

    def __init__(self):
        super().__init__('sensor_monitor')

        # Declare parameters
        self.declare_parameter('scan_topic', '/scan')
        self.declare_parameter('odom_topic', '/odom')
        self.declare_parameter('log_rate_hz', 0.5)

        scan_topic = self.get_parameter('scan_topic').value
        odom_topic = self.get_parameter('odom_topic').value
        log_rate_hz = self.get_parameter('log_rate_hz').value

        # QoS for sensor data — must match Gazebo publishers (BEST_EFFORT)
        sensor_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            depth=5,
        )

        # Subscribe to LaserScan
        self.scan_sub = self.create_subscription(
            LaserScan,
            scan_topic,
            self._scan_callback,
            sensor_qos,
        )

        # Subscribe to Odometry
        self.odom_sub = self.create_subscription(
            Odometry,
            odom_topic,
            self._odom_callback,
            sensor_qos,
        )

        # Latest data storage
        self.scan_count = 0
        self.scan_min = float('inf')
        self.scan_max = 0.0
        self.scan_mean = 0.0
        self.scan_rays = 0

        self.odom_count = 0
        self.robot_x = 0.0
        self.robot_y = 0.0
        self.robot_yaw = 0.0
        self.robot_linear_vel = 0.0
        self.robot_angular_vel = 0.0

        # Timer for periodic logging
        timer_period = 1.0 / log_rate_hz
        self.log_timer = self.create_timer(timer_period, self._log_stats)

        self.get_logger().info(
            f'SensorMonitor started: listening to {scan_topic} and {odom_topic} '
            f'(logging at {log_rate_hz} Hz)'
        )

    def _scan_callback(self, msg: LaserScan):
        """Process LaserScan message and extract statistics."""
        self.scan_count += 1

        # Filter valid ranges (not inf or nan)
        valid_ranges = [
            r for r in msg.ranges
            if not math.isinf(r) and not math.isnan(r)
            and msg.range_min <= r <= msg.range_max
        ]

        if valid_ranges:
            self.scan_min = min(valid_ranges)
            self.scan_max = max(valid_ranges)
            self.scan_mean = sum(valid_ranges) / len(valid_ranges)
        self.scan_rays = len(msg.ranges)

    def _odom_callback(self, msg: Odometry):
        """Process Odometry message and extract position/velocity."""
        self.odom_count += 1

        # Position
        self.robot_x = msg.pose.pose.position.x
        self.robot_y = msg.pose.pose.position.y

        # Extract yaw from quaternion
        q = msg.pose.pose.orientation
        siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
        cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        self.robot_yaw = math.atan2(siny_cosp, cosy_cosp)

        # Velocity
        self.robot_linear_vel = msg.twist.twist.linear.x
        self.robot_angular_vel = msg.twist.twist.angular.z

    def _log_stats(self):
        """Periodically log sensor statistics."""
        if self.scan_count == 0 and self.odom_count == 0:
            self.get_logger().warn('No sensor data received yet — is Gazebo running?')
            return

        self.get_logger().info(
            f'LIDAR: rays={self.scan_rays}, '
            f'min={self.scan_min:.2f}m, max={self.scan_max:.2f}m, '
            f'mean={self.scan_mean:.2f}m '
            f'({self.scan_count} msgs) | '
            f'ODOM: pos=({self.robot_x:.2f}, {self.robot_y:.2f}), '
            f'yaw={math.degrees(self.robot_yaw):.1f}°, '
            f'vel=({self.robot_linear_vel:.3f} m/s, '
            f'{self.robot_angular_vel:.3f} rad/s) '
            f'({self.odom_count} msgs)'
        )


def main(args=None):
    """Entry point for the sensor monitor node."""
    rclpy.init(args=args)
    node = SensorMonitorNode()

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

#!/usr/bin/env python3
"""
Diagnostics Node — System Health Monitor.

Aggregates sensor health and system state into a unified diagnostics
report published as DiagnosticArray and a human-readable JSON summary.

Monitors
--------
    - System orchestrator state (mode, stack, localized, estop)
    - Sensor data rates (scan, odom)
    - Node liveness (watchdog timeouts)

Topics Subscribed
-----------------
    /system_state  (SystemState) — from orchestrator (mode, estop, localized)
    /scan          (LaserScan)   — for rate monitoring
    /odom          (Odometry)    — for rate monitoring

Topics Published
----------------
    /diagnostics   (DiagnosticArray) — ROS2 standard diagnostics
    /system_health (String)          — JSON system health summary

Parameters
----------
    publish_rate_hz (float) — diagnostics publish rate (default: 1.0)
    node_timeout_sec (float) — watchdog timeout (default: 5.0)

"""

import json
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
from std_msgs.msg import Bool, Float32, String
from sensor_msgs.msg import LaserScan
from nav_msgs.msg import Odometry
from medguide_msgs.msg import SystemState


class DiagnosticsNode(Node):
    """Aggregates system-wide diagnostics from all MedGuide nodes."""

    def __init__(self):
        super().__init__('diagnostics_node')

        self.declare_parameter('publish_rate_hz', 1.0)
        self.declare_parameter('node_timeout_sec', 5.0)

        rate = self.get_parameter('publish_rate_hz').value
        self.timeout = self.get_parameter('node_timeout_sec').value

        # QoS
        sensor_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT, depth=5
        )

        # Subscribers
        self.create_subscription(
            SystemState, '/system_state', self._system_state_cb, 10
        )
        self.create_subscription(
            LaserScan, '/scan', self._scan_cb, sensor_qos
        )
        self.create_subscription(
            Odometry, '/odom', self._odom_cb, sensor_qos
        )
        self.create_subscription(
            String, '/mission_status_json', self._mission_cb, 10
        )
        self.create_subscription(
            Bool, '/emergency_stop', self._estop_cb, 10
        )
        self.create_subscription(
            Float32, '/obstacle_distance', self._obstacle_dist_cb, 10
        )

        # Publishers
        self.diag_pub = self.create_publisher(
            DiagnosticArray, '/diagnostics', 10
        )
        self.health_pub = self.create_publisher(
            String, '/system_health', 10
        )

        # State tracking
        self.mode = 'OFFLINE'
        self.emergency_stop = False
        self.obstacle_distance = -1.0
        self.localized = False
        self.mission_status = '{}'
        self.scan_count = 0
        self.odom_count = 0
        self.last_scan_time = 0.0
        self.last_odom_time = 0.0
        self.last_state_time = 0.0
        self.last_mission_time = 0.0
        self.last_estop_time = 0.0
        self.scan_rate = 0.0
        self.odom_rate = 0.0
        self._prev_scan_count = 0
        self._prev_odom_count = 0
        self.start_time = time.time()

        # Timer
        self.create_timer(1.0 / rate, self._publish_diagnostics)

        self.get_logger().info(
            f'Diagnostics started: {rate} Hz, '
            f'watchdog timeout={self.timeout}s'
        )

    # ── Callbacks ─────────────────────────────────────────────

    def _system_state_cb(self, msg):
        """Handle SystemState from orchestrator."""
        self.mode = msg.mode
        self.emergency_stop = msg.estop_active
        self.localized = msg.localized
        self.last_state_time = time.time()

    def _mission_cb(self, msg: String):
        self.mission_status = msg.data
        self.last_mission_time = time.time()

    def _estop_cb(self, msg: Bool):
        self.emergency_stop = msg.data
        self.last_estop_time = time.time()

    def _obstacle_dist_cb(self, msg: Float32):
        self.obstacle_distance = msg.data

    def _scan_cb(self, msg: LaserScan):
        self.scan_count += 1
        self.last_scan_time = time.time()

    def _odom_cb(self, msg: Odometry):
        self.odom_count += 1
        self.last_odom_time = time.time()

    # ── Diagnostics Publishing ────────────────────────────────

    def _publish_diagnostics(self):
        """Publish DiagnosticArray and JSON system health."""
        now = time.time()
        uptime = now - self.start_time

        # Calculate rates
        self.scan_rate = self.scan_count - self._prev_scan_count
        self.odom_rate = self.odom_count - self._prev_odom_count
        self._prev_scan_count = self.scan_count
        self._prev_odom_count = self.odom_count

        # Node liveness checks
        scan_alive = (
            (now - self.last_scan_time) < self.timeout
            if self.last_scan_time > 0 else False
        )
        odom_alive = (
            (now - self.last_odom_time) < self.timeout
            if self.last_odom_time > 0 else False
        )
        orchestrator_alive = (
            (now - self.last_state_time) < self.timeout
            if self.last_state_time > 0 else False
        )
        mission_alive = (
            (now - self.last_mission_time) < self.timeout
            if self.last_mission_time > 0 else False
        )
        estop_alive = (
            (now - self.last_estop_time) < self.timeout
            if self.last_estop_time > 0 else False
        )

        # Parse mission status
        try:
            mission_data = json.loads(self.mission_status)
        except (json.JSONDecodeError, TypeError):
            mission_data = {'state': 'UNKNOWN'}

        # ── DiagnosticArray ───────────────────────────────────

        diag_msg = DiagnosticArray()
        diag_msg.header.stamp = self.get_clock().now().to_msg()

        # Sensor status
        sensor_status = DiagnosticStatus()
        sensor_status.name = 'MedGuide/Sensors'
        sensor_status.level = (
            DiagnosticStatus.OK if (scan_alive and odom_alive)
            else DiagnosticStatus.WARN
        )
        sensor_status.message = 'Sensors active' if scan_alive else 'Sensor data missing'
        sensor_status.values = [
            KeyValue(key='scan_rate_hz', value=str(self.scan_rate)),
            KeyValue(key='odom_rate_hz', value=str(self.odom_rate)),
        ]

        # Safety status
        safety_status = DiagnosticStatus()
        safety_status.name = 'MedGuide/Safety'
        safety_status.level = (
            DiagnosticStatus.ERROR if self.emergency_stop
            else DiagnosticStatus.OK
        )
        safety_status.message = (
            'EMERGENCY STOP' if self.emergency_stop else 'Safe'
        )
        safety_status.values = [
            KeyValue(key='emergency_stop', value=str(self.emergency_stop)),
            KeyValue(key='localized', value=str(self.localized)),
        ]

        # System status
        system_status = DiagnosticStatus()
        system_status.name = 'MedGuide/System'
        system_status.level = DiagnosticStatus.OK
        system_status.message = f'Mode: {self.mode} | Uptime: {uptime:.0f}s'
        system_status.values = [
            KeyValue(key='mode', value=self.mode),
            KeyValue(key='uptime_sec', value=f'{uptime:.1f}'),
            KeyValue(
                key='nodes_alive',
                value=f'{sum([scan_alive, odom_alive, orchestrator_alive])}/3',
            ),
        ]

        diag_msg.status = [sensor_status, safety_status, system_status]
        self.diag_pub.publish(diag_msg)

        # ── JSON Health Summary ───────────────────────────────

        health = {
            'uptime_sec': round(uptime, 1),
            'sensors': {
                'scan_rate_hz': self.scan_rate,
                'odom_rate_hz': self.odom_rate,
                'scan_alive': scan_alive,
                'odom_alive': odom_alive,
            },
            'safety': {
                'emergency_stop': self.emergency_stop,
                'obstacle_m': round(self.obstacle_distance, 3),
            },
            'mission': mission_data,
            'nodes_alive': f'{sum([scan_alive, odom_alive, mission_alive, estop_alive])}/4',
        }

        health_msg = String()
        health_msg.data = json.dumps(health)
        self.health_pub.publish(health_msg)

        # Console log every 10s
        if int(uptime) % 10 == 0 and int(uptime) > 0:
            self.get_logger().info(
                f'[HEALTH] uptime={uptime:.0f}s '
                f'scan={self.scan_rate}Hz odom={self.odom_rate}Hz '
                f'estop={self.emergency_stop} '
                f'mission={mission_data.get("state", "UNKNOWN")} '
                f'nodes={sum([scan_alive, odom_alive, mission_alive, estop_alive])}/4'
            )


def main(args=None):
    """Entry point for the diagnostics node."""
    rclpy.init(args=args)
    node = DiagnosticsNode()

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

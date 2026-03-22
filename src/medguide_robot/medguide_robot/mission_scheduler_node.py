#!/usr/bin/env python3
"""
Mission Scheduler Node — Research-Grade Autonomous Delivery.

Orchestrates multi-room delivery missions using Nav2 NavigateToPose action.
Publishes typed MissionStatus/GoalResult messages. Tracks odometry distance.

Services
--------
    /start_mission (std_srvs/Trigger) — Start default mission sequence
    /abort_mission (std_srvs/Trigger) — Abort current mission

Topics Subscribed
-----------------
    /emergency_stop (std_msgs/Bool)   — from obstacle_detector
    /odom           (nav_msgs/Odometry) — for distance tracking

Topics Published
----------------
    /mission_status (medguide_msgs/MissionStatus) — typed mission state
    /goal_result    (medguide_msgs/GoalResult)    — per-goal result

Parameters
----------
    mission_rooms       (str list)  — Room visit sequence
    battery_drain_pct   (float)     — % drain per minute
    battery_abort_pct   (float)     — Abort below this %
    goal_timeout_sec    (float)     — Timeout per goal
    rooms.{name}.x/y/yaw (float)   — Goal coordinates (from YAML)

"""

import time
import math
import json
from enum import Enum

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from rclpy.action import ActionClient
from nav2_msgs.action import NavigateToPose
from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped
from nav_msgs.msg import Odometry
from std_msgs.msg import Bool, String
from std_srvs.srv import Trigger
from medguide_msgs.msg import MissionStatus, GoalResult


DEFAULT_MISSION = ['room_a', 'room_b', 'room_c', 'dock']

# Fallback room coords (overridden by YAML params)
DEFAULT_ROOMS = {
    'dock':   {'x': 0.5,  'y': 0.5,  'yaw': 0.0},
    'room_a': {'x': 1.0,  'y': 1.0,  'yaw': 0.0},
    'room_b': {'x': 5.0,  'y': 1.0,  'yaw': 1.57},
    'room_c': {'x': 5.0,  'y': 5.0,  'yaw': 3.14},
}


class MissionState(Enum):
    """Mission finite state machine states."""

    IDLE = 'IDLE'
    NAVIGATING = 'NAVIGATING'
    EMERGENCY_STOP = 'EMERGENCY_STOP'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'
    ABORTED = 'ABORTED'


class MissionSchedulerNode(Node):
    """Orchestrates multi-room delivery missions via Nav2."""

    def __init__(self):
        super().__init__('mission_scheduler')

        # Parameters
        self.declare_parameter('mission_rooms', DEFAULT_MISSION)
        self.declare_parameter('battery_drain_pct', 2.0)
        self.declare_parameter('battery_abort_pct', 10.0)
        self.declare_parameter('goal_timeout_sec', 120.0)

        # Load room coordinates from params (YAML) with fallback
        self.rooms = {}
        for name, defaults in DEFAULT_ROOMS.items():
            self.declare_parameter(f'rooms.{name}.x', defaults['x'])
            self.declare_parameter(f'rooms.{name}.y', defaults['y'])
            self.declare_parameter(f'rooms.{name}.yaw', defaults['yaw'])
            self.rooms[name] = {
                'x': self.get_parameter(f'rooms.{name}.x').value,
                'y': self.get_parameter(f'rooms.{name}.y').value,
                'yaw': self.get_parameter(f'rooms.{name}.yaw').value,
            }

        # Nav2 action client
        self._nav_client = ActionClient(
            self, NavigateToPose, 'navigate_to_pose'
        )

        # Services
        self.create_service(Trigger, 'start_mission', self._start_mission_cb)
        self.create_service(Trigger, 'abort_mission', self._abort_mission_cb)

        # Subscribers
        self.create_subscription(
            Bool, '/emergency_stop', self._estop_callback, 10
        )
        sensor_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT, depth=5
        )
        self.create_subscription(
            Odometry, '/odom', self._odom_callback, sensor_qos
        )

        # Publishers — typed messages
        self.status_pub = self.create_publisher(
            MissionStatus, '/mission_status', 10
        )
        self.result_pub = self.create_publisher(
            GoalResult, '/goal_result', 10
        )
        # Keep JSON for backwards compat with diagnostics/logger
        self.status_json_pub = self.create_publisher(
            String, '/mission_status_json', 10
        )

        # Mission state
        self.state = MissionState.IDLE
        self.mission_queue = []
        self.current_goal_idx = 0
        self.current_goal_name = ''
        self.emergency_stop_active = False
        self._goal_handle = None
        self.mission_id = ''
        self._next_goal_timer = None
        self._mission_first_goal = True  # Flag: first goal of a new mission
        self._goal_retry_count = 0
        self._max_goal_retries = 3

        # Initial pose publisher for AMCL
        self._init_pose_pub = self.create_publisher(
            PoseWithCovarianceStamped, '/initialpose', 10
        )

        # Metrics
        self.mission_start_time = 0.0
        self.goal_start_time = 0.0
        self.goals_succeeded = 0
        self.goals_failed = 0
        self.estop_count = 0
        self.battery_level = 100.0
        self.battery_start = 100.0

        # Odometry distance tracking
        self.total_distance_m = 0.0
        self.goal_distance_m = 0.0
        self._last_odom_x = None
        self._last_odom_y = None
        self._current_odom_x = 0.0
        self._current_odom_y = 0.0

        # Path efficiency: straight-line vs actual distance
        self.goal_start_x = 0.0
        self.goal_start_y = 0.0
        self.goal_target_x = 0.0
        self.goal_target_y = 0.0

        # Feedback counter
        self._feedback_count = 0

        # Timer for status publishing + battery simulation (2 Hz)
        self.create_timer(0.5, self._status_loop)

        self.get_logger().info(
            f'MissionScheduler ready. '
            f'Rooms: {list(self.rooms.keys())}. '
            f'Call /start_mission to begin.'
        )

    # ── Odometry Distance ─────────────────────────────────────

    def _odom_callback(self, msg: Odometry):
        """Accumulate Euclidean distance from odometry."""
        x = msg.pose.pose.position.x
        y = msg.pose.pose.position.y
        self._current_odom_x = x
        self._current_odom_y = y

        if self._last_odom_x is not None:
            dx = x - self._last_odom_x
            dy = y - self._last_odom_y
            dist = math.sqrt(dx * dx + dy * dy)
            # Filter out teleportation artifacts (> 1m between ticks)
            if dist < 1.0:
                self.total_distance_m += dist
                self.goal_distance_m += dist

        self._last_odom_x = x
        self._last_odom_y = y

    # ── Services ──────────────────────────────────────────────

    def _start_mission_cb(self, request, response):
        """Handle /start_mission service call."""
        if self.state == MissionState.NAVIGATING:
            response.success = False
            response.message = 'Mission already in progress'
            return response

        rooms = self.get_parameter('mission_rooms').value
        for r in rooms:
            if r not in self.rooms:
                response.success = False
                response.message = f'Unknown room: {r}'
                return response

        # Reset metrics
        self.mission_queue = list(rooms)
        self.current_goal_idx = 0
        self.goals_succeeded = 0
        self.goals_failed = 0
        self.estop_count = 0
        self.battery_start = self.battery_level
        self.mission_start_time = time.time()
        self.total_distance_m = 0.0
        self.mission_id = f'M{int(self.mission_start_time)}'
        self.state = MissionState.NAVIGATING
        self._mission_first_goal = True  # reset for readiness delay

        self.get_logger().info(
            f'🚀 MISSION {self.mission_id}: '
            f'{" → ".join(rooms)} ({len(rooms)} stops)'
        )

        self._send_next_goal()
        response.success = True
        response.message = f'Mission {self.mission_id}: {len(rooms)} goals'
        return response

    def _abort_mission_cb(self, request, response):
        """Handle /abort_mission service call."""
        if self.state in (MissionState.IDLE, MissionState.COMPLETED,
                          MissionState.ABORTED):
            response.success = False
            response.message = 'No active mission'
            return response

        self.state = MissionState.ABORTED
        if self._goal_handle:
            self._goal_handle.cancel_goal_async()

        self.get_logger().warn('⛔ Mission ABORTED')
        response.success = True
        response.message = 'Mission aborted'
        return response

    # ── Navigation ────────────────────────────────────────────

    def _publish_initial_pose(self):
        """Publish initial pose to /initialpose for AMCL convergence."""
        msg = PoseWithCovarianceStamped()
        msg.header.frame_id = 'map'
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.pose.pose.position.x = 1.0
        msg.pose.pose.position.y = 1.2
        msg.pose.pose.position.z = 0.0
        msg.pose.pose.orientation.w = 1.0
        # Covariance — moderate initial uncertainty
        msg.pose.covariance = [0.0] * 36
        msg.pose.covariance[0] = 0.25   # x variance
        msg.pose.covariance[7] = 0.25   # y variance
        msg.pose.covariance[35] = 0.07  # yaw variance
        self._init_pose_pub.publish(msg)
        self.get_logger().info('Published initial pose (1.0, 1.2, yaw=0.0)')

    def _send_current_goal_retry(self):
        """Retry sending the current goal without advancing the index."""
        room_name = self.mission_queue[self.current_goal_idx]
        room = self.rooms[room_name]
        self.goal_start_time = time.time()

        goal = NavigateToPose.Goal()
        goal.pose = PoseStamped()
        goal.pose.header.frame_id = 'map'
        goal.pose.header.stamp = self.get_clock().now().to_msg()
        goal.pose.pose.position.x = float(room['x'])
        goal.pose.pose.position.y = float(room['y'])
        goal.pose.pose.orientation.z = math.sin(float(room['yaw']) / 2.0)
        goal.pose.pose.orientation.w = math.cos(float(room['yaw']) / 2.0)

        future = self._nav_client.send_goal_async(
            goal, feedback_callback=self._nav_feedback
        )
        future.add_done_callback(self._goal_response_cb)

    def _send_next_goal(self):
        """Send the next goal in the mission queue to Nav2."""
        if self.current_goal_idx >= len(self.mission_queue):
            self._complete_mission()
            return

        if self.emergency_stop_active:
            self.state = MissionState.EMERGENCY_STOP
            return

        # Battery check
        abort_pct = float(self.get_parameter('battery_abort_pct').value)
        if self.battery_level < abort_pct:
            self.get_logger().error(
                f'🔋 Battery critical ({self.battery_level:.0f}%)'
            )
            self.state = MissionState.FAILED
            return

        room_name = self.mission_queue[self.current_goal_idx]
        room = self.rooms[room_name]
        self.current_goal_name = room_name
        self.goal_start_time = time.time()
        self.goal_distance_m = 0.0
        self.goal_start_x = self._current_odom_x
        self.goal_start_y = self._current_odom_y
        self.goal_target_x = float(room['x'])
        self.goal_target_y = float(room['y'])

        self.get_logger().info(
            f'📍 Goal {self.current_goal_idx + 1}/{len(self.mission_queue)}: '
            f'{room_name} → ({room["x"]:.1f}, {room["y"]:.1f})'
        )

        if not self._nav_client.wait_for_server(timeout_sec=10.0):
            self.get_logger().error('Nav2 action server not available after 10s — check stack launch')
            self._finish_goal(False)
            return

        # On first goal of a new mission, publish initial pose and wait for Nav2
        if self._mission_first_goal:
            self._mission_first_goal = False
            self._publish_initial_pose()
            self.get_logger().info(
                'Published initial pose. Waiting 5s for Nav2 '
                'planner/costmap/AMCL to fully activate...'
            )
            time.sleep(5.0)

        goal = NavigateToPose.Goal()
        goal.pose = PoseStamped()
        goal.pose.header.frame_id = 'map'
        goal.pose.header.stamp = self.get_clock().now().to_msg()
        goal.pose.pose.position.x = float(room['x'])
        goal.pose.pose.position.y = float(room['y'])
        goal.pose.pose.orientation.z = math.sin(float(room['yaw']) / 2.0)
        goal.pose.pose.orientation.w = math.cos(float(room['yaw']) / 2.0)

        self.state = MissionState.NAVIGATING
        future = self._nav_client.send_goal_async(
            goal, feedback_callback=self._nav_feedback
        )
        future.add_done_callback(self._goal_response_cb)

    def _goal_response_cb(self, future):
        """Handle Nav2 goal accept/reject."""
        goal_handle = future.result()
        if not goal_handle.accepted:
            self._goal_retry_count += 1
            elapsed = time.time() - self.goal_start_time
            self.get_logger().error(
                f'Goal [{self.current_goal_name}] REJECTED by Nav2 '
                f'(attempt {self._goal_retry_count}/{self._max_goal_retries}) — '
                f'check costmap inflation, goal tolerance, and initial pose. '
                f'Elapsed: {elapsed:.2f}s'
            )
            if self._goal_retry_count < self._max_goal_retries:
                self.get_logger().info(
                    f'Retrying goal [{self.current_goal_name}] in 5s...'
                )
                time.sleep(5.0)
                # Resend the same goal
                self._send_current_goal_retry()
                return
            else:
                self.get_logger().error(
                    f'Goal [{self.current_goal_name}] failed after '
                    f'{self._max_goal_retries} retries'
                )
                self._finish_goal(False)
            return

        self._goal_retry_count = 0  # Reset retry counter on acceptance
        self._goal_handle = goal_handle
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self._goal_result_cb)

    def _goal_result_cb(self, future):
        """Handle Nav2 goal completion."""
        result = future.result()
        self._goal_handle = None
        success = (result.status == 4)  # SUCCEEDED

        if success:
            self.get_logger().info(
                f'✅ Arrived at {self.current_goal_name} '
                f'(dist={self.goal_distance_m:.2f}m)'
            )
        else:
            self.get_logger().warn(
                f'❌ Failed: {self.current_goal_name} (status={result.status})'
            )

        self._finish_goal(success)

    def _finish_goal(self, success: bool):
        """Record goal result and advance to next."""
        duration = time.time() - self.goal_start_time

        if success:
            self.goals_succeeded += 1
        else:
            self.goals_failed += 1

        # Compute straight-line distance for path efficiency
        sl_dx = self.goal_target_x - self.goal_start_x
        sl_dy = self.goal_target_y - self.goal_start_y
        straight_line = math.sqrt(sl_dx * sl_dx + sl_dy * sl_dy)

        # Publish typed GoalResult
        result_msg = GoalResult()
        result_msg.header.stamp = self.get_clock().now().to_msg()
        result_msg.mission_id = self.mission_id
        result_msg.goal_name = self.current_goal_name
        result_msg.success = success
        result_msg.duration_sec = float(duration)
        result_msg.distance_m = float(self.goal_distance_m)
        result_msg.straight_line_m = float(straight_line)
        self.result_pub.publish(result_msg)

        self.current_goal_idx += 1

        if self.state not in (MissionState.ABORTED, MissionState.FAILED):
            # Cancel previous timer if any
            if self._next_goal_timer is not None:
                self._next_goal_timer.cancel()
            # Single-shot timer: fires once then cancels itself
            self._next_goal_timer = self.create_timer(
                1.0, self._fire_next_goal
            )

    def _fire_next_goal(self):
        """Single-shot timer callback to send next goal."""
        if self._next_goal_timer is not None:
            self._next_goal_timer.cancel()
            self._next_goal_timer = None
        self._send_next_goal()

    def _nav_feedback(self, feedback_msg):
        """Log navigation progress."""
        self._feedback_count += 1
        if self._feedback_count % 5 == 0:
            pos = feedback_msg.feedback.current_pose.pose.position
            self.get_logger().info(
                f'  → {self.current_goal_name}: '
                f'({pos.x:.2f}, {pos.y:.2f}) '
                f'dist={self.goal_distance_m:.2f}m'
            )

    # ── Emergency Stop ────────────────────────────────────────

    def _estop_callback(self, msg: Bool):
        """Handle emergency stop from obstacle detector."""
        was_active = self.emergency_stop_active
        self.emergency_stop_active = msg.data

        if msg.data and not was_active:
            self.estop_count += 1
            self.get_logger().error(f'🚨 E-stop #{self.estop_count}')
            if self.state == MissionState.NAVIGATING:
                self.state = MissionState.EMERGENCY_STOP
                if self._goal_handle:
                    self._goal_handle.cancel_goal_async()

        elif not msg.data and was_active:
            self.get_logger().info('✅ E-stop cleared')
            if self.state == MissionState.EMERGENCY_STOP:
                self._send_next_goal()

    # ── Mission Lifecycle ─────────────────────────────────────

    def _complete_mission(self):
        """Mark mission completed."""
        if self.state == MissionState.COMPLETED:
            return  # Already completed, no re-entry
        elapsed = time.time() - self.mission_start_time
        self.state = MissionState.COMPLETED
        battery_used = self.battery_start - self.battery_level

        self.get_logger().info(
            f'🏁 MISSION {self.mission_id} COMPLETE! '
            f'✅{self.goals_succeeded} ❌{self.goals_failed} '
            f'🚨{self.estop_count} '
            f'📏{self.total_distance_m:.1f}m '
            f'⏱️{elapsed:.1f}s '
            f'🔋{battery_used:.1f}%'
        )

    def _status_loop(self):
        """Publish status and simulate battery drain."""
        elapsed = 0.0
        if self.mission_start_time > 0:
            elapsed = time.time() - self.mission_start_time

        # Battery drain during navigation
        if self.state == MissionState.NAVIGATING and self.mission_start_time:
            drain = float(self.get_parameter('battery_drain_pct').value)
            self.battery_level = max(
                0.0, self.battery_start - (elapsed / 60.0 * drain)
            )

        # Publish typed MissionStatus
        msg = MissionStatus()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.mission_id = self.mission_id
        msg.state = self.state.value
        msg.current_goal = self.current_goal_name
        msg.goals_total = len(self.mission_queue)
        msg.goals_succeeded = self.goals_succeeded
        msg.goals_failed = self.goals_failed
        msg.emergency_stops = self.estop_count
        msg.battery_pct = float(self.battery_level)
        msg.distance_m = float(self.total_distance_m)
        msg.elapsed_sec = float(elapsed)
        self.status_pub.publish(msg)

        # Also publish JSON for backwards compat
        json_msg = String()
        json_msg.data = json.dumps({
            'state': self.state.value,
            'mission_id': self.mission_id,
            'goal': f'{self.current_goal_idx}/{len(self.mission_queue)}',
            'current_room': self.current_goal_name,
            'succeeded': self.goals_succeeded,
            'failed': self.goals_failed,
            'emergency_stops': self.estop_count,
            'battery_pct': round(self.battery_level, 1),
            'distance_m': round(self.total_distance_m, 2),
            'elapsed_sec': round(elapsed, 1),
        })
        self.status_json_pub.publish(json_msg)


def main(args=None):
    """Entry point."""
    rclpy.init(args=args)
    node = MissionSchedulerNode()
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

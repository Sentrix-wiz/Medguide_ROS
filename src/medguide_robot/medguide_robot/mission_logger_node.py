#!/usr/bin/env python3
"""
Mission Logger Node — Phase 7 Data Analytics.

Logs all mission events to timestamped JSON files for research analysis.
Each mission produces one log file with complete event history.

Log files are saved to: ~/medguide_ws/logs/mission_YYYYMMDD_HHMMSS.json

Subscribes to
-------------
    /mission_status    (String)  — mission state changes
    /emergency_stop    (Bool)    — obstacle emergency events
    /obstacle_distance (Float32) — closest obstacle readings
    /system_health     (String)  — system diagnostics

Output format
-------------
    {
        "mission_id": "20260319_103000",
        "start_time": "2026-03-19T10:30:00",
        "events": [...],
        "summary": { "duration_sec": ..., "goals_reached": ..., ... }
    }

"""

import json
import os
import time
from datetime import datetime
from pathlib import Path

import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, Float32, String


class MissionLoggerNode(Node):
    """Logs mission events to JSON files for research analysis."""

    def __init__(self):
        super().__init__('mission_logger')

        self.declare_parameter(
            'log_dir',
            os.path.expanduser('~/medguide_ws/logs')
        )
        self.declare_parameter('log_health_interval_sec', 10.0)

        self.log_dir = self.get_parameter('log_dir').value
        self.health_interval = self.get_parameter(
            'log_health_interval_sec'
        ).value

        # Create log directory
        Path(self.log_dir).mkdir(parents=True, exist_ok=True)

        # Subscribers
        self.create_subscription(
            String, '/mission_status', self._mission_cb, 10
        )
        self.create_subscription(
            Bool, '/emergency_stop', self._estop_cb, 10
        )
        self.create_subscription(
            Float32, '/obstacle_distance', self._obstacle_cb, 10
        )
        self.create_subscription(
            String, '/system_health', self._health_cb, 10
        )

        # State
        self.current_log = None
        self.current_file = None
        self.mission_active = False
        self.last_state = ''
        self.last_health_log = 0.0
        self.estop_active = False
        self.min_obstacle = float('inf')
        self.event_count = 0

        self.get_logger().info(
            f'MissionLogger ready. Logs → {self.log_dir}/'
        )

    def _start_log(self):
        """Start a new mission log file."""
        now = datetime.now()
        mission_id = now.strftime('%Y%m%d_%H%M%S')
        filename = f'mission_{mission_id}.json'
        filepath = os.path.join(self.log_dir, filename)

        self.current_log = {
            'mission_id': mission_id,
            'start_time': now.isoformat(),
            'end_time': None,
            'events': [],
            'summary': {},
        }
        self.current_file = filepath
        self.mission_active = True
        self.event_count = 0
        self.min_obstacle = float('inf')

        self._add_event('MISSION_START', {'file': filepath})
        self.get_logger().info(f'📝 Logging to {filename}')

    def _end_log(self, final_status: dict):
        """Finalize and save the mission log."""
        if not self.current_log:
            return

        self.current_log['end_time'] = datetime.now().isoformat()
        self.current_log['summary'] = {
            'total_events': self.event_count,
            'goals_succeeded': final_status.get('succeeded', 0),
            'goals_failed': final_status.get('failed', 0),
            'emergency_stops': final_status.get('emergency_stops', 0),
            'battery_remaining': final_status.get('battery_pct', '?'),
            'min_obstacle_m': (
                round(self.min_obstacle, 3)
                if self.min_obstacle != float('inf') else None
            ),
            'elapsed_sec': final_status.get('elapsed_sec', 0),
        }

        # Write to file
        try:
            with open(self.current_file, 'w') as f:
                json.dump(self.current_log, f, indent=2)
            self.get_logger().info(
                f'💾 Mission log saved: {self.current_file} '
                f'({self.event_count} events)'
            )
        except IOError as e:
            self.get_logger().error(f'Failed to write log: {e}')

        self.mission_active = False
        self.current_log = None

    def _add_event(self, event_type: str, data: dict = None):
        """Add a timestamped event to the current log."""
        if not self.current_log:
            return

        self.event_count += 1
        event = {
            'seq': self.event_count,
            'time': datetime.now().isoformat(),
            'type': event_type,
        }
        if data:
            event['data'] = data

        self.current_log['events'].append(event)

    # ── Callbacks ─────────────────────────────────────────────

    def _mission_cb(self, msg: String):
        """Handle mission status updates."""
        try:
            status = json.loads(msg.data)
        except (json.JSONDecodeError, TypeError):
            return

        state = status.get('state', '')

        # Detect mission start
        if state == 'NAVIGATING' and not self.mission_active:
            self._start_log()

        # Log state changes
        if state != self.last_state and self.mission_active:
            self._add_event('STATE_CHANGE', {
                'from': self.last_state,
                'to': state,
                'goal': status.get('current_room', ''),
                'progress': status.get('goal', ''),
                'battery': status.get('battery_pct', '?'),
            })
            self.last_state = state

        # Detect mission end
        if state in ('COMPLETED', 'FAILED', 'ABORTED') and self.mission_active:
            self._add_event(f'MISSION_{state}', status)
            self._end_log(status)

    def _estop_cb(self, msg: Bool):
        """Log emergency stop events."""
        if msg.data and not self.estop_active:
            self._add_event('EMERGENCY_STOP_ON')
            self.estop_active = True
        elif not msg.data and self.estop_active:
            self._add_event('EMERGENCY_STOP_OFF')
            self.estop_active = False

    def _obstacle_cb(self, msg: Float32):
        """Track minimum obstacle distance."""
        if msg.data > 0 and msg.data < self.min_obstacle:
            self.min_obstacle = msg.data

    def _health_cb(self, msg: String):
        """Log periodic health snapshots."""
        if not self.mission_active:
            return

        now = time.time()
        if now - self.last_health_log < self.health_interval:
            return
        self.last_health_log = now

        try:
            health = json.loads(msg.data)
            self._add_event('HEALTH_SNAPSHOT', health)
        except (json.JSONDecodeError, TypeError):
            pass


def main(args=None):
    """Entry point for the mission logger node."""
    rclpy.init(args=args)
    node = MissionLoggerNode()

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

#!/usr/bin/env python3
"""
Experiment Automation Script — Run N Mission Trials.

Connects to a running MedGuide-ROS stack, runs multiple missions,
and logs per-goal results to a CSV file for statistical analysis.

Prerequisites:
    1. Full stack running:
       ros2 launch medguide_robot medguide_full.launch.py

    2. Set initial pose in RViz2 (Nav2 must be localized)

Usage:
    python3 scripts/run_experiment.py --trials 5 --output results.csv

Output CSV columns:
    trial, mission_id, goal_name, success, duration_sec, distance_m

Summary printed to stdout after all trials complete.
"""

import argparse
import csv
import os
import time
from datetime import datetime

import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger
from medguide_msgs.msg import MissionStatus, GoalResult


class ExperimentRunner(Node):
    """Runs N mission trials and collects data."""

    def __init__(self, num_trials, output_path, delay_sec):
        super().__init__('experiment_runner')

        self.num_trials = num_trials
        self.output_path = output_path
        self.delay_sec = delay_sec

        # Service client
        self.start_client = self.create_client(Trigger, '/start_mission')

        # Subscribers
        self.create_subscription(
            MissionStatus, '/mission_status', self._status_cb, 10
        )
        self.create_subscription(
            GoalResult, '/goal_result', self._result_cb, 10
        )

        # State
        self.current_trial = 0
        self.mission_active = False
        self.results = []
        self.current_mission_id = ''
        self.trial_start_time = 0.0
        self.done = False

        # CSV file
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
        self.csv_file = open(output_path, 'w', newline='')
        self.csv_writer = csv.writer(self.csv_file)
        self.csv_writer.writerow([
            'trial', 'mission_id', 'goal_name', 'success',
            'duration_sec', 'distance_m', 'timestamp'
        ])

        self.get_logger().info(
            f'Experiment: {num_trials} trials → {output_path}'
        )

        # Track startup
        self._startup_wait_done = False
        self._startup_time = time.time()

        # Wait for service then start first trial
        self.create_timer(2.0, self._check_and_start)

    def _check_and_start(self):
        """Start next trial if ready."""
        if self.done or self.mission_active:
            return

        if self.current_trial >= self.num_trials:
            self._finish_experiment()
            return

        if not self.start_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().warn('Waiting for /start_mission service...')
            return

        # Wait 10s on first trial for AMCL to converge
        if not self._startup_wait_done:
            elapsed = time.time() - self._startup_time
            if elapsed < 10.0:
                self.get_logger().info(
                    f'Waiting for AMCL convergence... {10 - elapsed:.0f}s'
                )
                return
            self._startup_wait_done = True
            self.get_logger().info('AMCL converged — starting experiments')

        self.current_trial += 1
        self.trial_start_time = time.time()
        self.get_logger().info(
            f'━━━ Trial {self.current_trial}/{self.num_trials} ━━━'
        )

        req = Trigger.Request()
        future = self.start_client.call_async(req)
        future.add_done_callback(self._start_response)

    def _start_response(self, future):
        try:
            resp = future.result()
            if resp.success:
                self.mission_active = True
                self.get_logger().info(f'Mission started: {resp.message}')
            else:
                self.get_logger().warn(f'Start failed: {resp.message}')
        except Exception as e:
            self.get_logger().error(f'Service call failed: {e}')

    def _status_cb(self, msg: MissionStatus):
        """Detect mission completion."""
        self.current_mission_id = msg.mission_id

        if msg.state in ('COMPLETED', 'FAILED', 'ABORTED'):
            if self.mission_active:
                self.mission_active = False
                elapsed = time.time() - self.trial_start_time
                self.get_logger().info(
                    f'Trial {self.current_trial} {msg.state}: '
                    f'{msg.goals_succeeded}/{msg.goals_total} goals, '
                    f'{msg.distance_m:.1f}m, {elapsed:.1f}s'
                )

    def _result_cb(self, msg: GoalResult):
        """Log each goal result to CSV."""
        row = [
            self.current_trial,
            msg.mission_id,
            msg.goal_name,
            msg.success,
            round(msg.duration_sec, 2),
            round(msg.distance_m, 2),
            datetime.now().isoformat(),
        ]
        self.csv_writer.writerow(row)
        self.csv_file.flush()
        self.results.append(row)

    def _finish_experiment(self):
        """Print summary statistics and exit."""
        self.done = True
        self.csv_file.close()

        if not self.results:
            self.get_logger().warn('No results collected!')
            return

        # Compute statistics
        total_goals = len(self.results)
        successes = sum(1 for r in self.results if r[3])
        durations = [r[4] for r in self.results if r[3]]
        distances = [r[5] for r in self.results if r[3]]

        success_rate = successes / total_goals * 100 if total_goals else 0
        avg_time = sum(durations) / len(durations) if durations else 0
        avg_dist = sum(distances) / len(distances) if distances else 0

        self.get_logger().info('')
        self.get_logger().info('═══════════════════════════════════════')
        self.get_logger().info('       EXPERIMENT SUMMARY')
        self.get_logger().info('═══════════════════════════════════════')
        self.get_logger().info(f'  Trials:         {self.num_trials}')
        self.get_logger().info(f'  Total goals:    {total_goals}')
        self.get_logger().info(f'  Success rate:   {success_rate:.1f}%')
        self.get_logger().info(f'  Avg time/goal:  {avg_time:.1f}s')
        self.get_logger().info(f'  Avg dist/goal:  {avg_dist:.2f}m')
        self.get_logger().info(f'  CSV saved:      {self.output_path}')
        self.get_logger().info('═══════════════════════════════════════')

        # Force exit after logging
        self.create_timer(1.0, lambda: rclpy.shutdown())


def main():
    parser = argparse.ArgumentParser(
        description='Run MedGuide mission experiments'
    )
    parser.add_argument(
        '--trials', type=int, default=3,
        help='Number of mission trials (default: 3)'
    )
    parser.add_argument(
        '--output', type=str,
        default=os.path.expanduser('~/medguide_ws/logs/experiment_results.csv'),
        help='Output CSV path'
    )
    parser.add_argument(
        '--delay', type=float, default=5.0,
        help='Delay between trials in seconds'
    )
    args = parser.parse_args()

    rclpy.init()
    node = ExperimentRunner(args.trials, args.output, args.delay)

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

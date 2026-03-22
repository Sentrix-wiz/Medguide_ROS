#!/usr/bin/env python3
"""
Experiment Orchestrator — Central ROS2 system controller.

Manages system lifecycle, mode switching, and experiment automation.
The dashboard communicates ONLY through this node's services/topics.

Services Provided
-----------------
    /set_mode        (SetMode)         — Switch system mode
    /run_experiment  (RunExperiment)   — Start N-trial experiment

Topics Published
----------------
    /system_state    (SystemState)     — Unified status @ 2Hz

Topics Subscribed
-----------------
    /amcl_pose      — Detects AMCL convergence (localization ready)
    /mission_status — Tracks mission completion for experiments
    /emergency_stop — E-stop state

Modes: OFFLINE → LAUNCHING → IDLE → TELEOP / AUTONOMOUS / EXPERIMENT
"""

import os
import signal
import subprocess
import threading
import time

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseWithCovarianceStamped
from std_msgs.msg import Bool
from std_srvs.srv import Trigger

from medguide_msgs.msg import MissionStatus, SystemState
from medguide_msgs.srv import SetMode, RunExperiment


# Workspace root
WS = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')
)
if not os.path.isdir(os.path.join(WS, 'install')):
    WS = os.path.expanduser('~/medguide_ws')

VALID_MODES = {
    'LAUNCH', 'IDLE', 'TELEOP', 'AUTONOMOUS',
    'EXPERIMENT', 'SHUTDOWN',
}


class ExperimentOrchestrator(Node):
    """Central orchestrator for MedGuide-ROS system."""

    def __init__(self):
        super().__init__('experiment_orchestrator')

        # ── State ────────────────────────────────────
        self.mode = 'OFFLINE'
        self.stack_running = False
        self.localized = False
        self.estop_active = False
        self.battery_pct = 100.0
        self.active_goal = ''
        self.experiment_trial = 0
        self.experiment_total = 0

        # Process handles
        self._launch_proc = None
        self._teleop_proc = None

        # Mission tracking for experiments
        self._mission_state = 'IDLE'
        self._mission_complete_event = threading.Event()

        # ── Services ─────────────────────────────────
        self.create_service(
            SetMode, '/set_mode', self._set_mode_cb)
        self.create_service(
            RunExperiment, '/run_experiment', self._run_experiment_cb)

        # ── Service Clients ──────────────────────────
        self._start_mission_client = self.create_client(
            Trigger, '/start_mission')
        self._abort_mission_client = self.create_client(
            Trigger, '/abort_mission')

        # ── Publishers ───────────────────────────────
        self._state_pub = self.create_publisher(
            SystemState, '/system_state', 10)

        # ── Subscribers ──────────────────────────────
        self.create_subscription(
            PoseWithCovarianceStamped, '/amcl_pose',
            self._amcl_cb, 10)
        self.create_subscription(
            Bool, '/emergency_stop',
            self._estop_cb, 10)
        self.create_subscription(
            MissionStatus, '/mission_status',
            self._mission_status_cb, 10)

        # ── Timer: publish state @ 2Hz ───────────────
        self.create_timer(0.5, self._publish_state)

        self.get_logger().info(
            '╔════════════════════════════════════════╗')
        self.get_logger().info(
            '║  Experiment Orchestrator READY          ║')
        self.get_logger().info(
            '╚════════════════════════════════════════╝')

    # ── State Publishing ─────────────────────────────

    def _publish_state(self):
        """Publish unified system state at 2Hz."""
        # Check if launch process died
        if self._launch_proc and self._launch_proc.poll() is not None:
            self.stack_running = False
            self.localized = False
            if self.mode not in ('OFFLINE', 'LAUNCHING'):
                self.mode = 'OFFLINE'
                self.get_logger().warn('Stack process died — OFFLINE')

        msg = SystemState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.mode = self.mode
        msg.stack_running = self.stack_running
        msg.localized = self.localized
        msg.estop_active = self.estop_active
        msg.experiment_trial = self.experiment_trial
        msg.experiment_total = self.experiment_total
        msg.battery_pct = self.battery_pct
        msg.active_goal = self.active_goal
        self._state_pub.publish(msg)

    # ── Subscribers ──────────────────────────────────

    def _amcl_cb(self, msg):
        """AMCL pose received — robot is localized."""
        if not self.localized:
            self.localized = True
            self.get_logger().info('✅ AMCL localized — ready')
            if self.mode == 'LAUNCHING':
                self.mode = 'IDLE'
                self.get_logger().info('Mode → IDLE (stack ready)')

    def _estop_cb(self, msg):
        """Track emergency stop state."""
        self.estop_active = msg.data

    def _mission_status_cb(self, msg):
        """Track mission state for experiment loop."""
        self._mission_state = msg.state
        self.battery_pct = msg.battery_pct
        self.active_goal = msg.current_goal or ''

        if msg.state in ('COMPLETED', 'FAILED', 'ABORTED'):
            self._mission_complete_event.set()

    # ── SetMode Service ──────────────────────────────

    def _set_mode_cb(self, request, response):
        """Handle /set_mode service call."""
        target = request.mode.upper().strip()
        self.get_logger().info(f'SetMode: {self.mode} → {target}')

        if target not in VALID_MODES:
            response.success = False
            response.message = f'Invalid mode: {target}'
            return response

        # Dispatch
        if target == 'LAUNCH':
            return self._do_launch(response)
        elif target == 'SHUTDOWN':
            return self._do_shutdown(response)
        elif target == 'IDLE':
            return self._do_idle(response)
        elif target == 'TELEOP':
            return self._do_teleop(response)
        elif target == 'AUTONOMOUS':
            return self._do_autonomous(response)
        elif target == 'EXPERIMENT':
            response.success = False
            response.message = 'Use /run_experiment service'
            return response

        return response

    def _do_launch(self, response):
        """Launch the full simulation stack."""
        if self.stack_running:
            response.success = False
            response.message = 'Stack already running'
            return response

        self.mode = 'LAUNCHING'
        self.localized = False
        self.get_logger().info('🚀 Launching full stack...')

        cmd = (
            'source /opt/ros/humble/setup.bash && '
            f'source {WS}/install/setup.bash && '
            'export TURTLEBOT3_MODEL=burger && '
            'ros2 launch medguide_robot medguide_full.launch.py'
        )
        log_dir = os.path.join(WS, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        log_file = open(
            os.path.join(log_dir, 'stack_stderr.log'), 'w')

        self._launch_proc = subprocess.Popen(
            cmd, shell=True, executable='/bin/bash',
            stdout=subprocess.DEVNULL, stderr=log_file,
            preexec_fn=os.setsid,
        )
        self.stack_running = True

        # Auto-transition to IDLE after AMCL converges (or timeout)
        def _wait_for_ready():
            for i in range(60):  # Max 60 seconds
                time.sleep(1)
                if self.localized:
                    return
                if self._launch_proc.poll() is not None:
                    self.stack_running = False
                    self.mode = 'OFFLINE'
                    self.get_logger().error('Stack launch failed')
                    return
            # Timeout: assume ready if stack still running
            if self.stack_running:
                self.mode = 'IDLE'
                self.get_logger().warn(
                    'AMCL timeout — assuming ready')

        threading.Thread(target=_wait_for_ready, daemon=True).start()

        response.success = True
        response.message = 'Stack launching — waiting for AMCL'
        return response

    def _do_shutdown(self, response):
        """Shut down the stack."""
        self._kill_teleop()
        if self._launch_proc and self._launch_proc.poll() is None:
            try:
                os.killpg(
                    os.getpgid(self._launch_proc.pid),
                    signal.SIGTERM)
                self._launch_proc.wait(timeout=10)
            except Exception:
                pass
        subprocess.run(
            'killall -9 gzserver gzclient 2>/dev/null',
            shell=True, stderr=subprocess.DEVNULL)

        self._launch_proc = None
        self.stack_running = False
        self.localized = False
        self.mode = 'OFFLINE'
        self.experiment_trial = 0
        self.experiment_total = 0

        response.success = True
        response.message = 'Stack shut down'
        self.get_logger().info('🛑 Stack shut down')
        return response

    def _do_idle(self, response):
        """Return to idle — abort if navigating."""
        self._kill_teleop()

        if self.mode in ('AUTONOMOUS', 'EXPERIMENT'):
            # Abort active mission
            if self._abort_mission_client.wait_for_service(
                    timeout_sec=2.0):
                self._abort_mission_client.call_async(
                    Trigger.Request())

        self.mode = 'IDLE'
        self.experiment_trial = 0
        self.experiment_total = 0
        response.success = True
        response.message = 'Mode → IDLE'
        return response

    def _do_teleop(self, response):
        """Enable manual teleop control."""
        if not self.stack_running:
            response.success = False
            response.message = 'Stack not running'
            return response
        if self.mode in ('AUTONOMOUS', 'EXPERIMENT'):
            response.success = False
            response.message = (
                f'Cannot teleop during {self.mode} — '
                f'abort first')
            return response

        self.mode = 'TELEOP'
        # Launch teleop terminal
        teleop_cmd = (
            'gnome-terminal -- bash -c "'
            'source /opt/ros/humble/setup.bash && '
            f'source {WS}/install/setup.bash && '
            'export TURTLEBOT3_MODEL=burger && '
            'ros2 run turtlebot3_teleop teleop_keyboard; '
            'exec bash"'
        )
        try:
            self._teleop_proc = subprocess.Popen(
                teleop_cmd, shell=True,
                stderr=subprocess.DEVNULL)
        except Exception:
            pass

        response.success = True
        response.message = 'Teleop terminal opened'
        self.get_logger().info('🎮 Teleop active')
        return response

    def _do_autonomous(self, response):
        """Start a single autonomous mission."""
        if not self.stack_running:
            response.success = False
            response.message = 'Stack not running'
            return response
        if self.mode in ('EXPERIMENT',):
            response.success = False
            response.message = 'Experiment running — abort first'
            return response

        self._kill_teleop()
        self.mode = 'AUTONOMOUS'

        # Call /start_mission
        if not self._start_mission_client.wait_for_service(
                timeout_sec=3.0):
            response.success = False
            response.message = '/start_mission not available'
            self.mode = 'IDLE'
            return response

        future = self._start_mission_client.call_async(
            Trigger.Request())
        future.add_done_callback(self._mission_start_done)

        response.success = True
        response.message = 'Mission started'
        self.get_logger().info('🤖 Autonomous mission started')
        return response

    def _mission_start_done(self, future):
        """Callback when start_mission service returns."""
        try:
            result = future.result()
            if not result.success:
                self.get_logger().warn(
                    f'Mission start failed: {result.message}')
                self.mode = 'IDLE'
        except Exception as e:
            self.get_logger().error(f'Mission call failed: {e}')
            self.mode = 'IDLE'

    # ── Experiment Service ───────────────────────────

    def _run_experiment_cb(self, request, response):
        """Handle /run_experiment — runs N mission trials."""
        if not self.stack_running:
            response.success = False
            response.message = 'Stack not running'
            return response
        if self.mode in ('AUTONOMOUS', 'EXPERIMENT'):
            response.success = False
            response.message = f'Cannot experiment during {self.mode}'
            return response

        num = max(1, min(50, request.num_trials))
        self.get_logger().info(
            f'📊 Experiment: {num} trials starting')
        self._kill_teleop()
        self.mode = 'EXPERIMENT'
        self.experiment_total = num
        self.experiment_trial = 0

        # Run trials in background thread
        threading.Thread(
            target=self._experiment_loop,
            args=(num,), daemon=True).start()

        response.success = True
        response.message = f'Experiment: {num} trials started'
        return response

    def _experiment_loop(self, num_trials):
        """Background: run N mission trials sequentially."""
        for i in range(num_trials):
            if self.mode != 'EXPERIMENT':
                self.get_logger().warn('Experiment aborted')
                break

            self.experiment_trial = i + 1
            self.get_logger().info(
                f'━━━ Trial {i + 1}/{num_trials} ━━━')

            # Wait for mission service
            if not self._start_mission_client.wait_for_service(
                    timeout_sec=5.0):
                self.get_logger().error(
                    '/start_mission not available')
                break

            # Clear completion event and start mission
            self._mission_complete_event.clear()
            future = self._start_mission_client.call_async(
                Trigger.Request())

            # Wait for result
            try:
                rclpy.spin_until_future_complete(
                    self, future, timeout_sec=5.0)
            except Exception:
                pass

            # Wait for mission to finish (max 120s)
            completed = self._mission_complete_event.wait(
                timeout=120.0)
            if not completed:
                self.get_logger().warn(
                    f'Trial {i + 1} timed out')

            # Inter-trial delay
            if i < num_trials - 1:
                time.sleep(3.0)

        self.get_logger().info(
            f'📊 Experiment done: {self.experiment_trial} trials')
        self.experiment_trial = 0
        self.experiment_total = 0
        self.mode = 'IDLE'

    # ── Helpers ──────────────────────────────────────

    def _kill_teleop(self):
        """Kill teleop terminal if running."""
        if self._teleop_proc and self._teleop_proc.poll() is None:
            try:
                self._teleop_proc.terminate()
            except Exception:
                pass
            self._teleop_proc = None

    def destroy_node(self):
        """Clean shutdown."""
        self._kill_teleop()
        if self._launch_proc and self._launch_proc.poll() is None:
            try:
                os.killpg(
                    os.getpgid(self._launch_proc.pid),
                    signal.SIGTERM)
            except Exception:
                pass
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = ExperimentOrchestrator()
    executor = rclpy.executors.MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

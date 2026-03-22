#!/usr/bin/env python3
"""
MedGuide-ROS — Experiment Dashboard (v1.0).
FUTURISTIC COMMAND CONSOLE

Developed by: Pragadeesh
Project: MedGuide-ROS Autonomous Hospital Navigation System
"""

import os
import sys
import time
import threading

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QPushButton, QGroupBox, QSpinBox,
    QTextEdit, QFrame, QProgressBar, QStackedWidget,
    QGraphicsDropShadowEffect, QGraphicsOpacityEffect
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject, QEvent, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QFont, QColor, QPalette, QKeySequence

try:
    import rclpy
    from rclpy.node import Node
    from medguide_msgs.msg import (
        MissionStatus, GoalResult, SystemState,
    )
    from geometry_msgs.msg import Twist
    from medguide_msgs.srv import SetMode, RunExperiment
    ROS_AVAILABLE = True
except ImportError:
    ROS_AVAILABLE = False

# ── Colors ───────────────────────────────────────────
C = {
    'bg':       '#08090f',  
    'panel':    'rgba(14, 18, 30, 0.85)',  
    'border':   '#1e253c',
    'text':     '#e2e8f0',
    'dim':      '#64748b',
    'accent':   '#00f3ff',  
    'green':    '#39ff14',  
    'red':      '#ff003c',  
    'yellow':   '#facc15',  
    'blue':     '#3b82f6',
    'cyan':     '#00f3ff',
    'purple':   '#b537f2',  
}

STYLESHEET = f"""
QMainWindow {{ background-color: {C['bg']}; font-family: 'Segoe UI', Inter, sans-serif; }}
QGroupBox {{
    background-color: {C['panel']}; 
    border: 1px solid {C['border']};
    border-radius: 12px; margin-top: 16px; padding: 12px; padding-top: 24px;
    font-size: 14px; font-weight: bold; color: {C['text']};
}}
QGroupBox::title {{
    subcontrol-origin: margin; left: 16px; padding: 0 4px;
    color: {C['accent']}; font-size: 13px; font-weight: 800; text-transform: uppercase;
    letter-spacing: 2px;
}}
QLabel {{ color: {C['text']}; font-size: 13px; }}
QPushButton {{
    background-color: rgba(0, 243, 255, 0.05); color: {C['accent']};
    border: 1px solid {C['accent']}; border-radius: 8px; padding: 10px 16px; 
    font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px;
}}
QPushButton:hover {{ background-color: rgba(0, 243, 255, 0.2); }}
QPushButton:pressed {{ background-color: {C['accent']}; color: {C['bg']}; }}
QPushButton:disabled {{
    background-color: {C['bg']}; color: {C['dim']}; border: 1px solid {C['border']};
}}
QPushButton#launchBtn {{
    background-color: rgba(57, 255, 20, 0.15); color: {C['green']}; border-color: {C['green']};
}}
QPushButton#launchBtn:hover {{ background-color: rgba(57, 255, 20, 0.3); }}
QPushButton#dangerBtn {{
    background-color: rgba(255, 0, 60, 0.15); color: {C['red']}; border-color: {C['red']};
}}
QPushButton#dangerBtn:hover {{ background-color: rgba(255, 0, 60, 0.3); }}
QPushButton#dangerBtn:pressed {{ background-color: {C['red']}; color: white; }}
QPushButton#teleopBtn {{
    background-color: rgba(181, 55, 242, 0.15); color: {C['purple']}; border-color: {C['purple']};
}}
QPushButton#teleopBtn:hover {{ background-color: rgba(181, 55, 242, 0.3); }}

QTextEdit {{
    background-color: #050508; color: {C['accent']};
    border: 1px solid {C['border']}; border-radius: 8px;
    font-family: 'Consolas', 'Fira Code', monospace;
    font-size: 12px; padding: 10px; line-height: 1.5;
}}
QSpinBox {{
    background-color: {C['bg']}; color: {C['accent']};
    border: 1px solid {C['accent']}; border-radius: 6px;
    padding: 6px 12px; font-size: 14px; font-weight: bold; min-width: 60px;
}}
QProgressBar {{
    background-color: {C['bg']}; border: 1px solid {C['border']};
    border-radius: 8px; text-align: center; font-size: 12px;
    font-weight: 800; color: white; min-height: 24px;
}}
QProgressBar::chunk {{
    background-color: {C['green']}; border-radius: 6px; width: 10px; margin: 2px;
}}
"""

# ── ROS2 Bridge ─────────────────────────────────────



class RosBridge(QObject):
    """Thin ROS2 bridge — subscriptions + service callers."""

    state_updated = pyqtSignal(dict)
    mission_updated = pyqtSignal(dict)
    result_received = pyqtSignal(dict)
    log_msg = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._node = None
        self._running = False
        self._linear = 0.0
        self._angular = 0.0

    def start(self):
        if not ROS_AVAILABLE:
            self.log_msg.emit(
                "⚠ ROS2 not sourced — source install/setup.bash")
            return
        self._running = True
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        try:
            rclpy.init()
        except RuntimeError:
            pass
        self._node = Node('dashboard_ui')

        # Subscriptions
        self._node.create_subscription(
            SystemState, '/system_state', self._state_cb, 10)
        self._node.create_subscription(
            MissionStatus, '/mission_status', self._mission_cb, 10)
        self._node.create_subscription(
            GoalResult, '/goal_result', self._result_cb, 10)

        # Service clients
        self._set_mode = self._node.create_client(
            SetMode, '/set_mode')
        self._run_exp = self._node.create_client(
            RunExperiment, '/run_experiment')

        # Teleop Publisher
        self._cmd_pub = self._node.create_publisher(Twist, '/cmd_vel', 10)
        self._node.create_timer(0.1, self._publish_cmd)

        self.log_msg.emit("✅ Dashboard connected to ROS2")

        while self._running and rclpy.ok():
            rclpy.spin_once(self._node, timeout_sec=0.1)

    def _publish_cmd(self):
        msg = Twist()
        msg.linear.x = self._linear
        msg.angular.z = self._angular
        self._cmd_pub.publish(msg)

    def send_cmd_vel(self, linear, angular):
        self._linear = float(linear)
        self._angular = float(angular)

    # ── Callbacks ────────────────────────────────────

    def _state_cb(self, msg):
        self.state_updated.emit({
            'mode': msg.mode,
            'stack_running': msg.stack_running,
            'localized': msg.localized,
            'estop_active': msg.estop_active,
            'experiment_trial': msg.experiment_trial,
            'experiment_total': msg.experiment_total,
            'battery_pct': msg.battery_pct,
            'active_goal': msg.active_goal,
        })

    def _mission_cb(self, msg):
        self.mission_updated.emit({
            'mission_id': msg.mission_id,
            'state': msg.state,
            'current_goal': msg.current_goal,
            'goals_total': msg.goals_total,
            'goals_succeeded': msg.goals_succeeded,
            'goals_failed': msg.goals_failed,
            'emergency_stops': msg.emergency_stops,
            'battery_pct': msg.battery_pct,
            'distance_m': msg.distance_m,
            'elapsed_sec': msg.elapsed_sec,
        })

    def _result_cb(self, msg):
        self.result_received.emit({
            'goal_name': msg.goal_name,
            'success': msg.success,
            'duration_sec': msg.duration_sec,
            'distance_m': msg.distance_m,
            'straight_line_m': msg.straight_line_m,
        })

    # ── Service Calls ────────────────────────────────

    def call_set_mode(self, mode):
        """Call /set_mode on orchestrator."""
        if not self._node:
            self.log_msg.emit("❌ ROS2 not connected")
            return
        if not self._set_mode.wait_for_service(timeout_sec=3.0):
            self.log_msg.emit(
                "⚠ Orchestrator not running — "
                "start it: ros2 run medguide_robot orchestrator")
            return
        req = SetMode.Request()
        req.mode = mode
        future = self._set_mode.call_async(req)
        future.add_done_callback(
            lambda f: self._service_done(f, mode))

    def call_run_experiment(self, n):
        """Call /run_experiment on orchestrator."""
        if not self._node:
            return
        if not self._run_exp.wait_for_service(timeout_sec=3.0):
            self.log_msg.emit("⚠ Orchestrator not available")
            return
        req = RunExperiment.Request()
        req.num_trials = n
        future = self._run_exp.call_async(req)
        future.add_done_callback(
            lambda f: self._service_done(f, f'experiment({n})'))

    def _service_done(self, future, label):
        try:
            r = future.result()
            icon = '[OK]' if r.success else '[FAIL]'
            self.log_msg.emit(f"{icon} {label}: {r.message}")
        except Exception as e:
            self.log_msg.emit(f"[FAIL] {label} failed: {e}")

    def stop(self):
        self._running = False
        if hasattr(self, '_thread') and self._thread.is_alive():
            self._thread.join(timeout=1.0)



# ── Dashboard Window ─────────────────────────────────

class Dashboard(QMainWindow):
    """Futuristic Experiment Dashboard — ROS2 services only."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("🏥 MedGuide-ROS — Command Console v1.0")
        self.setMinimumSize(1024, 768)
        self.setStyleSheet(STYLESHEET)

        self.ros = RosBridge()
        self.ros.state_updated.connect(self._on_state)
        self.ros.mission_updated.connect(self._on_mission)
        self.ros.result_received.connect(self._on_result)
        self.ros.log_msg.connect(self._on_log)

        self.trial_results = []
        self._current_mode = 'OFFLINE'
        self._keys_held = set()
        self._led_anim_tick = 0
        self._pulse_tick = 0
        self._pulse_dir = 1
        
        self.stack_op = None

        w = QWidget()
        self.setCentralWidget(w)
        root = QVBoxLayout(w)
        root.setSpacing(20)
        root.setContentsMargins(24, 24, 24, 24)

        # Header
        hdr = QLabel("MEDGUIDE // COMMAND_CONSOLE")
        hdr.setFont(QFont("Monospace", 24, QFont.Bold))
        hdr.setStyleSheet(f"color: {C['cyan']}; letter-spacing: 4px;")
        hdr.setAlignment(Qt.AlignCenter)
        
        glow = QGraphicsDropShadowEffect(self)
        glow.setColor(QColor(C['cyan']))
        glow.setBlurRadius(20)
        glow.setOffset(0, 0)
        hdr.setGraphicsEffect(glow)
        root.addWidget(hdr)

        # Zone Top: System + Mission
        top = QHBoxLayout()
        top.setSpacing(20)
        top.addWidget(self._build_system())
        top.addWidget(self._build_mission())
        root.addLayout(top, stretch=1)

        # Zone Mid: Dynamic Control Stage
        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_controls())      # Index 0
        self.stack.addWidget(self._build_teleop_panel())  # Index 1
        
        self.stack_op = QGraphicsOpacityEffect(self.stack)
        self.stack_op.setOpacity(1.0)
        self.stack.setGraphicsEffect(self.stack_op)
        root.addWidget(self.stack, stretch=0)

        # Zone Bottom: Results + Logs
        bot = QHBoxLayout()
        bot.setSpacing(20)
        bot.addWidget(self._build_results(), stretch=3)
        bot.addWidget(self._build_log(), stretch=2)
        root.addLayout(bot, stretch=3)

        self.ros.start()
        QApplication.instance().installEventFilter(self)

        # Footer credit
        footer = QLabel("MedGuide-ROS v1.0  //  Developed by Pragadeesh  //  ROS2 Humble + Nav2")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet(f"color: {C['dim']}; font-size: 11px; font-family: 'Consolas', monospace; letter-spacing: 1px; padding: 4px;")
        root.addWidget(footer)

        # Animation Timer
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._on_anim_tick)
        self.anim_timer.start(50)  # 20fps for buttery smooth glow pulse

    # ── UI Initialization ─────────────────────────────

    def _build_system(self):
        g = QGroupBox("SYSTEM_LINK_STATE")
        lay = QGridLayout()
        lay.setSpacing(10)
        
        self.lbl_mode = self._val("> OFFLINE", C['red'])
        self.lbl_stack = self._val("[ ] OFFLINE", C['red'])
        self.lbl_localized = self._val("[ ] SEEKING", C['yellow'])
        self.lbl_estop = self._val("[OK] SAFE", C['cyan'])
        self.lbl_experiment = self._val("—")
        
        self.battery_bar = QProgressBar()
        self.battery_bar.setRange(0, 100)
        self.battery_bar.setValue(100)
        
        rows = [
            ("MODE_CMD", self.lbl_mode),
            ("STACK_RDY", self.lbl_stack),
            ("LOCALIZED", self.lbl_localized),
            ("ESTOP_SYS", self.lbl_estop),
            ("BATCH_RUN", self.lbl_experiment),
            ("BATTERY", self.battery_bar),
        ]
        
        for i, (label, widget) in enumerate(rows):
            lay.addWidget(self._lbl(label), i, 0)
            lay.addWidget(widget, i, 1)
        g.setLayout(lay)
        return g

    def _build_mission(self):
        g = QGroupBox("MISSION_TELEMETRY")
        lay = QGridLayout()
        lay.setSpacing(10)
        
        self.lbl_state = self._val("IDLE", C['dim'])
        self.lbl_goal = self._val("—")
        
        self.lbl_progress = QLabel("0 / 0")
        self.lbl_progress.setStyleSheet(f"color: {C['text']}; font-size: 24px; font-weight: 800; font-family: 'Consolas', 'DejaVu Sans Mono', monospace;")
        self.lbl_progress.setAlignment(Qt.AlignCenter)
        
        self.lbl_distance = self._val("0.0 m")
        self.lbl_duration = self._val("0.0 s")
        self.lbl_estop_count = self._val("0")
        
        rows = [
            ("M_STATE", self.lbl_state),
            ("TARGET_WP", self.lbl_goal),
            ("DIST_TRAV", self.lbl_distance),
            ("TIME_ELAPSED", self.lbl_duration),
            ("INTERRUPTIONS", self.lbl_estop_count),
        ]
        
        for i, (label, widget) in enumerate(rows):
            lay.addWidget(self._lbl(label), i, 0)
            lay.addWidget(widget, i, 1)
            
        prog_lay = QVBoxLayout()
        lbl_p = self._lbl("PROGRESS")
        lbl_p.setAlignment(Qt.AlignCenter)
        prog_lay.addWidget(lbl_p)
        prog_lay.addWidget(self.lbl_progress)
        prog_lay.setAlignment(Qt.AlignCenter)
        prog_lay.setSpacing(4)
        lay.addLayout(prog_lay, 0, 2, 5, 1)
        
        g.setLayout(lay)
        return g

    def _build_controls(self):
        g = QGroupBox("STAGE // SEQUENCE_CONTROL")
        lay = QHBoxLayout()
        lay.setSpacing(16)

        self.btn_launch = QPushButton("LAUNCH")
        self.btn_launch.setObjectName("launchBtn")
        self.btn_launch.clicked.connect(lambda: self._mode("LAUNCH"))

        self.btn_teleop = QPushButton("TELEOP_MODE")
        self.btn_teleop.setObjectName("teleopBtn")
        self.btn_teleop.clicked.connect(lambda: self._mode("TELEOP"))

        self.btn_mission = QPushButton("AUTO_MISSION")
        self.btn_mission.clicked.connect(lambda: self._mode("AUTONOMOUS"))

        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet(f"color: {C['border']};")

        self.spin_trials = QSpinBox()
        self.spin_trials.setRange(1, 50)
        self.spin_trials.setValue(3)

        self.btn_experiment = QPushButton("BATCH_RUN")
        self.btn_experiment.clicked.connect(self._on_experiment)

        self.btn_abort = QPushButton("ABORT")
        self.btn_abort.setObjectName("dangerBtn")
        self.btn_abort.clicked.connect(lambda: self._mode("IDLE"))

        self.btn_shutdown = QPushButton("SHUTDOWN")
        self.btn_shutdown.setObjectName("dangerBtn")
        self.btn_shutdown.clicked.connect(lambda: self._mode("SHUTDOWN"))

        # Group components
        lay.addWidget(self.btn_launch)
        lay.addWidget(self.btn_teleop)
        lay.addWidget(self.btn_mission)
        lay.addWidget(sep)
        lay.addWidget(QLabel("CYCLES:"))
        lay.addWidget(self.spin_trials)
        lay.addWidget(self.btn_experiment)
        lay.addStretch(1)
        lay.addWidget(self.btn_abort)
        lay.addWidget(self.btn_shutdown)

        g.setLayout(lay)
        return g

    def _build_teleop_panel(self):
        g = QGroupBox("STAGE // DIRECT_OVERRIDE")
        g.setMinimumHeight(400) # Force the dashboard to expand when this is visible
        lay = QVBoxLayout()
        lay.setSpacing(16)
        
        bstyle = (
            f"border-radius: 40px; font-size: 24px; font-weight: bold; font-family: 'Consolas', 'DejaVu Sans Mono', monospace;"
            f"background-color: rgba(181, 55, 242, 0.1); color: {C['purple']}; border: 2px solid {C['purple']};"
        )
        def make_btn(label, lin, ang):
            b = QPushButton(label)
            b.setFixedSize(80, 80) # Larger D-pad buttons
            b.setStyleSheet(bstyle)
            b.setFocusPolicy(Qt.NoFocus)
            b.pressed.connect(lambda l=lin, a=ang: self.ros.send_cmd_vel(l, a))
            b.released.connect(lambda: self.ros.send_cmd_vel(0.0, 0.0))
            return b

        self.btn_fwd   = make_btn("[W]",  0.22,   0.0)
        self.btn_left  = make_btn("[A]",  0.0,    0.5)
        self.btn_stop  = make_btn("[S]",  0.0,    0.0)
        self.btn_right = make_btn("[D]",  0.0,   -0.5)
        self.btn_rev   = make_btn("[X]", -0.22,   0.0)
        
        # Stop button — special red style with smaller font to prevent clipping
        stop_style = (
            f"border-radius: 40px; font-size: 18px; font-weight: bold; letter-spacing: 0px;"
            f" font-family: 'Consolas', 'DejaVu Sans Mono', monospace;"
            f" background-color: rgba(255, 0, 60, 0.1); color: {C['red']}; border: 2px solid {C['red']};"
        )
        self.btn_stop.setStyleSheet(stop_style)

        # Central nested QWidget for D-pad buttons
        pad = QWidget()
        pad.setFixedSize(280, 280) # Force exactly enough space for 3x80px columns + 2x16px spacing
        pad_lay = QGridLayout(pad)
        pad_lay.setContentsMargins(0, 0, 0, 0) # Remove margins for tight fit
        pad_lay.setSpacing(16)
        pad_lay.addWidget(self.btn_fwd,   0, 1, Qt.AlignCenter)
        pad_lay.addWidget(self.btn_left,  1, 0, Qt.AlignCenter)
        pad_lay.addWidget(self.btn_stop,  1, 1, Qt.AlignCenter)
        pad_lay.addWidget(self.btn_right, 1, 2, Qt.AlignCenter)
        pad_lay.addWidget(self.btn_rev,   2, 1, Qt.AlignCenter)
        
        # Back Button Container
        top_ctrls = QHBoxLayout()
        self.btn_teleop_back = QPushButton("◀ BACK_TO_IDLE")
        self.btn_teleop_back.setFixedSize(200, 40)
        self.btn_teleop_back.setStyleSheet(f"background-color: transparent; border-radius: 8px; font-size: 14px; font-weight: bold; font-family: 'Consolas', monospace; color: {C['text']}; border: 1px solid {C['border']};")
        self.btn_teleop_back.clicked.connect(lambda: self._mode("IDLE"))
        top_ctrls.addWidget(self.btn_teleop_back)
        top_ctrls.addStretch()

        lay.addLayout(top_ctrls)
        lay.addWidget(pad, alignment=Qt.AlignCenter)

        w_help = QLabel("TELEMETRY_LINK ACTIVE // HOLD W/A/S/D TO THRUST")
        w_help.setAlignment(Qt.AlignCenter)
        w_help.setStyleSheet(f"color: {C['purple']}; font-size: 14px; font-weight: bold; letter-spacing: 2px;")
        lay.addWidget(w_help)
        lay.addStretch()
        
        g.setLayout(lay)
        return g

    def _build_results(self):
        g = QGroupBox("TERMINAL // RESULTS")
        lay = QVBoxLayout()
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setPlaceholderText("Awaiting mission data block...")
        lay.addWidget(self.results_text)
        self.lbl_summary = QLabel("")
        self.lbl_summary.setStyleSheet(f"color: {C['cyan']}; font-size: 13px; font-weight: 800; padding: 4px; font-family: 'Consolas', 'DejaVu Sans Mono', monospace;")
        lay.addWidget(self.lbl_summary)
        g.setLayout(lay)
        return g

    def _build_log(self):
        g = QGroupBox("TERMINAL // EVENT_LOG")
        lay = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        lay.addWidget(self.log_text)
        g.setLayout(lay)
        return g

    # ── Helpers ──────────────────────────────────────

    def _lbl(self, t):
        w = QLabel(t)
        w.setStyleSheet(f"color: {C['dim']}; font-size: 12px; font-family: 'Consolas', 'DejaVu Sans Mono', monospace; letter-spacing: 1px;")
        return w

    def _val(self, t, color=None):
        w = QLabel(t)
        c = color or C['text']
        w.setStyleSheet(f"color: {c}; font-size: 14px; font-weight: bold; font-family: 'Consolas', 'DejaVu Sans Mono', monospace;")
        return w

    def _set_lbl(self, lbl, text, color):
        lbl.setText(text)
        lbl.setStyleSheet(f"color: {color}; font-size: 14px; font-weight: bold; font-family: 'Consolas', 'DejaVu Sans Mono', monospace;")

    # ── Transitions / Animations ─────────────────────

    def _animate_stack_transition(self, idx):
        self.stack.setCurrentIndex(idx)
        self._fade_in = QPropertyAnimation(self.stack_op, b"opacity")
        self._fade_in.setDuration(300)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)
        self._fade_in.setEasingCurve(QEasingCurve.OutCubic)
        self._fade_in.start()

    def _on_anim_tick(self):
        # Animate STOP button pulse if teleop is active
        if self._current_mode == 'TELEOP':
            self._pulse_tick += 1 * self._pulse_dir
            if self._pulse_tick >= 15: self._pulse_dir = -1
            elif self._pulse_tick <= 0: self._pulse_dir = 1
            
            alpha = int(10 + (self._pulse_tick / 15.0) * 40)
            bstyle = (
                f"border-radius: 40px; font-size: 18px; font-weight: bold; letter-spacing: 0px;"
                f" font-family: 'Consolas', 'DejaVu Sans Mono', monospace;"
                f" background-color: rgba(255, 0, 60, 0.{alpha}); color: {C['red']}; border: 2px solid {C['red']};"
            )
            self.btn_stop.setStyleSheet(bstyle)

    # ── Slots ────────────────────────────────────────

    def _on_state(self, d):
        mode = d['mode']
        
        # Mode transition logic
        if mode != self._current_mode:
            self._current_mode = mode
            target_idx = 1 if mode == 'TELEOP' else 0
            if self.stack.currentIndex() != target_idx:
                self._animate_stack_transition(target_idx)

        # Mode label
        mode_colors = {
            'OFFLINE': C['red'], 'LAUNCHING': C['yellow'],
            'IDLE': C['dim'], 'TELEOP': C['purple'],
            'AUTONOMOUS': C['blue'], 'EXPERIMENT': C['accent'],
        }
        
        # Blink stack LED
        self._led_anim_tick += 1
        blink = "[*]" if (self._led_anim_tick % 10 < 5) and d['stack_running'] else "[ ]"
        
        self._set_lbl(self.lbl_mode, f"> {mode}", mode_colors.get(mode, C['text']))

        if not (mode == 'TELEOP'):
            self.ros.send_cmd_vel(0.0, 0.0)

        # Stack
        if d['stack_running']:
            self._set_lbl(self.lbl_stack, f"{blink} ONLINE", C['green'])
        else:
            self._set_lbl(self.lbl_stack, "[ ] OFFLINE", C['red'])

        # Localized
        if d['localized']:
            self._set_lbl(self.lbl_localized, "[*] LOCK_ACQUIRED", C['green'])
        else:
            self._set_lbl(self.lbl_localized, "[ ] SEEKING...", C['yellow'])

        # E-stop
        if d['estop_active']:
            self._set_lbl(self.lbl_estop, "[!] TRIGGERED", C['red'])
        else:
            self._set_lbl(self.lbl_estop, "[OK] SAFE", C['cyan'])

        # Experiment progress
        if d['experiment_total'] > 0:
            self._set_lbl(self.lbl_experiment, f"TRIAL_{d['experiment_trial']}/{d['experiment_total']}", C['accent'])
        else:
            self._set_lbl(self.lbl_experiment, "—", C['dim'])

        # Battery gradient pulse
        batt = int(d['battery_pct'])
        self.battery_bar.setValue(batt)
        bc = C['red'] if batt < 20 else C['green']
        self.battery_bar.setStyleSheet(f"QProgressBar::chunk {{ background-color: {bc}; border-radius: 6px; width: 10px; margin: 2px; }}")

        # Button states
        self._update_buttons(mode, d['stack_running'])

    def _update_buttons(self, mode, running):
        self.btn_launch.setEnabled(not running)
        self.btn_teleop.setEnabled(running and mode in ('IDLE', 'TELEOP'))
        self.btn_mission.setEnabled(running and mode == 'IDLE')
        self.btn_abort.setEnabled(mode in ('TELEOP', 'AUTONOMOUS', 'EXPERIMENT'))
        self.btn_shutdown.setEnabled(running)
        self.btn_experiment.setEnabled(running and mode == 'IDLE')

    def _on_mission(self, d):
        st = d['state']
        cmap = {
            'IDLE': C['dim'], 'NAVIGATING': C['blue'],
            'EMERGENCY_STOP': C['red'],
            'COMPLETED': C['green'], 'FAILED': C['red'],
            'ABORTED': C['yellow'],
        }
        self._set_lbl(self.lbl_state, f"▸ {st}", cmap.get(st, C['text']))
        self.lbl_goal.setText(d['current_goal'] or "—")
        done = d['goals_succeeded'] + d['goals_failed']
        
        # Colorize progress tracker
        color = C['green'] if done == d['goals_total'] and d['goals_total'] > 0 else C['accent']
        self.lbl_progress.setStyleSheet(f"color: {color}; font-size: 24px; font-weight: 800; font-family: 'Consolas', 'DejaVu Sans Mono', monospace;")
        self.lbl_progress.setText(f"{done}/{d['goals_total']}")
        
        self.lbl_distance.setText(f"{d['distance_m']:.1f} m")
        self.lbl_duration.setText(f"{d['elapsed_sec']:.1f} s")
        self.lbl_estop_count.setText(str(d['emergency_stops']))

    def _on_result(self, d):
        icon = "[OK]" if d['success'] else "[FAIL]"
        sl = d.get('straight_line_m', 0)
        actual = d['distance_m']
        eff = (sl / actual * 100) if actual > 0.01 else 0
        self.results_text.append(
            f"{icon} WP_{d['goal_name']:<6s}  "
            f"T={d['duration_sec']:5.1f}s  "
            f"D={actual:5.2f}m  EFF={eff:5.1f}%")
        self.trial_results.append(d)
        self._update_summary()

    def _update_summary(self):
        if not self.trial_results: return
        ok = sum(1 for r in self.trial_results if r['success'])
        n = len(self.trial_results)
        durs = [r['duration_sec'] for r in self.trial_results if r['success']]
        dists = [r['distance_m'] for r in self.trial_results if r['success']]
        ad = sum(durs) / len(durs) if durs else 0
        am = sum(dists) / len(dists) if dists else 0
        self.lbl_summary.setText(f">> BATCH_EVAL: {n} WPs | RATIO: {ok / n * 100:.0f}% | AVG: {ad:.1f}s, {am:.2f}m <<")

    def _on_log(self, msg):
        ts = time.strftime("%H:%M:%S")
        clr = C['green'] if '[OK]' in msg else C['cyan'] if '→' in msg else C['text']
        self.log_text.append(f"<span style='color:{clr};'>[{ts}] {msg}</span>")

    # ── Button Handlers ─────────────────────────────

    def _mode(self, mode):
        self._on_log(f"→ SYS_CMD_OVERRIDE_MODE: {mode}")
        threading.Thread(target=self.ros.call_set_mode, args=(mode,), daemon=True).start()

    def _on_experiment(self):
        n = self.spin_trials.value()
        self._on_log(f"→ EXEC_BATCH_SEQUENCE: {n} CYCLES")
        self.results_text.append(f"\n> INITIATING BATCH SEQUENCE: {n} TRIALS...")
        self.trial_results.clear()
        threading.Thread(target=self.ros.call_run_experiment, args=(n,), daemon=True).start()

    # ── Input Handlers ───────────────────────────────

    def eventFilter(self, obj, event):
        if self._current_mode != 'TELEOP':
            return super().eventFilter(obj, event)

        if event.type() == QEvent.KeyPress and not event.isAutoRepeat():
            k = event.key()
            self._keys_held.add(k)
            self._apply_held_keys()

        elif event.type() == QEvent.KeyRelease and not event.isAutoRepeat():
            k = event.key()
            self._keys_held.discard(k)
            self._apply_held_keys()

        return super().eventFilter(obj, event)

    def _apply_held_keys(self):
        STOP_KEYS = {Qt.Key_S, Qt.Key_Space}
        if any(k in self._keys_held for k in STOP_KEYS) or not self._keys_held:
            linear, angular = 0.0, 0.0
        else:
            linear, angular = 0.0, 0.0
            if Qt.Key_W in self._keys_held or Qt.Key_Up in self._keys_held: linear += 0.2
            if Qt.Key_X in self._keys_held or Qt.Key_Down in self._keys_held: linear -= 0.2
            if Qt.Key_A in self._keys_held or Qt.Key_Left in self._keys_held: angular += 0.5
            if Qt.Key_D in self._keys_held or Qt.Key_Right in self._keys_held: angular -= 0.5

        self.ros.send_cmd_vel(linear, angular)
        
        # Visual feedback on circular D-Pad
        held = self._keys_held
        if hasattr(self, 'btn_fwd'):
            base_style = "border-radius: 40px; font-size: 24px; font-weight: bold; font-family: 'Consolas', 'DejaVu Sans Mono', monospace;"
            def style(active):
                if active: return base_style + f"background-color: rgba(0, 243, 255, 0.4); color: white; border: 2px solid {C['cyan']};"
                return base_style + f"background-color: rgba(181, 55, 242, 0.1); color: {C['purple']}; border: 2px solid {C['purple']};"

            self.btn_fwd.setStyleSheet(style(Qt.Key_W in held or Qt.Key_Up in held))
            self.btn_rev.setStyleSheet(style(Qt.Key_X in held or Qt.Key_Down in held))
            self.btn_left.setStyleSheet(style(Qt.Key_A in held or Qt.Key_Left in held))
            self.btn_right.setStyleSheet(style(Qt.Key_D in held or Qt.Key_Right in held))

    # ── Cleanup ──────────────────────────────────────

    def closeEvent(self, event):
        if hasattr(self, 'anim_timer'): self.anim_timer.stop()
        
        # Signal shutdown cleanly
        self.ros.call_set_mode("SHUTDOWN")
        
        # Await ROS thread graceful termination
        self.ros.stop()
        
        QApplication.instance().removeEventFilter(self)
        event.accept()

# ── Main ─────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("MedGuide Command Console")
    p = QPalette()
    p.setColor(QPalette.Window, QColor(C['bg']))
    p.setColor(QPalette.WindowText, QColor(C['text']))
    p.setColor(QPalette.Base, QColor(C['bg']))
    p.setColor(QPalette.Text, QColor(C['text']))
    app.setPalette(p)
    w = Dashboard()
    w.show()
    
    ret = app.exec_()
    if rclpy.ok():
        try:
            rclpy.shutdown()
        except Exception:
            pass
            
    sys.exit(ret)

if __name__ == '__main__':
    main()

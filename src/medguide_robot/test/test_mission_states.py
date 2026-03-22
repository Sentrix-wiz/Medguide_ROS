#!/usr/bin/env python3
"""
Unit Tests — Mission State Transitions & Distance Tracking.

Tests the mission state machine and odometry distance accumulation
without requiring a running ROS2 system.

Run:
    cd ~/medguide_ws
    colcon test --packages-select medguide_robot --pytest-args test/test_mission_states.py
"""

import math
import pytest


# ── Pure logic extracted for testing ──────────────────────────

class MissionStateMachine:
    """

    Minimal state machine matching mission_scheduler_node logic.

    Extracted for unit testability.
    """

    IDLE = 'IDLE'
    NAVIGATING = 'NAVIGATING'
    EMERGENCY_STOP = 'EMERGENCY_STOP'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'
    ABORTED = 'ABORTED'

    def __init__(self):
        self.state = self.IDLE
        self.goals_succeeded = 0
        self.goals_failed = 0
        self.current_idx = 0
        self.queue = []

    def start(self, rooms):
        if self.state == self.NAVIGATING:
            return False
        self.queue = list(rooms)
        self.current_idx = 0
        self.goals_succeeded = 0
        self.goals_failed = 0
        self.state = self.NAVIGATING
        return True

    def goal_succeeded(self):
        self.goals_succeeded += 1
        self.current_idx += 1
        if self.current_idx >= len(self.queue):
            self.state = self.COMPLETED

    def goal_failed(self):
        self.goals_failed += 1
        self.current_idx += 1
        if self.current_idx >= len(self.queue):
            self.state = self.COMPLETED

    def abort(self):
        if self.state in (self.IDLE, self.COMPLETED, self.ABORTED):
            return False
        self.state = self.ABORTED
        return True

    def emergency_stop(self):
        if self.state == self.NAVIGATING:
            self.state = self.EMERGENCY_STOP

    def emergency_clear(self):
        if self.state == self.EMERGENCY_STOP:
            self.state = self.NAVIGATING


def accumulate_distance(prev_x, prev_y, new_x, new_y, max_jump=1.0):
    """

    Odometry distance accumulation logic from mission_scheduler.

    Returns (distance_delta, new_prev_x, new_prev_y).
    """
    if prev_x is None:
        return 0.0, new_x, new_y
    dx = new_x - prev_x
    dy = new_y - prev_y
    dist = math.sqrt(dx * dx + dy * dy)
    if dist >= max_jump:
        return 0.0, new_x, new_y  # Teleportation filter
    return dist, new_x, new_y


# ── Test: State Machine ──────────────────────────────────────

class TestMissionStateMachine:
    """Test mission state transitions."""

    def test_start_from_idle(self):
        sm = MissionStateMachine()
        assert sm.start(['room_a', 'room_b'])
        assert sm.state == 'NAVIGATING'
        assert len(sm.queue) == 2

    def test_cannot_start_while_navigating(self):
        sm = MissionStateMachine()
        sm.start(['room_a'])
        assert not sm.start(['room_b'])

    def test_complete_all_goals(self):
        sm = MissionStateMachine()
        sm.start(['room_a', 'room_b'])
        sm.goal_succeeded()
        assert sm.state == 'NAVIGATING'
        sm.goal_succeeded()
        assert sm.state == 'COMPLETED'
        assert sm.goals_succeeded == 2

    def test_mixed_success_failure(self):
        sm = MissionStateMachine()
        sm.start(['a', 'b', 'c'])
        sm.goal_succeeded()
        sm.goal_failed()
        sm.goal_succeeded()
        assert sm.state == 'COMPLETED'
        assert sm.goals_succeeded == 2
        assert sm.goals_failed == 1

    def test_abort_during_navigation(self):
        sm = MissionStateMachine()
        sm.start(['room_a'])
        assert sm.abort()
        assert sm.state == 'ABORTED'

    def test_cannot_abort_idle(self):
        sm = MissionStateMachine()
        assert not sm.abort()

    def test_emergency_stop_pause_resume(self):
        sm = MissionStateMachine()
        sm.start(['room_a'])
        sm.emergency_stop()
        assert sm.state == 'EMERGENCY_STOP'
        sm.emergency_clear()
        assert sm.state == 'NAVIGATING'

    def test_emergency_no_effect_when_idle(self):
        sm = MissionStateMachine()
        sm.emergency_stop()
        assert sm.state == 'IDLE'


# ── Test: Distance Tracking ──────────────────────────────────

class TestDistanceAccumulation:
    """Test odometry distance logic."""

    def test_first_reading_zero(self):
        dist, x, y = accumulate_distance(None, None, 1.0, 2.0)
        assert dist == 0.0
        assert x == 1.0
        assert y == 2.0

    def test_straight_line(self):
        total = 0.0
        px, py = 0.0, 0.0
        for i in range(1, 11):
            d, px, py = accumulate_distance(px, py, float(i) * 0.1, 0.0)
            total += d
        assert total == pytest.approx(1.0, abs=0.01)

    def test_diagonal(self):
        """Small diagonal movement should be tracked."""
        dist, _, _ = accumulate_distance(0.0, 0.0, 0.3, 0.4)
        assert dist == pytest.approx(0.5, abs=0.01)

    def test_teleport_filtered(self):
        """Jumps > 1m should be filtered (sim reset artifacts)."""
        dist, _, _ = accumulate_distance(0.0, 0.0, 10.0, 10.0)
        assert dist == 0.0

    def test_zero_movement(self):
        dist, _, _ = accumulate_distance(1.0, 2.0, 1.0, 2.0)
        assert dist == 0.0

    def test_small_movement(self):
        dist, _, _ = accumulate_distance(0.0, 0.0, 0.01, 0.0)
        assert dist == pytest.approx(0.01, abs=0.001)

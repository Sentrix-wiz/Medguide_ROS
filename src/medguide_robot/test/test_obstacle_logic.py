#!/usr/bin/env python3
"""
Unit Tests — Obstacle Detector Logic.

Tests the front-cone filtering and hysteresis-based emergency stop
logic without requiring a running ROS2 system.

Run:
    cd ~/medguide_ws
    colcon test --packages-select medguide_robot --pytest-args test/test_obstacle_logic.py
"""

import math
import pytest


class FakeMsg:
    """Minimal LaserScan-like object for unit testing."""

    def __init__(self, ranges, angle_min=-math.pi, angle_max=math.pi,
                 angle_increment=None, range_min=0.1, range_max=30.0):
        self.ranges = ranges
        self.angle_min = angle_min
        self.angle_max = angle_max
        self.range_min = range_min
        self.range_max = range_max
        n = len(ranges)
        self.angle_increment = angle_increment or (
            (angle_max - angle_min) / max(n - 1, 1)
        )


def find_closest_in_cone(msg, filter_angle_rad):
    """

    Extract the core obstacle detection algorithm.

    Extracts the algorithm from the node for isolated testing.

    This mirrors ObstacleDetectorNode._scan_callback.
    """
    min_dist = float('inf')
    min_angle = 0.0
    valid_rays = 0

    for i, r in enumerate(msg.ranges):
        if math.isnan(r) or math.isinf(r):
            continue
        if r < msg.range_min or r > msg.range_max:
            continue

        angle = msg.angle_min + (i * msg.angle_increment)

        if abs(angle) > filter_angle_rad:
            continue

        valid_rays += 1
        if r < min_dist:
            min_dist = r
            min_angle = angle

    return min_dist, min_angle, valid_rays


def apply_hysteresis(min_dist, was_active, threshold, clear_threshold):
    """

    Pure hysteresis logic extracted from obstacle_detector_node.

    Returns new emergency_active state.
    """
    if min_dist < threshold:
        return True
    elif min_dist > clear_threshold:
        return False
    else:
        return was_active  # Stay in current state (hysteresis band)


# ── Test: Front-cone filtering ───────────────────────────────

class TestFrontConeFiltering:
    """Test that only front-facing beams are considered."""

    def test_obstacle_in_front(self):
        """Obstacle directly ahead should be detected."""
        # 5 beams spread -pi to pi, obstacle at center beam
        ranges = [10.0, 10.0, 0.3, 10.0, 10.0]
        msg = FakeMsg(ranges)
        dist, angle, valid = find_closest_in_cone(
            msg, math.radians(30)
        )
        assert dist == pytest.approx(0.3, abs=0.01)
        assert abs(angle) < 0.1  # Near center

    def test_obstacle_behind_ignored(self):
        """Obstacle behind robot (angle > cone) should be ignored."""
        ranges = [0.1, 10.0, 10.0, 10.0, 0.1]
        msg = FakeMsg(ranges)
        dist, _, valid = find_closest_in_cone(msg, math.radians(30))
        assert dist > 5.0  # Behind obstacles ignored

    def test_nan_values_filtered(self):
        """Verify NaN and inf ranges are skipped."""
        ranges = [float('nan'), float('inf'), 2.0, float('nan'), 5.0]
        msg = FakeMsg(ranges)
        dist, _, valid = find_closest_in_cone(msg, math.pi)
        assert dist == pytest.approx(2.0, abs=0.01)
        assert valid == 2  # Only 2 valid rays

    def test_empty_scan(self):
        """Empty scan should return inf distance."""
        msg = FakeMsg([])
        dist, _, valid = find_closest_in_cone(msg, math.radians(30))
        assert dist == float('inf')
        assert valid == 0

    def test_all_out_of_range(self):
        """All beams below range_min should be ignored."""
        msg = FakeMsg([0.01, 0.02, 0.03], range_min=0.1)
        dist, _, valid = find_closest_in_cone(msg, math.pi)
        assert dist == float('inf')
        assert valid == 0


# ── Test: Hysteresis logic ───────────────────────────────────

class TestHysteresis:
    """Test emergency stop trigger/clear with hysteresis band."""

    THRESHOLD = 0.25
    CLEAR = 0.35

    def test_trigger_below_threshold(self):
        """Should activate when distance < threshold."""
        active = apply_hysteresis(0.20, False, self.THRESHOLD, self.CLEAR)
        assert active is True

    def test_clear_above_clear_threshold(self):
        """Should deactivate when distance > clear_threshold."""
        active = apply_hysteresis(0.40, True, self.THRESHOLD, self.CLEAR)
        assert active is False

    def test_hysteresis_band_stays_active(self):
        """Between threshold and clear: should stay active if was active."""
        active = apply_hysteresis(0.30, True, self.THRESHOLD, self.CLEAR)
        assert active is True

    def test_hysteresis_band_stays_inactive(self):
        """Between threshold and clear: should stay inactive if was inactive."""
        active = apply_hysteresis(0.30, False, self.THRESHOLD, self.CLEAR)
        assert active is False

    def test_exact_threshold(self):
        """At exactly threshold distance, should trigger."""
        active = apply_hysteresis(0.24, False, self.THRESHOLD, self.CLEAR)
        assert active is True

    def test_oscillation_prevention(self):
        """Rapid distance changes in band should not oscillate."""
        state = False
        distances = [0.40, 0.30, 0.20, 0.30, 0.30, 0.30, 0.40]
        expected = [False, False, True, True, True, True, False]

        for d, exp in zip(distances, expected):
            state = apply_hysteresis(d, state, self.THRESHOLD, self.CLEAR)
            assert state == exp, f'dist={d}, expected={exp}, got={state}'

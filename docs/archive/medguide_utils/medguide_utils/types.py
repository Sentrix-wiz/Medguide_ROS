"""
Custom types and enumerations for MedGuide robotics system.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional


class MissionStatus(Enum):
    """Status enumeration for mission execution states."""
    IDLE = "idle"
    EXECUTING = "executing"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    EMERGENCY_STOP = "emergency_stop"


class GoalStatus(Enum):
    """Status enumeration for individual navigation goals."""
    PENDING = "pending"
    ACTIVE = "active"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"


@dataclass
class MissionMetrics:
    """Aggregated metrics for a mission execution."""
    total_goals: int
    succeeded_goals: int
    failed_goals: int
    total_time_seconds: float
    emergency_stops: int
    battery_used_percent: float
    
    @property
    def success_rate(self) -> float:
        """Calculate mission success rate as percentage."""
        if self.total_goals == 0:
            return 0.0
        return (self.succeeded_goals / self.total_goals) * 100.0
    
    def __str__(self):
        return (
            f"MissionMetrics(goals={self.total_goals}, "
            f"succeeded={self.succeeded_goals}, failed={self.failed_goals}, "
            f"time={self.total_time_seconds:.1f}s, success_rate={self.success_rate:.1f}%)"
        )


@dataclass
class ObstacleData:
    """Obstacle detection data from sensor processing."""
    closest_distance: float  # meters
    angle_to_obstacle: float  # radians
    timestamp: float  # seconds
    is_emergency: bool  # True if below safety threshold

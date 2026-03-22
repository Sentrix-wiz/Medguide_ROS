"""
Mission configuration types and constants for MedGuide.

Defines the primary mission parameters including room locations,
obstacle thresholds, and goal definitions.
"""

from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class RoomGoal:
    """Represents a room delivery mission goal."""
    name: str
    x: float  # meters
    y: float  # meters
    theta: float  # radians (orientation)
    description: str = ""

    def __str__(self):
        return f"{self.name} @ ({self.x:.2f}, {self.y:.2f})"


# Default Hospital Layout Rooms
HOSPITAL_ROOMS = {
    "room_a": RoomGoal(name="room_a", x=1.0, y=1.0, theta=0.0, 
                       description="Patient Room A"),
    "room_b": RoomGoal(name="room_b", x=5.0, y=1.0, theta=0.0, 
                       description="Patient Room B"),
    "room_c": RoomGoal(name="room_c", x=5.0, y=5.0, theta=0.0, 
                       description="Patient Room C"),
    "dock": RoomGoal(name="dock", x=0.5, y=0.5, theta=0.0, 
                     description="Charging Dock"),
}

# Default mission sequence: A -> B -> C -> Dock
DEFAULT_MISSION_SEQUENCE: List[str] = ["room_a", "room_b", "room_c", "dock"]

# Safety thresholds
OBSTACLE_DISTANCE_THRESHOLD = 0.3  # meters
MAX_GOAL_TIMEOUT = 120.0  # seconds
MISSION_LOOP_RATE_HZ = 1.0  # Hz

# Navigation parameters
MAX_LINEAR_VELOCITY = 0.5  # m/s
MAX_ANGULAR_VELOCITY = 1.0  # rad/s
GOAL_TOLERANCE_DISTANCE = 0.2  # meters
GOAL_TOLERANCE_ANGLE = 0.1  # radians

# Battery simulation
INITIAL_BATTERY_LEVEL = 100.0  # percent
BATTERY_DRAIN_RATE = 0.5  # percent per minute of movement

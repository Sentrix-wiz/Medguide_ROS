"""
QoS profile definitions for MedGuide ROS 2 nodes.

Provides consistent quality-of-service profiles for different communication types:
- Sensor data (LaserScan): Best effort, volatile
- Command/control (Nav2 goals): Reliable, transient_local
- Status/diagnostics: Reliable, volatile
"""

from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy


# Sensor data: Best effort, high frequency, no history needed
SENSOR_QOS = QoSProfile(
    reliability=ReliabilityPolicy.BEST_EFFORT,
    durability=DurabilityPolicy.VOLATILE,
    history=HistoryPolicy.KEEP_LAST,
    depth=1,
)

# Command/control: Reliable, persistent for action clients
COMMAND_QOS = QoSProfile(
    reliability=ReliabilityPolicy.RELIABLE,
    durability=DurabilityPolicy.TRANSIENT_LOCAL,
    history=HistoryPolicy.KEEP_LAST,
    depth=10,
)

# Status/diagnostics: Reliable, volatile, moderate history
STATUS_QOS = QoSProfile(
    reliability=ReliabilityPolicy.RELIABLE,
    durability=DurabilityPolicy.VOLATILE,
    history=HistoryPolicy.KEEP_LAST,
    depth=5,
)

# Default system clock QoS (for timestamps)
DEFAULT_QOS = QoSProfile(
    reliability=ReliabilityPolicy.RELIABLE,
    durability=DurabilityPolicy.VOLATILE,
    history=HistoryPolicy.KEEP_LAST,
    depth=10,
)

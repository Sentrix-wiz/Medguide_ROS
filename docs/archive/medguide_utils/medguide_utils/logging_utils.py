"""
Logging utilities for MedGuide nodes.

Provides consistent logging patterns with structured output for research-grade monitoring.
"""

from typing import Optional
import logging


def get_logger(node_logger):
    """
    Get a configured logger from a ROS 2 node.
    
    Args:
        node_logger: The ROS 2 node's logger object (from self.get_logger())
    
    Returns:
        The logger object for use with .info(), .warn(), .error(), etc.
    """
    return node_logger


def log_mission_start(logger, mission_id: str, goals: list):
    """Log the start of a mission sequence."""
    logger.info(f"[MISSION-START] ID={mission_id}, Goals={goals}")


def log_goal_sent(logger, goal_name: str, x: float, y: float, theta: float):
    """Log when a navigation goal is sent."""
    logger.info(
        f"[GOAL-SENT] name={goal_name}, "
        f"pose=({x:.2f}, {y:.2f}, {theta:.2f})"
    )


def log_goal_reached(logger, goal_name: str, elapsed_time: float):
    """Log successful goal completion."""
    logger.info(
        f"[GOAL-REACHED] name={goal_name}, elapsed={elapsed_time:.2f}s"
    )


def log_goal_failed(logger, goal_name: str, reason: str, elapsed_time: float):
    """Log goal failure."""
    logger.error(
        f"[GOAL-FAILED] name={goal_name}, "
        f"reason={reason}, elapsed={elapsed_time:.2f}s"
    )


def log_emergency_stop(logger, obstacle_distance: float):
    """Log an emergency stop event."""
    logger.warn(
        f"[EMERGENCY-STOP] Obstacle detected at distance={obstacle_distance:.3f}m"
    )


def log_mission_complete(logger, total_time: float, success_count: int, 
                         failure_count: int):
    """Log mission sequence completion."""
    success_rate = (success_count / (success_count + failure_count) * 100
                    if (success_count + failure_count) > 0 else 0)
    logger.info(
        f"[MISSION-COMPLETE] total_time={total_time:.2f}s, "
        f"successes={success_count}, failures={failure_count}, "
        f"success_rate={success_rate:.1f}%"
    )


def log_battery_status(logger, battery_level: float):
    """Log current battery level."""
    level_str = "CRITICAL" if battery_level < 20 else "LOW" if battery_level < 40 else "OK"
    logger.info(f"[BATTERY] level={battery_level:.1f}% [{level_str}]")

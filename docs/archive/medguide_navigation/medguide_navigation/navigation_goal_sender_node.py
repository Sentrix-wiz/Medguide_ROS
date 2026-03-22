#!/usr/bin/env python3
"""
Navigation Goal Sender Node for MedGuide.

Sends Navigation-to-Pose goals using Nav2 action server.
Waits for goal completion, reports success/failure, and provides feedback.

Subscribes to:
  - /goal_request (geometry_msgs/PoseStamped) - incoming navigation goals

Publishes to:
  - /goal_status (std_msgs/String) - goal status updates

Actions:
  - Uses NavigateToPose action from Nav2
"""

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose
from std_msgs.msg import String

from medguide_utils.qos_profiles import COMMAND_QOS, STATUS_QOS
from medguide_utils.logging_utils import log_goal_sent, log_goal_reached, log_goal_failed


class NavigationGoalSender(Node):
    """Sends navigation goals to the Nav2 stack via action client."""

    def __init__(self):
        super().__init__('navigation_goal_sender')
        
        # Nav2 action client
        self._action_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')
        
        # Status publisher
        self.status_pub = self.create_publisher(
            String, 
            '/goal_status', 
            STATUS_QOS
        )
        
        # Get parameters from config
        self.declare_parameter('use_sim_time', True)
        self.declare_parameter('goal_timeout', 120.0)
        
        # Tracking current goal
        self.current_goal = None
        self.current_handle = None
        self.goal_name = ""
        
        self.get_logger().info("NavigationGoalSender node initialized")

    def send_goal(self, target_pose: PoseStamped, goal_name: str = "goal") -> bool:
        """
        Send a navigation goal and wait for completion.
        
        Args:
            target_pose: geometry_msgs/PoseStamped goal pose
            goal_name: Human-readable name for logging
            
        Returns:
            True if goal succeeded, False otherwise
        """
        self.goal_name = goal_name
        
        # Log the goal send
        x = target_pose.pose.position.x
        y = target_pose.pose.position.y
        theta = 0.0  # Simplified; would extract from quaternion in production
        log_goal_sent(self.get_logger(), goal_name, x, y, theta)
        
        # Create goal message
        goal_msg = NavigateToPose.Goal()
        goal_msg.pose = target_pose
        
        # Wait for action server
        if not self._action_client.wait_for_server(timeout_sec=10.0):
            self.get_logger().error(f"Nav2 action server not available for {goal_name}")
            self._publish_status(f"FAILED: Action server unavailable - {goal_name}")
            return False
        
        # Send goal asynchronously
        self._send_goal_future = self._action_client.send_goal_async(
            goal_msg,
            feedback_callback=self._feedback_callback
        )
        
        # Wait for goal response
        rclpy.spin_until_future_complete(self, self._send_goal_future, timeout_sec=5.0)
        
        if self._send_goal_future.result() is None:
            self.get_logger().error(f"Goal {goal_name} was rejected by Nav2")
            self._publish_status(f"FAILED: Goal rejected - {goal_name}")
            return False
        
        self.current_handle = self._send_goal_future.result()
        
        # Wait for goal completion
        self._get_result_future = self.current_handle.get_result_async()
        rclpy.spin_until_future_complete(
            self, 
            self._get_result_future, 
            timeout_sec=self.get_parameter('goal_timeout').value
        )
        
        result = self._get_result_future.result()
        
        if result is None or result.status != 4:  # 4 = SUCCEEDED
            self.get_logger().warn(
                f"Goal {goal_name} did not complete successfully. Status: {result.status if result else 'None'}"
            )
            self._publish_status(f"FAILED: {goal_name}")
            return False
        
        self.get_logger().info(f"Goal {goal_name} completed successfully")
        self._publish_status(f"SUCCESS: {goal_name}")
        return True

    def _feedback_callback(self, feedback_msg):
        """Handle feedback from Nav2 during goal execution."""
        feedback = feedback_msg.feedback
        remaining_distance = feedback.distance_remaining
        self.get_logger().debug(
            f"Goal {self.goal_name}: distance_remaining={remaining_distance:.2f}m"
        )

    def _publish_status(self, status_msg: str):
        """Publish status to topic."""
        msg = String()
        msg.data = status_msg
        self.status_pub.publish(msg)


def main(args=None):
    """Main entry point for the navigation goal sender node."""
    rclpy.init(args=args)
    node = NavigationGoalSender()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Shutting down navigation goal sender")
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

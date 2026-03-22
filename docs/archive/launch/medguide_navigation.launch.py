#!/usr/bin/env python3
"""
MedGuide navigation nodes launch file.

Launches all navigation-related nodes:
  - Navigation goal sender (Nav2 action client)
"""

import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    """Generate launch description for navigation layer."""
    
    from ament_index_python.packages import get_package_share_directory
    
    medguide_bringup_dir = get_package_share_directory('medguide_bringup')
    
    # Config path
    nav_config = os.path.join(
        medguide_bringup_dir,
        '..',
        '..',
        'config',
        'nav2_params_hospital.yaml'
    )
    
    # Declare launch arguments
    launch_args = [
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='Use simulation time'
        ),
        DeclareLaunchArgument(
            'log_level',
            default_value='INFO',
            description='Log level for nodes'
        ),
    ]
    
    # Navigation goal sender node
    nav_goal_sender = Node(
        package='medguide_navigation',
        executable='navigation_goal_sender',
        name='navigation_goal_sender',
        parameters=[
            nav_config,
            {'use_sim_time': LaunchConfiguration('use_sim_time')}
        ],
        arguments=['--ros-args', '--log-level', LaunchConfiguration('log_level')],
        output='screen',
    )
    
    return LaunchDescription(launch_args + [nav_goal_sender])

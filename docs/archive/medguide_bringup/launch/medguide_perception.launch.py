#!/usr/bin/env python3
"""
MedGuide perception nodes launch file.

Launches all perception-related nodes:
  - Obstacle detector (LaserScan -> emergency stop)
"""

import os
from pathlib import Path

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    """Generate launch description for perception layer."""
    
    from ament_index_python.packages import get_package_share_directory
    
    medguide_perception_dir = get_package_share_directory('medguide_perception')
    medguide_bringup_dir = get_package_share_directory('medguide_bringup')
    
    # Config path
    perception_config = os.path.join(
        medguide_bringup_dir,
        '..',
        '..',
        'config',
        'perception_params.yaml'
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
    
    # Obstacle detector node
    obstacle_detector = Node(
        package='medguide_perception',
        executable='obstacle_detector',
        name='obstacle_detector',
        parameters=[
            perception_config,
            {'use_sim_time': LaunchConfiguration('use_sim_time')}
        ],
        arguments=['--ros-args', '--log-level', LaunchConfiguration('log_level')],
        output='screen',
    )
    
    # TODO: Camera detection node placeholder
    # camera_detector = Node(
    #     package='medguide_perception',
    #     executable='camera_detector',
    #     name='camera_detector',
    #     parameters=[perception_config],
    #     output='screen',
    # )
    
    return LaunchDescription(launch_args + [obstacle_detector])

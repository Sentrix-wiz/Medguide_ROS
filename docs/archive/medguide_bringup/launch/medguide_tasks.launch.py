#!/usr/bin/env python3
"""
MedGuide task management nodes launch file.

Launches all task management and orchestration nodes:
  - Mission scheduler (core mission coordinator)
"""

import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    """Generate launch description for task management layer."""
    
    from ament_index_python.packages import get_package_share_directory
    
    medguide_bringup_dir = get_package_share_directory('medguide_bringup')
    
    # Config paths
    task_config = os.path.join(
        medguide_bringup_dir,
        '..',
        '..',
        'config',
        'task_params.yaml'
    )
    
    mission_config = os.path.join(
        medguide_bringup_dir,
        '..',
        '..',
        'config',
        'mission_params.yaml'
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
    
    # Mission scheduler node (core orchestrator)
    mission_scheduler = Node(
        package='medguide_tasks',
        executable='mission_scheduler',
        name='mission_scheduler',
        parameters=[
            task_config,
            mission_config,
            {'use_sim_time': LaunchConfiguration('use_sim_time')}
        ],
        arguments=['--ros-args', '--log-level', LaunchConfiguration('log_level')],
        output='screen',
    )
    
    return LaunchDescription(launch_args + [mission_scheduler])
